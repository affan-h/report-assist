import logging
from typing import Any, Dict, List, Union, Literal
from contextlib import contextmanager
from app.services.agent.bias_evaluator import BiasEvaluator
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, messages_to_dict, messages_from_dict
from core.config import default_config, AppSettings, LlmConfig, GraphConfig, Persona
from .schemas import AgentEvaluationResult, GlobalAgentState, MultiPersonaResponse, PersonaResponse, PydanticAnalysisResult, PydanticDiagramResult
from .utils import load_prompt, SessionWorkspace
from .file_utils import FileUtils
from .graph import TaskGraph
from .sub_agents import AnalysisAgent
from .llm_factory import get_chat_model

c_logger = logging.getLogger(default_config.CENTRAL_LOG_NAME)

class MasterAgent:
    def __init__(self, config: AppSettings, tools=[]):
        """Initialize master agent with LLM client, tools, prompts, and sub-agents."""
        self.graph_config: GraphConfig = config.graph_config
        self.personas: List[Persona] = config.personas
        self.llm_config: LlmConfig = config.llm_config
        target_model = getattr(self.llm_config, 'GEMINI_MODEL', None) or getattr(self.llm_config, 'OPENAI_MODEL', None) or default_config.GEMINI_MODEL
        self.llm = get_chat_model(
            model_name=target_model,
            temperature=self.llm_config.TEMPERATURE,
            max_retries=getattr(self.llm_config, 'MAX_RETRIES', 2),
            timeout=self.llm_config.TIMEOUT
        )
        self.tools = tools
        self.instructions_ans = load_prompt(agent_name=default_config.AGENT_NAME_MASTER, key=default_config.PROMPT_KEY_MASTER_ANS)
        self.instructions_user_req = load_prompt(agent_name=default_config.AGENT_NAME_MASTER, key=default_config.PROMPT_KEY_MASTER_REQ)
        self.task_graph: TaskGraph = TaskGraph(llm_config=self.llm_config, graph_config=self.graph_config)
        self.analysis_agent = AnalysisAgent(model=target_model)
        self.bias_evaluator = BiasEvaluator()
        self.conversation_history: List[BaseMessage] = []
  
    def _get_history_file_path(self, workspace: SessionWorkspace) -> str:
        """
        Constructs the path for the session-level history file.
        It should be outside the specific run folder, in the session root.
        """
        import os
        session_dir = os.path.dirname(workspace.run_base) 
        return os.path.join(session_dir, default_config.FILENAME_SESSION_HISTORY)

    def _load_conversation_history(self, workspace: SessionWorkspace, logger: logging.Logger):
        """Loads existing conversation history from JSON."""
        import os, json
        history_path = self._get_history_file_path(workspace)
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = messages_from_dict(data)
                c_logger.info(f"Loaded {len(self.conversation_history)} messages.")
            except Exception as e:
                c_logger.error(f"Failed to load history: {e}")
                self.conversation_history = []
        else:
            self.conversation_history = []

    def _save_conversation_history(self, workspace: SessionWorkspace, logger: logging.Logger) -> str:
        """Saves current conversation history to JSON."""
        import json
        history_path = self._get_history_file_path(workspace)
        try:
            messages_data = messages_to_dict(self.conversation_history)
            
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved history to {history_path}")
        except Exception as e:
            logger.error(f"Failed to save history: {e}")

    @contextmanager
    def _session_logger(self, workspace: SessionWorkspace):
        """Context manager to handle session-specific logging setup/teardown."""
        log_path = workspace.get_log_path()

        handler = logging.FileHandler(log_path)
        sess_formatter = logging.Formatter(default_config.SESS_LOG_FORMAT)
        handler.setFormatter(sess_formatter)
        handler.setLevel(logging.DEBUG)
        
        sess_logger = logging.getLogger(default_config.SESS_LOG_NAME)
        sess_logger.setLevel(logging.DEBUG)
        sess_logger.addHandler(handler)

        # setup handler
        sess_logger = logging.getLogger(default_config.SESS_LOG_NAME)
        sess_logger.addHandler(handler)
        try:
            yield sess_logger
        finally:
            sess_logger.removeHandler(handler)
            handler.close()

    def _initialize_agent_state(self, workplace:SessionWorkspace, requirement:str, file_list: List[str]) -> GlobalAgentState:
        """Create the initial agent state payload for a run."""
        state = GlobalAgentState(sess_id=workplace.sess_id, run_id=workplace.run_id, requirement=requirement, num_steps=0, raw_data_filenames=file_list, evaluation_results=[], visualization_paths=[], agent_messages=[], neutral_report='this is default report placeholder')
        return state
    
    def _synthesize_reports(self, requirement: str, perspectives: List[PersonaResponse]) -> str:
        """The Neutral Arbitrator Logic"""
    
        # Combine all biased reports into one context block
        debate_transcript = ""
        for p in perspectives:
            debate_transcript += f"--- {p['role']} says: ---\n{p['content']}\n\n"

        system_prompt = (
            "You are the Neutral Arbitrator.\n"
            "You have received conflicting analyses from biased agents.\n"
            "Your Goal:\n"
            "1. Strip away the emotional/subjective language.\n"
            "2. Merge the factual findings into a perfectly neutral executive summary.\n"
            "3. Explicitly mention where the agents disagreed."
            "4. When discussing a specific insight that is visualized in a chart or diagram, insert the chart/diagram immediately after the explanation using the format <<<filename>>>. Do not invent filenames, only use the one listed. Example Output: Here is the summary of Q1.\n <<<sales_q1.png>>>"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"User Goal: {requirement}\n\nDEBATE TRANSCRIPT:\n{debate_transcript}")
        ]

        return self.llm.invoke(messages).content
    
    def _generate_final_report(self, state: GlobalAgentState) -> MultiPersonaResponse:
        """Generate the final user-facing answer from the aggregated state."""
        messages = [
            SystemMessage(content= self.instructions_ans),
            AIMessage(content=f'analysis results:{str(state["analysis_result"])}'),
            HumanMessage(content=f'user question: {str(state["requirement"])}'),
        ]
        response_content: str = self.llm.invoke(messages).content

        return MultiPersonaResponse(text=response_content, run_id=state['run_id'], figures=state['analysis_result'].figures)
    
    #! Not in use
    def _summarize_user_request(self, human_req: str) -> str:
        """Summarize the user request with the master prompt."""
        messages = [
            SystemMessage(content= self.instructions_user_req),
            HumanMessage(content=f'user request:{human_req}'),
        ]

        response = self.llm.invoke(messages)
        return response.text
    
    def _log_and_notify(self, message: str, logger: logging.Logger, progress_callback: Union[callable, None] = None, level: str = "info"):
        """
        Logs a message and optionally sends it to the progress callback.
        """
        if level.lower() == "error":
            logger.error(message)
        elif level.lower() == "warning":
            logger.warning(message)
        else:
            logger.info(message)

        if progress_callback:
            progress_callback(message)
    
    def run_request_demo(self,
                    human_input: str, 
                    file_list: List[str], 
                    workspace: SessionWorkspace,
                    progress_callback=None) -> MultiPersonaResponse:
        """Demo pathway: analyze existing figures and produce a final answer."""
        
        final_output = MultiPersonaResponse(
                    run_id="run_12345_abcde",
                    text="## Consolidated Financial Analysis\n\nBased on the multi-perspective review, the company demonstrates strong fundamentals but faces short-term volatility risks.\n\n### Key Findings\n1. **Revenue Growth**: Year-over-year revenue has increased by 15%, driven largely by the new cloud division.\n2. **Risk Factors**: Supply chain disruptions in the semiconductor sector remain a primary concern.\n\n### Conclusion\nThe consensus suggests a **Hold** rating for short-term investors, while long-term value investors may find the current dip an attractive entry point.",
                    perspectives=[
          {
            "role": "The Optimistic",
            "persona": "Focus on growth metrics, upside potential, and opportunities.",
            "icon": "📈",
            "content": "Strong upside momentum observed across key performance indicators. The top-line growth trajectory suggests robust expansion potential.",
            "metrics": {"bias_score": 0.75, "neutrality_index": 0.25, "polarity": 0.65}
          },
          {
            "role": "The Pessimistic",
            "persona": "Focus on liabilities, downside risks, and cost pressures.",
            "icon": "📉",
            "content": "Underlying cost pressures and volatility present significant downside risks. Margin compression may threaten sustainability.",
            "metrics": {"bias_score": -0.72, "neutrality_index": 0.28, "polarity": -0.58}
          },
          {
            "role": "The Skeptic",
            "persona": "Doubt data integrity and methodology.",
            "icon": "🕵️",
            "content": "The sample size exhibits potential selection bias and seasonal confounding factors that warrant skeptical verification.",
            "metrics": {"bias_score": -0.15, "neutrality_index": 0.85, "polarity": -0.05}
          }
        ],
                    figures=[]
                )
        return final_output
     
        # return FinalAnswer(text="Result.", run_id=workspace.run_id, figures=[PydanticDiagramResult(filename="gold_annual_returns.png", text="Analysis Result")])
        with self._session_logger(workspace) as logger:
            try:
                state = self._initialize_agent_state(workplace=workspace, requirement=human_input, file_list=[])
                diagram_paths = workspace.list_figures()
                state['visualization_paths'] = diagram_paths
                self._log_and_notify('Analysis in Progress', logger=logger, progress_callback=progress_callback)
                final_state = self.analysis_agent.analyze_all_diagrams(state=state, prompt=f'Give insights on these diagrams regarding user request:{state["requirement"]}')
                self._log_and_notify('Fabricating Final Answer', logger=logger, progress_callback=progress_callback)
                final_result = self._synthesis_reports(final_state)
                logger.info(final_result)
                return final_result

            except Exception as e:
                logger.error(f"Run failed: {e}", exc_info=True)
                return MultiPersonaResponse(text=default_config.ERROR_MSG_EXECUTION_FAILED, run_id=workspace.run_id)
    
    def _broadcast_graph_structure(self, send_sse):
        """Call this when the Planner Agent finishes creating the TaskGraph"""
        nodes = []
        edges = []
        
        execution_order: list[str] = self.task_graph.get_execution_order()
        if not execution_order:
            return

        for tid in self.task_graph.nodes:
            node = self.task_graph.nodes[tid]
            # 1. Build Node
            nodes.append({
                "id": node.node_id,
                "label": node.node_name,
                "status": node.status,
                "description": node.instruction,
                # Extract action steps for detailed view
                "sub_steps": [
                    {"id": action.action_id, "desc": action.description}
                    for action in node.action_graph.nodes
                ]
            })
            
            # 2. Build Edges
            for dep in node.dependencies:
                edges.append({"source": dep, "target": node.node_id})

        send_sse({"nodes": nodes, "edges": edges}, "graph_init")

    def run_request(self, 
                    human_input: str, 
                    file_list: List[str],
                    workspace: SessionWorkspace,
                    analyze_only = False,
                    progress_callback=None) -> MultiPersonaResponse:
        """Full workflow: build/refine task graph, execute tasks, analyze diagrams, and craft answer."""
        
        import time
        from copy import deepcopy
        workspace = SessionWorkspace(workspace.sess_id, workspace.run_id)
        
        start_time = time.time()
        log_summary = {
            'sess_id': workspace.sess_id,
            'run_id': workspace.run_id,
            'user_request': human_input,
            'model':{'name':self.llm_config.OPENAI_MODEL,'timeout':self.llm_config.TIMEOUT,'cache':self.llm_config.CACHE,'temperature':self.llm_config.TEMPERATURE,'max_tokens':self.llm_config.MAX_COMPLETION_TOKENS}
        }
        status = default_config.STATUS_FAILED

        initial_state: GlobalAgentState = self._initialize_agent_state(workplace=workspace, requirement=human_input, file_list=file_list)
        workflow_state: GlobalAgentState = deepcopy(initial_state)
        agent_state_version = {'initial':initial_state}

        # Settings from Frontend --
        max_retries_action = self.graph_config.ACTION_GRAPH_MAX_RETRIES
        max_retries_task = self.graph_config.TASK_GRAPH_MAX_RETRIES
        # --

        with self._session_logger(workspace) as logger:
            try:
                
                self._load_conversation_history(workspace, logger=logger)
                self.conversation_history.append(
                    HumanMessage(content=human_input, additional_kwargs={"run_id": workspace.run_id})
                )
                file_context: List[Dict[str, Any]] = FileUtils.format_files_for_llm(file_list, workspace.data_dir)

                # Initialize and run the LangGraph StateGraph workflow
                from .workflow import create_report_assist_workflow
                self._log_and_notify("Initializing LangGraph multi-agent execution pipeline...", logger=logger, progress_callback=progress_callback)

                workflow_app = create_report_assist_workflow(
                    master_agent=self,
                    workspace=workspace,
                    progress_callback=progress_callback
                )

                initial_lg_state = {
                    "sess_id": workspace.sess_id,
                    "run_id": workspace.run_id,
                    "requirement": human_input,
                    "raw_data_filenames": file_list,
                    "file_context": file_context,
                    "task_graph_dict": None,
                    "visualization_paths": [],
                    "selected_diagrams": [],
                    "persona_insights": [],
                    "evaluated_results": [],
                    "neutral_report": None,
                    "pipeline_success": False,
                    "error_message": None
                }

                final_lg_state = workflow_app.invoke(initial_lg_state)

                neutral_report = final_lg_state.get("neutral_report") or "Analysis completed successfully."
                evaluated_insights = final_lg_state.get("evaluated_results") or []
                visualization_paths = final_lg_state.get("visualization_paths") or []

                self.conversation_history.append(
                    AIMessage(content=neutral_report, additional_kwargs={"run_id": workspace.run_id})
                )

                final_output = MultiPersonaResponse(
                    run_id=workspace.run_id,
                    text=neutral_report,
                    perspectives=evaluated_insights,
                    figures=visualization_paths
                )

                status = default_config.STATUS_SUCCESS
                return final_output
            
            except Exception as e:
                c_logger.error(f"Run failed: {e}")
                logger.error(f"Run failed: {e}", exc_info=True)
                raise RuntimeError(default_config.ERROR_MSG_EXECUTION_FAILED)
            
            finally:
                self._save_conversation_history(workspace, logger=logger)
                workspace.save_graph_state(self.task_graph.to_dict())
                self.task_graph.save_code(sess_id=initial_state['sess_id'], run_id=initial_state['run_id'], verbose=True)

                logger.info('Saved TaskGraph and Conversation History')

                # Generate Request Summary
                duration_sec = time.time() - start_time
                log_summary['status'] = status
                log_summary['duration_sec'] = round(duration_sec, 2)
                c_logger.info(
                    f"Finished request",
                    extra=log_summary
                )
                workspace.save_json(data=agent_state_version)
                logger.info(f"Closing log handler for Run ID {workspace.run_id}")


def get_master_agent(config: AppSettings):
    """Factory helper to construct a MasterAgent with the default model."""
    return MasterAgent(config=config)