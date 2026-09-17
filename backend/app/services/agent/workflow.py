"""
LangGraph Multi-Agent Workflow Engine for report-assist.

This module coordinates the end-to-end data analysis pipeline using LangGraph:
  1. [Planner Node]: Analyzes user query & uploaded datasets to construct a Directed Acyclic Graph (DAG) of tasks.
  2. [Executor Node]: Compiles task nodes into Python code, executes them sequentially, and captures output/visuals.
  3. [Curator Node]: Multimodal curation selecting the top key visualizations relevant to the analytical objective.
  4. [Persona Debate Node]: Concurrent analysis using contrasting personas (The Optimistic, The Pessimistic, The Skeptic) via Google Gemini.
  5. [Bias Evaluator Node]: Computes empirical bias vectors and neutrality indices using SentenceTransformer embeddings.
  6. [Neutral Synthesizer Node]: Reconciles persona disagreements into a balanced, objective executive summary.
"""

import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from core.config import default_config
from .schemas import AgentEvaluationResult, PersonaResponse, GlobalAgentState

logger = logging.getLogger(default_config.CENTRAL_LOG_NAME)


class ReportAssistState(TypedDict):
    """
    Typed state passed across all nodes in the LangGraph workflow.
    """
    sess_id: str
    run_id: str
    requirement: str
    raw_data_filenames: List[str]
    file_context: List[Dict[str, Any]]
    task_graph_dict: Optional[Dict[str, Any]]
    visualization_paths: List[str]
    selected_diagrams: List[str]
    persona_insights: List[PersonaResponse]
    evaluated_results: List[AgentEvaluationResult]
    neutral_report: Optional[str]
    pipeline_success: bool
    error_message: Optional[str]


def create_report_assist_workflow(master_agent, workspace, progress_callback=None):
    """
    Constructs and compiles the LangGraph StateGraph workflow for report-assist.
    
    Args:
        master_agent: MasterAgent instance with LLM, task_graph, and sub_agents.
        workspace: SessionWorkspace managing filesystem paths.
        progress_callback: Callback for streaming SSE events to the frontend.
    """

    # -------------------------------------------------------------
    # Node 1: Planner Node (Task Decomposition)
    # -------------------------------------------------------------
    def planner_node(state: ReportAssistState) -> Dict[str, Any]:
        """
        Decomposes user objective and uploaded datasets into a structured TaskGraph.
        """
        if progress_callback:
            progress_callback("Planning analytical workflow DAG with Gemini...")

        file_context = state.get("file_context", [])
        human_input = state["requirement"]

        previous_state = workspace.load_graph_state()
        if previous_state:
            if progress_callback:
                progress_callback("Restoring previous session state and refining plan...")
            master_agent.task_graph.refine_plan(
                file_context=file_context,
                history=master_agent.conversation_history,
                refine_instruction=master_agent.task_graph.sys_instructions_refine
            )
        else:
            master_agent.task_graph.generate_plan(
                human_input=human_input,
                file_context=file_context
            )

        # Broadcast DAG structure to frontend for React Flow rendering
        master_agent._broadcast_graph_structure(send_sse=progress_callback)
        workspace.save_graph_state(master_agent.task_graph.to_dict())

        return {
            "task_graph_dict": master_agent.task_graph.to_dict(),
            "pipeline_success": True
        }

    # -------------------------------------------------------------
    # Node 2: Executor Node (Code Generation & Execution)
    # -------------------------------------------------------------
    def executor_node(state: ReportAssistState) -> Dict[str, Any]:
        """
        Iterates over tasks in topological order, generates Python snippets,
        executes them in an isolated namespace, and saves generated figures.
        """
        if progress_callback:
            progress_callback("Executing data processing and visualization pipeline...")

        initial_agent_state: GlobalAgentState = master_agent._initialize_agent_state(
            workplace=workspace,
            requirement=state["requirement"],
            file_list=state["raw_data_filenames"]
        )

        workflow_state = master_agent.task_graph.execute_pipeline(
            initial_state=initial_agent_state,
            workspace=workspace,
            progress_callback=progress_callback,
            stop_on_failure=False
        )

        diagram_paths = workspace.list_figures()
        master_agent.task_graph.save_code(
            sess_id=state["sess_id"],
            run_id=state["run_id"]
        )

        return {
            "visualization_paths": diagram_paths,
            "pipeline_success": True
        }

    # -------------------------------------------------------------
    # Node 3: Visual Curator Node (Multimodal Diagram Selection)
    # -------------------------------------------------------------
    def curator_node(state: ReportAssistState) -> Dict[str, Any]:
        """
        Selects the top most informative diagrams for multi-perspective debate.
        """
        all_diagrams = state.get("visualization_paths", [])
        if not all_diagrams:
            logger.info("No diagrams generated to curate.")
            return {"selected_diagrams": []}

        if progress_callback:
            progress_callback(f"Curating key visualizations for deep analysis ({len(all_diagrams)} generated)...")

        synthetic_state: GlobalAgentState = {
            "sess_id": state["sess_id"],
            "run_id": state["run_id"],
            "requirement": state["requirement"],
            "num_steps": 0,
            "raw_data_filenames": state["raw_data_filenames"],
            "visualization_paths": all_diagrams,
            "analysis_result": [],
            "neutral_report": None,
            "agent_messages": []
        }

        selected = master_agent.analysis_agent.select_key_diagrams(
            state=synthetic_state,
            max_items=5
        )
        return {"selected_diagrams": selected}

    # -------------------------------------------------------------
    # Node 4: Persona Debate Node (Multimodal Gemini Agents)
    # -------------------------------------------------------------
    def debate_node(state: ReportAssistState) -> Dict[str, Any]:
        """
        Consults contrasting personas (The Optimistic, The Pessimistic, The Skeptic)
        in parallel using Gemini Vision.
        """
        selected_diagrams = state.get("selected_diagrams", [])
        personas = master_agent.personas

        if progress_callback:
            progress_callback(f"Initiating multi-persona debate across {len(personas)} perspectives...")

        workflow_state = {
            "requirement": state["requirement"],
            "visualization_paths": selected_diagrams
        }

        collected_insights = master_agent.analysis_agent.analyze_diagrams_with_all_personas(
            workflow_state=workflow_state,
            diagram_paths=selected_diagrams,
            personas=personas,
            logger=logger
        )

        return {"persona_insights": collected_insights}

    # -------------------------------------------------------------
    # Node 5: Bias Evaluator Node (Semantic Vector Projection)
    # -------------------------------------------------------------
    def evaluator_node(state: ReportAssistState) -> Dict[str, Any]:
        """
        Quantifies empirical bias scores (-1.0 to +1.0) and Neutrality Index (0.0 to 1.0)
        via SentenceTransformer embedding distance to anchor vectors.
        """
        insights = state.get("persona_insights", [])
        if progress_callback:
            progress_callback("Computing empirical bias vectors & neutrality indices...")

        evaluated = master_agent.bias_evaluator.evaluate_batch(agent_responses=insights)
        return {"evaluated_results": evaluated}

    # -------------------------------------------------------------
    # Node 6: Neutral Synthesizer Node (Arbitrator Synthesis)
    # -------------------------------------------------------------
    def synthesizer_node(state: ReportAssistState) -> Dict[str, Any]:
        """
        Neutral Arbitrator synthesizes conflicting viewpoints into an objective,
        balanced report, embedding figure tags like <<<filename.png>>>.
        """
        if progress_callback:
            progress_callback("Synthesizing objective neutral report...")

        insights = state.get("persona_insights", [])
        neutral_report = master_agent._synthesize_reports(
            requirement=state["requirement"],
            perspectives=insights
        )

        return {"neutral_report": neutral_report}

    # -------------------------------------------------------------
    # Build LangGraph StateGraph Architecture
    # -------------------------------------------------------------
    workflow = StateGraph(ReportAssistState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("curator", curator_node)
    workflow.add_node("debate", debate_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Sequential edges with clear transitions
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "curator")
    workflow.add_edge("curator", "debate")
    workflow.add_edge("debate", "evaluator")
    workflow.add_edge("evaluator", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()
