from enum import Enum
from typing import Optional, TypedDict, List, Any
from pydantic import BaseModel, Field

# --- Enums ---

class TaskStatus(str, Enum):
    """Execution status for a task or action node."""
    SUCCESS = "success"
    FAILED = "failed" 
    PENDING = "pending"
    RUNNING = "running"

class TaskType(str, Enum):
    """Categories of data science workflow tasks."""
    DATA_LOADING = "data_loading"
    EXPLORATION = "exploration"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    EVALUATION = "evaluation"
    VISUALIZATION = "visualization"

# --- Pydantic Schemas for Structured Output ---

class PydanticActionNode(BaseModel):
    action_id: int = Field(..., description="The sequential ID of the action node in numbers only.")
    description: str = Field(..., description="A brief natural language description of what the action does.")
    code: str = Field(..., description="A valid, self-contained, executable Python code snippet.")

class PydanticActionGraph(BaseModel):
    task_nodes: List[PydanticActionNode] = Field(default=[], description="List of action nodes to execute for the specific task.")

class PydanticTaskNode(BaseModel):
    task_id: str = Field(..., description="Unique ID for the task (e.g., '1', '2').")
    task_name: str = Field(..., description="Human-readable name for the task.")
    dependencies: List[str] = Field(default=[], description="List of task_ids that must complete before this task.")
    instruction: str = Field(..., description="Concise instruction on what this task must accomplish.")
    task_type: TaskType = Field(description="Primary category of the task.")
    output: str = Field(..., description="Description of the expected output artifacts or files.")

class PydanticTaskGraph(BaseModel):
    task_nodes: List[PydanticTaskNode] = Field(..., description="Structured DAG of tasks required to fulfill the user request.")

class PydanticEditAction(str, Enum):
    ADD = "add"       
    MODIFY = "modify" 
    DELETE = "delete" 

class PydanticGraphEdit(BaseModel):
    action: PydanticEditAction = Field(..., description="The type of modification to apply.")
    task: Optional[PydanticTaskNode] = Field(None, description="Task details required for ADD and MODIFY.")
    target_task_id: Optional[str] = Field(None, description="Task ID to DELETE.")

class PydanticGraphModificationPlan(BaseModel):
    reasoning: str = Field(..., description="Explanation of why these graph edits fulfill the revised requirement.")
    edits: List[PydanticGraphEdit] = Field(..., description="List of atomic graph edits.")

class PydanticAnalysisResult(BaseModel):
    summary: str = Field(..., description="Persuasive narrative and analytical insights from the assigned persona perspective.")

class PydanticForecastResult(BaseModel):
    forecast: List[str] = Field(..., description="Forecasted future trends or values.")
    text: str = Field(..., description="Explanation supporting the forecast.")

# --- TypedDicts & Runtime State ---

class AgentMessage(TypedDict):
    sender: str
    content: Any

class PersonaResponse(TypedDict):
    role: str
    persona: str
    icon: str
    content: PydanticAnalysisResult | PydanticForecastResult

# --- Bias Evaluation ---

class BiasMetrics(BaseModel):
    bias_score: float       # -1.0 (The Pessimistic) to +1.0 (The Optimistic)
    neutrality_index: float # 0.0 (Extreme Bias) to 1.0 (Completely Neutral)
    polarity: float         # Sentiment polarity (-1.0 to 1.0)

class AgentEvaluationResult(BaseModel):
    role: str
    persona: str
    icon: str
    content: str
    metrics: BiasMetrics

class GlobalAgentState(TypedDict):
    sess_id: str
    run_id: str
    requirement: str
    num_steps: int
    raw_data_filenames: List[str]
    visualization_paths: List[str]
    analysis_result: List[AgentEvaluationResult]
    neutral_report: Optional[str]
    agent_messages: List[AgentMessage]

class MultiPersonaResponse(TypedDict):
    run_id: str
    text: str
    perspectives: List[AgentEvaluationResult]
    figures: List[str]
