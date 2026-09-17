import os, logging, json
from copy import deepcopy
from graphlib import TopologicalSorter, CycleError
from typing import Any, List, Dict, Union
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage, FunctionMessage
from core.config import default_config, LlmConfig, GraphConfig
from .schemas import (
    GlobalAgentState, PydanticActionGraph, TaskStatus, 
    TaskType, PydanticTaskGraph, PydanticEditAction, PydanticGraphModificationPlan
)
from .utils import load_prompt, increase_num_steps, comment_block, SessionWorkspace
from .action_graph import ActionGraph, ActionNode
from .llm_factory import get_chat_model

logger = logging.getLogger(default_config.SESS_LOG_NAME)

class TaskNode:
    """Represents a single node in the task graph."""
    def __init__(self, node_id: str, node_name: str, instruction: str, dependencies: list[str], task_type: TaskType, output: str, model: str):
        """Construct a task node with metadata, dependencies, and LLM client."""
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("task_id must be a non-empty string.")
        
        self.node_id = node_id
        self.node_name = node_name
        self.instruction = instruction
        self.dependencies = dependencies
        self.status = TaskStatus.PENDING
        self.task_type = task_type
        self.output = output
        self.result: str | None = None
        self.action_graph = ActionGraph()
        self.conversation_history: List[BaseMessage] = []
        self.llm = get_chat_model(
            model_name=model,
            temperature=default_config.GEMINI_TEMPERATURE,
            max_retries=default_config.GEMINI_MAX_RETRIES,
            timeout=default_config.GEMINI_TIMEOUT
        )

    def __repr__(self):
        """Return a readable summary with id, status, and dependency info."""
        return (f"TaskNode(id='{self.node_id}', status='{self.status.value}', "
                f"instruction='{self.instruction[:30]}...', deps={self.dependencies})")
    
    def to_dict(self) -> dict:
        """Serialize the task node, trimming conversation history and actions."""
        history = getattr(self, "conversation_history", [])

        latest_history = history[-default_config.HISTORY_CONTEXT_WINDOW:]

        serialized_history = []
        for msg in latest_history:
            if hasattr(msg, "model_dump"): # LangChain Core / Pydantic v2
                serialized_history.append(msg.model_dump())
            elif hasattr(msg, "dict"): # Older Pydantic v1
                serialized_history.append(msg.dict())
            else:
                serialized_history.append(msg)

        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "instruction": self.instruction,
            "dependencies": self.dependencies,
            "task_type": self.task_type.value,
            "output": self.output,
            "status": self.status.value,
            "result": self.result,
            "action_graph": self.action_graph.to_dict(),
            "model_name": self.llm.model_name,
            "conversation_history": serialized_history
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Recreate a task node from stored data, including history and actions."""
        node = cls(
            node_id=data["node_id"],
            node_name=data["node_name"],
            instruction=data["instruction"],
            dependencies=data["dependencies"],
            task_type=TaskType(data["task_type"]),
            output=data["output"],
            model=data.get("model_name", default_config.GEMINI_MODEL)
        )
        
        node.status = TaskStatus(data["status"])
        node.result = data.get("result")

        if "conversation_history" in data and data["conversation_history"]:
            raw_history = data["conversation_history"]
            deserialized_history = []
            
            for msg_data in raw_history:
                msg_type = msg_data.get("type")
                
                if "data" in msg_data and isinstance(msg_data["data"], dict):
                    msg_payload = msg_data["data"]
                else:
                    msg_payload = msg_data

                if msg_type == "human":
                    deserialized_history.append(HumanMessage(**msg_payload))
                elif msg_type == "ai":
                    deserialized_history.append(AIMessage(**msg_payload))
                elif msg_type == "system":
                    deserialized_history.append(SystemMessage(**msg_payload))
                elif msg_type == "tool":
                    deserialized_history.append(ToolMessage(**msg_payload))
                elif msg_type == "function":
                    deserialized_history.append(FunctionMessage(**msg_payload))
            
            node.conversation_history = deserialized_history
        else:
            node.conversation_history = []
        
        if "action_graph" in data:
            node.action_graph = ActionGraph.from_dict(data["action_graph"])
            
        return node

    def plan_actions(self, global_agent_state: GlobalAgentState, workspace: SessionWorkspace, namespace: dict, tool_sets=[], additional_instruction: str = "", conversation_history: list = []) -> ActionGraph:
        """Generate an action graph using the code agent prompt and current context."""
        structured_llm = self.llm.with_structured_output(PydanticActionGraph)
        
        sys_prompt_template = load_prompt(agent_name=default_config.AGENT_NAME_CODE)
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt_template),
            ("human", "Agent State: {agent_state}. namespace: {namespace}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Instruction: {instruction}. Additional Instruction: {additional_instruction}.")
        ])
        chain = prompt | structured_llm
        
        pydantic_action_graph: PydanticActionGraph = chain.invoke({"instruction": self.instruction, "additional_instruction":additional_instruction, "agent_state":global_agent_state, "namespace":namespace, "data_dir":str(workspace.data_dir), "figure_dir":str(workspace.figure_dir), "model_dir":str(workspace.model_dir), "chat_history": conversation_history}) # type: ignore
        
        action_graph = ActionGraph()
        for p_node in pydantic_action_graph.task_nodes:
            action_node = ActionNode(
                action_id=p_node.action_id,
                description=p_node.description,
                code=p_node.code
            )
            action_graph.add_action(action_node)
        
        increase_num_steps(global_agent_state)
        return action_graph

    def replan_actions(self, global_agent_state: GlobalAgentState, workspace: SessionWorkspace, namespace: dict, conversation_history: list = []):
        """Regenerate the action graph with refinement instructions after failure."""
        refinement_instruction = load_prompt(agent_name=default_config.AGENT_NAME_CODE, key=default_config.PROMPT_KEY_CODE_REPLAN)
        refined_graph: ActionGraph = self.plan_actions(global_agent_state=global_agent_state, workspace=workspace, namespace=namespace, additional_instruction=refinement_instruction, conversation_history=conversation_history)
        self.action_graph.nodes = refined_graph.nodes
        self.action_graph.result = None

    def execute_with_retry(self, global_agent_state: GlobalAgentState, workspace: SessionWorkspace, max_retries: int = default_config.ACTION_GRAPH_MAX_RETRIES):
          """Generate and refine the ActionGraph within a trial limit."""
          debug_agent_state: GlobalAgentState = deepcopy(global_agent_state)
          
          namespace = {default_config.KEY_AGENT_STATE: deepcopy(debug_agent_state)}

          self.conversation_history = []

          action_graph: ActionGraph = self.plan_actions(global_agent_state=debug_agent_state, workspace=workspace, namespace=namespace)
          self.action_graph = action_graph

          for i in range(max_retries):
              namespace = {default_config.KEY_AGENT_STATE: deepcopy(debug_agent_state)}
              
              logger.debug(f"Trial {i+1}")
              self.action_graph.execute_action_graph(namespace)

              if self.action_graph.result is None:
                  raise Exception("Action Graph Result is None")
              
              plan_data = []
              for node in self.action_graph.nodes:
                  # Using attributes from your generate_action_graph function
                  plan_data.append({
                      "action_id": node.action_id,
                      "description": node.description,
                      "code": node.code
                  })
              plan_string = json.dumps(plan_data, indent=2)
              self.conversation_history.append(AIMessage(content=f"Current plan:\n```json\n{plan_string}\n```"))
              execution_message = (
                  f"Execution Succeeded: {self.action_graph.result.message}" if self.action_graph.result.success
                  else f"Execution Failed: {self.action_graph.result.message}"
              )
              self.conversation_history.append(HumanMessage(content=execution_message))
              self.conversation_history = self.conversation_history[-4:]

              logger.debug(self.action_graph.result)
              if self.action_graph.result.success is False:
                  self.replan_actions(global_agent_state=debug_agent_state, workspace=workspace, namespace=namespace, conversation_history=self.conversation_history)
                  increase_num_steps(global_agent_state)
              else:
                  self.status = TaskStatus.SUCCESS
                  break
              
          self._save_conversation_history(workspace=workspace)
          logger.debug(f"History Traceback: {self.conversation_history}")
          if self.action_graph.result is not None and self.action_graph.result.success is False:
              self.status = TaskStatus.FAILED
              self.result = str(self.action_graph.result)

    def _save_conversation_history(self, workspace: SessionWorkspace, filename: str = default_config.FILENAME_CONVERSATION_HISTORY, ensure_dir: bool = True) -> str:
        """
        Persist a conversation history to session/{sess_id}/{run_id}/{filename}.
        - conversation_history: list of messages (dicts with 'sender'/'content' or langchain Message objects with .content)
        - returns the written filepath as string
        """
        import json

        def _format_message(msg) -> str:
            # dict-like AgentMessage
            if isinstance(msg, dict):
                sender = msg.get("sender", "Unknown")
                content = msg.get("content", "")
            else:
                # langchain messages (HumanMessage/AIMessage/SystemMessage) or arbitrary objects
                sender = getattr(msg, "sender", None) or msg.__class__.__name__
                content = getattr(msg, "content", msg)

            # Pretty-print structured content
            if isinstance(content, (list, dict)):
                try:
                    content_str = json.dumps(content, ensure_ascii=False, indent=1)
                except Exception:
                    content_str = str(content)
            else:
                content_str = str(content)

            return f"{sender}:\n{content_str}\n"

        filepath = workspace.run_base / filename
        with open(filepath, "w", encoding="utf-8") as f:
            for i, msg in enumerate(self.conversation_history, start=1):
                f.write(f"--- Message {i} ---\n")
                f.write(_format_message(msg))
                f.write("\n")

        print(f"Saved conversation history to {filepath}")
        return str(filepath)
    
    def _run_action_graph(self, agent_state: GlobalAgentState) -> GlobalAgentState:
        """
        Final run of ActionGraph
        - Raise Error if run result failed
        """
        namespace = {default_config.KEY_AGENT_STATE:{}}

        final_state = deepcopy(agent_state)

        self.action_graph.execute_action_graph(namespace)

        if self.action_graph.result is not None and self.action_graph.result.success:
            modified_inner_state = self.action_graph.result.namespace.get(default_config.KEY_AGENT_STATE, {})
            
            execution_log = {
                'sender': f"{self.task_type.value} agent", 
                'message': modified_inner_state
            }

            final_state[default_config.KEY_AGENT_MESSAGES].append(execution_log)
            if isinstance(modified_inner_state, dict):
                
                ALLOWED_SCHEMA_KEYS = default_config.ALLOWED_STATE_SCHEMA_KEYS

                for key, value in modified_inner_state.items():
                    if key in ALLOWED_SCHEMA_KEYS:
                        final_state[key] = value
                    
                    elif key in final_state and key != default_config.KEY_AGENT_MESSAGES:
                        final_state[key] = value
                    
            return final_state
        
        else:
            error_msg = self.action_graph.result.message if self.action_graph.result else "Unknown error"
            raise RuntimeError(f'Failed to run ActionGraph {self.node_id}: {error_msg}')

class TaskGraph:
    """Manages the entire Directed Acyclic Graph (DAG) of tasks."""
    def __init__(self, llm_config: LlmConfig, graph_config: GraphConfig):
        """Initialize the task graph with LLM client, system prompts, and retry limits."""
        self.max_retries_action: int = graph_config.ACTION_GRAPH_MAX_RETRIES
        self.max_retries_task: int = graph_config.TASK_GRAPH_MAX_RETRIES
        self.nodes: dict[str, TaskNode] = {}
        self.sys_instructions: str = load_prompt(agent_name=default_config.AGENT_NAME_MASTER)
        self.sys_instructions_refine: str = load_prompt(agent_name=default_config.AGENT_NAME_MASTER, key=default_config.PROMPT_KEY_MASTER_REFINE)
        target_model = getattr(llm_config, 'GEMINI_MODEL', None) or getattr(llm_config, 'OPENAI_MODEL', None)
        self.llm = get_chat_model(
            model_name=target_model,
            temperature=llm_config.TEMPERATURE,
            max_retries=getattr(llm_config, 'MAX_RETRIES', 2),
            timeout=llm_config.TIMEOUT
        )
        
    def to_dict(self) -> dict:
        """Serialize all task nodes keyed by their identifiers."""
        return {
            "nodes": {
                tid: node.to_dict() for tid, node in self.nodes.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict, llm_config: LlmConfig, graph_config: GraphConfig):
        """Rehydrate a TaskGraph from serialized data using the specified model."""
        graph = cls(llm_config, graph_config)
        for tid, node_data in data.get("nodes", {}).items():
            node = TaskNode.from_dict(node_data)
            graph.nodes[tid] = node
        return graph

    def add_task(self, task: TaskNode, replace: bool = False):
        """Insert a task node, optionally replacing an existing one with the same id."""
        if not isinstance(task.node_id, str) or not task.node_id:
            raise ValueError("task_id must be a non-empty string.")
        if task.node_id in self.nodes:
            if replace:
                self.nodes[task.node_id] = task
                logger.info(f"Replaced existing Task with id '{task.node_id}'.")
                return
            raise ValueError(f"Task with id '{task.node_id}' already exists. Pass replace=True to overwrite.")
        self.nodes[task.node_id] = task

    def apply_edits(self, plan: PydanticGraphModificationPlan):
        """
        Applies a list of atomic edits to the current graph.
        """
        logger.info(f"Applying Graph Plan: {plan.reasoning}")

        for edit in plan.edits:
            try:
                if edit.action == PydanticEditAction.ADD:
                    self._handle_add(edit.task)
                elif edit.action == PydanticEditAction.MODIFY:
                    self._handle_modify(edit.task)
                elif edit.action == PydanticEditAction.DELETE:
                    self._handle_delete(edit.target_task_id)
            except Exception as e:
                logger.error(f"Failed to apply edit {edit}: {e}")
                # Decide: Continue or Raise? Usually better to continue best-effort.

    def _handle_add(self, p_node):
        """Add a planned task node, warning if dependencies are missing."""
        if not p_node: 
            return
        # Create new node
        new_node = TaskNode(
            node_id=p_node.task_id,
            node_name=p_node.task_name,
            instruction=p_node.instruction,
            dependencies=p_node.dependencies,
            task_type=p_node.task_type,
            output=p_node.output,
            model=default_config.GEMINI_MODEL
        )
        # Verify dependencies exist
        missing_deps = [d for d in new_node.dependencies if d not in self.nodes]
        if missing_deps:
            logger.warning(f"Task {new_node.node_id} depends on unknown tasks: {missing_deps}. Adding anyway, but graph may break.")
        
        self.add_task(new_node)
        logger.info(f"Added Task {new_node.node_id}")

    def _handle_modify(self, p_node):
        """Update an existing task node’s instruction, dependencies, and output."""
        if not p_node or p_node.task_id not in self.nodes:
            logger.warning(f"Cannot modify unknown task {getattr(p_node, 'task_id', 'Unknown')}")
            return
        
        existing_node = self.nodes[p_node.task_id]
        
        existing_node.instruction = p_node.instruction
        existing_node.instruction = p_node.node_name
        existing_node.dependencies = p_node.dependencies
        existing_node.output = p_node.output
        existing_node.status = TaskStatus.PENDING
        logger.info(f"Modified Task {existing_node.node_id}")
    
    def _handle_delete(self, node_id: str):
        """Delete a task node and warn about any dependent tasks."""
        if node_id not in self.nodes:
            return
        
        dependents = [
            tid for tid, node in self.nodes.items() 
            if node_id in node.dependencies
        ]
        if dependents:
            logger.warning(f"Deleting task {node_id}; tasks {dependents} depend on it.")

        del self.nodes[node_id]
        logger.info(f"Deleted Task {node_id}")

    def _read_text_file(self, file_path: str) -> str:
        """Reads a text-based file (txt, csv, json, etc.) into a string."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return f"Error reading file: {file_path}"
    
    # def _synthesis_dataset_info(self, filepath: str) -> str:
    #     import io
    #     import pandas as pd
    #     df = pd.read_csv(filepath)

    #     buffer = io.StringIO()

    #     df.info(buf=buffer)

    #     return buffer.getvalue()
    

    def generate_plan(self, human_input:str, file_context: List[Dict[str, Any]], max_retries_action: int = None, max_retries_task: int = None):
        """Generates a task graph"""
        structured_llm = self.llm.with_structured_output(PydanticTaskGraph)

        messages = [
            SystemMessage(content= self.sys_instructions),
            HumanMessage(content=file_context),
            HumanMessage(content=f"User request: {human_input}")
        ]

        pydantic_response: PydanticTaskGraph = structured_llm.invoke(messages) # type: ignore

        for pydantic_node in pydantic_response.task_nodes:
            node_data = pydantic_node.model_dump()
            node = TaskNode(
                node_id=node_data["task_id"],
                node_name=node_data["task_name"],
                instruction=node_data["instruction"], 
                dependencies=node_data["dependencies"], 
                task_type=node_data["task_type"],
                output=node_data["output"],
                model=default_config.GEMINI_MODEL
            )
            self.add_task(node)
        
        if max_retries_action is not None:
            self.max_retries_action = max_retries_action
        if max_retries_task is not None:
            self.max_retries_task = max_retries_task

    def refine_plan(self, refine_instruction: str, file_context: List[Dict[str, Any]], history: List[BaseMessage] = [], max_retries_task: int = None, max_retries_action: int = None):
        """
        Takes an existing populated graph and asks the LLM to add/modify nodes
        based on new user input.
        """
        current_graph_summary = []
        for tid, node in self.nodes.items():
            current_graph_summary.append(
                f"- Task {tid} ({node.status.value}): {node.instruction}. Output: {node.output}"
            )
        current_graph_str = "\n".join(current_graph_summary)

        system_msg = (
            f"{self.sys_instructions}\n"
            f"{refine_instruction}\n"
            f"EXISTING WORKFLOW STATE:\n{current_graph_str}\n\n"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("system", "Current available files:\n{file_context}"),
            MessagesPlaceholder(variable_name="chat_history"),
        ])

        structured_llm = self.llm.with_structured_output(PydanticGraphModificationPlan)
        chain = prompt | structured_llm

        import json
        pydantic_response: PydanticGraphModificationPlan = chain.invoke({
            "file_context": json.dumps(file_context, indent=2), 
            "chat_history": history,
        })
        
        self.apply_edits(pydantic_response)
        if max_retries_task is not None:
          self.max_retries_action = max_retries_action
        if max_retries_task is not None:
          self.max_retries_task = max_retries_task

    def get_execution_order(self) -> list[str]:
        """
        Determines the execution order of tasks using topological sort.
        This is crucial for executing tasks in the correct sequence based on their dependencies.
        """
        graph_representation = {
            task_id: node.dependencies for task_id, node in self.nodes.items()
        }
        
        try:
            ts = TopologicalSorter(graph_representation)
            return list(ts.static_order())
        except CycleError as e:
            logger.error(f"Error: A cycle was detected in the task graph. Cannot determine execution order. Details: {e}")
            return []
        
    def _save_taskgraph_structure(
        self,
        sess_id: str | None = None,
        run_id: str | None = None,
        filename: str = default_config.FILENAME_TASK_GRAPH,
        include_actions: bool = True,
        ensure_dir: bool = True
    ) -> str:
        """
        Save a readable representation of the TaskGraph to a text file.
        If sess_id and run_id are provided the file is saved under
        session/{sess_id}/{run_id}/{filename}, otherwise saved in CWD.
        Returns the saved filepath as string.
        """
        from pathlib import Path

        if sess_id and run_id:
            dest_dir = Path(os.path.join(default_config.SESSION_FILEPATH, sess_id, run_id))
        else:
            dest_dir = Path(".")

        if ensure_dir:
            dest_dir.mkdir(parents=True, exist_ok=True)

        filepath = dest_dir / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("TaskGraph Structure\n")
                f.write(f"Total nodes: {len(self.nodes)}\n\n")

                for task_id, node in self.nodes.items():
                    node_type = getattr(node.task_type, "value", str(node.task_type))
                    f.write(f"Task ID: {task_id}\n")
                    f.write(f"  Status: {node.status.value}\n")
                    f.write(f"  Type: {node_type}\n")
                    f.write(f"  Dependencies: {node.dependencies or []}\n")
                    f.write("  Instruction:\n")
                    f.write(comment_block(node.instruction) + "\n")

                    if include_actions and getattr(node, "action_graph", None) and node.action_graph.nodes:
                        f.write("  Actions:\n")
                        for action in node.action_graph.nodes:
                            f.write(f"    - Action ID: {action.action_id}\n")
                            f.write(f"      Status: {action.status.value}\n")
                            f.write(f"      Description:\n")
                            f.write(comment_block(action.description) + "\n")
                    f.write("\n")

            logger.info(f"Saved taskgraph structure to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save taskgraph structure to {filepath}: {e}", exc_info=True)
            raise
    
    def _log_and_notify(self, message: str, progress_callback: Union[callable, None] = None, level: str = "info"):
        """
        Logs a message and optionally sends it to the progress callback.
        """
        # Handle Logging
        if level.lower() == "error":
            logger.error(message)
        elif level.lower() == "warning":
            logger.warning(message)
        else:
            logger.info(message)

        # Handle Progress Streaming to frontend
        if progress_callback:
            progress_callback(message)

    def save_code(self, sess_id:str, run_id: str, verbose: bool = True, ensure_dir=True, filename: str = default_config.FILENAME_CODE_SUMMARY):
        """Prints a summary of all tasks and their dependencies."""
        from pathlib import Path
        
        if not self.nodes:
            logger.warning("Graph is empty.")
            return
        
        if verbose:
            try:
                dest_dir = Path(os.path.join(default_config.SESSION_FILEPATH,sess_id,run_id))
                if ensure_dir:
                    dest_dir.mkdir(parents=True, exist_ok=True)
                filepath = dest_dir / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    
                    f.write(f"# RUN ID -- {run_id}\n\n")
                    for task_id, node in self.nodes.items():
                        f.write(f"# --- Task {task_id} ---\n")
                        f.write(f"# Instruction:\n")
                        f.write(comment_block(node.instruction))
                        if getattr(node, 'action_graph', None) and node.action_graph.nodes:
                            for action in node.action_graph.nodes:
                                f.write(f"# Action {action.action_id}:\n")
                                f.write(comment_block(action.description))
                                f.write(action.code + "\n\n")
                        else:
                            f.write("# No action graph available\n\n")
                logger.info(f"Saved action graphs codes to {filepath}")
            except Exception as e:
                logger.error(f"Failed to write action graphs to file: {e}", exc_info=True)
        
        #! Deprecated
        else:
            print("--- Task Graph ---")
            for task_id, node in self.nodes.items():
                print(f"  - ID: {task_id}, Status: {node.status.value}")
                print(f"    Instruction: {node.instruction}")
                print(f"    Dependencies: {node.dependencies or 'None'}")
            print("--------------------")
    
    def _update_node_progress(self, node_id: str, status: str, send_sse, sub_step_id=None):
        """Call this inside your Code Execution loop"""
        send_sse({
            "node_id": node_id,
            "status": status,
            "active_sub_step": sub_step_id
        }, "node_update")

    def execute_pipeline(self, initial_state: GlobalAgentState, workspace: SessionWorkspace, stop_on_failure: bool = False, progress_callback: Union[callable, None] = None, current_refinement_step: int = 0) -> GlobalAgentState:
        """
        Run tasks in topological order. For each TaskNode:
          - evaluate optional `condition` (simple eval with limited globals),
          - execute via TaskNode.iterate_refining(llm, agent_state),
          - update agent_state from action_graph result if present.
          - Raise RuntimeError if final run fails & stop_on_failure=True
        Returns final agent_state dict.
        """
        from time import sleep
        # ensure order
        order = self.get_execution_order()
        if not order:
            raise RuntimeError("No execution order (empty graph or cycle detected).")

        current_state: GlobalAgentState = deepcopy(initial_state)

        for tid in order:
            if tid not in self.nodes:
                logger.warning(f"Skipping unknown task id {tid}")
                continue

            node = self.nodes[tid]

            # Skip Success Nodes
            if node.status == TaskStatus.SUCCESS:
                logger.debug(f"Skipping already completed task {tid}")
                if node.result:
                    pass 
                continue
            
            # 1. Notify Start
            self._log_and_notify(f'Working on Task {node.node_name}', progress_callback=progress_callback)
            self._update_node_progress(node_id=node.node_id, status=TaskStatus.RUNNING, send_sse=progress_callback)
            
            # 2. Planning & Verification Phase
            node.execute_with_retry(global_agent_state=current_state, workspace=workspace, max_retries=self.max_retries_action)
            
            # 3. Handle Planning Failure
            if node.status is TaskStatus.FAILED:
                self._update_node_progress(node_id=node.node_id, status=TaskStatus.FAILED, send_sse=progress_callback)

                # Check if limit has reached
                if current_refinement_step >= self.max_retries_task:
                    error_msg = (f"Task {node.node_id} failed and max graph refinements "
                                 f"({default_config.MAX_GRAPH_REFINEMENTS}) reached. Stopping execution.")
                    
                    self._log_and_notify(error_msg, progress_callback=progress_callback, level="error")
                    
                    if stop_on_failure:
                        raise RuntimeError(error_msg)
                    else:
                        # Break the loop, return partial state, do not recurse
                        return current_state
                  
                # Recurse for refinement
                self._log_and_notify(f'{node.node_id} failed to run in {self.max_retries_action} trials. Refining TaskGraph...', progress_callback=progress_callback)
                self.refine_plan(refine_instruction=f'Task {node.node_id} failed to run within {default_config.ACTION_GRAPH_MAX_RETRIES} tries. Make some changes to the node instruction.')
                return self.execute_pipeline(
                    initial_state=current_state, # Pass accumulate state for debugging
                    workspace=workspace, 
                    stop_on_failure=stop_on_failure, 
                    progress_callback=progress_callback,
                    current_refinement_step=current_refinement_step + 1
                )
            
            # Final run that will change agent state
            try:
                current_state = node._run_action_graph(agent_state=current_state)
                sleep(0.5)

                # Assume Success
                node.status = TaskStatus.SUCCESS
                self._update_node_progress(node_id=node.node_id, status=TaskStatus.SUCCESS, send_sse=progress_callback)
               
                sleep(0.5)
            
            except RuntimeError as e:
                logger.error(f"Exception when running task {node.node_name}: {type(e).__name__}: {e}", exc_info=True)
                node.status = TaskStatus.FAILED
                self._update_node_progress(node_id=node.node_id, status=TaskStatus.FAILED, send_sse=progress_callback)
                sleep(0.5)
                if stop_on_failure:
                    raise e # Re-raise to stop pipeline
                else:
                    return self.execute_pipeline(
                    initial_state=current_state, # Pass accumulate state for debugging
                    workspace=workspace, 
                    stop_on_failure=stop_on_failure, 
                    progress_callback=progress_callback,
                    current_refinement_step=current_refinement_step + 1
                )
                    
        return current_state
