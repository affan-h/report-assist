import os, json
from pathlib import Path
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from typing import List, Optional, Dict, Any, Type

import matplotlib
matplotlib.use('Agg')

ROOT = Path(__file__).resolve().parents[1]

class PathSettings(BaseSettings):
    """File system paths and storage configurations."""
    TEMP_FILEPATH: str = Field('tmp', description="Temporary storage")
    DATA_FILEPATH: str = Field('data', description="Shared session data")
    SESSION_FILEPATH: str = Field('session', description="Session artifacts")
    FIGURE_FILEPATH: str = Field('figures', description="Generated images")
    MODEL_FILEPATH: str = Field('model', description="Saved models")
    
    VISUAL_ALLOWED_EXTENSIONS: List[str] = ['*.png', '*.jpg', '*.jpeg', '*.pdf']

class LogSettings(BaseSettings):
    """Logging configurations."""
    SESS_LOG_NAME: str = 'sess_log'
    SESS_LOG_FILENAME: str = 'sess.log'
    SESS_LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    CENTRAL_LOG_DIR: str = 'logs'
    CENTRAL_LOG_FILENAME: str = 'central.log'
    CENTRAL_LOG_NAME: str = 'api_gateway'

    STATUS_SUCCESS: str = 'SUCCESS'
    STATUS_FAILED: str = 'FAILED'
    ERROR_MSG_EXECUTION_FAILED: str = "An error occurred during execution."

class ServerSettings(BaseSettings):
    """FastAPI Server settings."""
    ENV: str = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    UUID_LEN: int = 8

    # Timeouts & Intervals
    API_TIMEOUT: int = Field(30, description="General request timeout in seconds")
    KEEPALIVE_INTERVAL: int = Field(15, description="Ping interval in seconds for SSE keepalive")

class FileSystemConfig(BaseSettings):
    FILENAME_CONVERSATION_HISTORY: str = "conversation_history.txt"
    FILENAME_TASK_GRAPH: str = "taskgraph_structure.txt"
    FILENAME_CODE_SUMMARY: str = "code.py"
    FILENAME_SESSION_HISTORY: str = "session_history.json"
    FILENAME_AGENT_STATE: str = "agent_state.json"
    FILENAME_TASK_GRAPH_STATE: str = "task_graph_state.json"
    FILENAME_SETTINGS: str = "settings.json"
    
class DefaultLlmConfig(BaseSettings):
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = Field(default=None, validation_alias="GOOGLE_API_KEY")
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.3
    GEMINI_MAX_RETRIES: int = 2
    GEMINI_TIMEOUT: Optional[int] = 300

    # Optional OpenAI fallback
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.3
    OPENAI_MAX_RETRIES: int = 2

class GraphSettings(BaseSettings):
    ACTION_GRAPH_MAX_RETRIES: int = 5
    TASK_GRAPH_MAX_RETRIES: int = 3
    MAX_GRAPH_REFINEMENTS: int = 3
    
class AgentSettings(BaseSettings):
    """Workflow and Agent logic configuration."""
    AGENT_NAME_CODE: str = "code"
    AGENT_NAME_MASTER: str = "master"
    AGENT_NAME_ANALYSIS: str = "analysis"

    PROMPT_KEY_UNIVERSAL_SYSTEM: str = "system_prompt"
    PROMPT_KEY_MASTER_ANS: str = "system_prompt_ans"
    PROMPT_KEY_MASTER_REQ: str = "system_prompt_user_req"
    PROMPT_KEY_MASTER_REFINE: str = "system_prompt_refine"
    PROMPT_KEY_FORECAST: str = "system_prompt_forecast"
    PROMPT_KEY_ANALYSIS_USER: str = "prompt_user_instruction"
    PROMPT_KEY_CODE_REPLAN: str = "system_prompt_replan"

    KEY_AGENT_STATE: str = "agent_state"
    KEY_AGENT_MESSAGES: str = "agent_messages"

    ALLOWED_STATE_SCHEMA_KEYS: set = {
        "visualization_paths", 
        "evaluation_results", 
        "processed_path",
        "data_path"
    }

    DEFAULT_PERSONAS: List[dict] = [
        {"role": "The Optimistic", "icon": "📈", "injected_persona": "Focus strictly on growth metrics, upside potential, and opportunities. Highlight positive momentum and ignore risks."},
        {"role": "The Pessimistic", "icon": "📉", "injected_persona": "Focus strictly on liabilities, downside risks, cost pressures, and volatility. Be skeptical of growth metrics."},
        {"role": "The Skeptic", "icon": "🕵️", "injected_persona": "Doubt data integrity and methodology. Look for anomalies, small sample sizes, and spurious correlations."}
    ]

class LogicSettings(BaseSettings):
    HISTORY_CONTEXT_WINDOW: int = 5 
    LOG_PREVIEW_LENGTH: int = 30

class BaseConfig(
    ServerSettings, 
    PathSettings, 
    LogSettings, 
    AgentSettings, 
    GraphSettings,
    DefaultLlmConfig,
    FileSystemConfig,
    LogicSettings,
    BaseSettings
):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

class TestConfig(BaseConfig):
    pass

class LocalConfig(BaseConfig):
    pass

class ProductionConfig(BaseConfig):
    DEBUG: bool = False

def get_config() -> BaseConfig:
    env = os.getenv("ENV", "local")
    if env == "test":
        return TestConfig()
    elif env == "prod":
        return ProductionConfig()
    return LocalConfig()

default_config = get_config()
SETTINGS_FILE = ROOT / default_config.FILENAME_SETTINGS

# --- Sub-Models for Nested Structures ---

class LlmConfig(BaseModel):
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = default_config.GEMINI_API_KEY
    GEMINI_MODEL: str = default_config.GEMINI_MODEL
    TEMPERATURE: float = default_config.GEMINI_TEMPERATURE
    TIMEOUT: Optional[int] = default_config.GEMINI_TIMEOUT
    MAX_RETRIES: int = default_config.GEMINI_MAX_RETRIES

    # Optional OpenAI fallback
    OPENAI_API_KEY: Optional[str] = default_config.OPENAI_API_KEY
    OPENAI_MODEL: str = default_config.OPENAI_MODEL

class GraphConfig(BaseModel):
    ACTION_GRAPH_MAX_RETRIES: int = default_config.ACTION_GRAPH_MAX_RETRIES
    TASK_GRAPH_MAX_RETRIES: int = default_config.TASK_GRAPH_MAX_RETRIES

class Persona(BaseModel):
    role: str
    icon: str
    injected_persona: str

class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field, field_name):
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        if not SETTINGS_FILE.exists():
            return {}
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings.json: {e}")
            return {}

class AppSettings(BaseSettings):
    prompts: Dict[str, Dict[str, str]] = {} 
    personas: List[Persona] = []
    llm_config: LlmConfig = LlmConfig()
    graph_config: GraphConfig = GraphConfig()

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore"
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ):
        return (
            init_settings,
            env_settings, 
            JsonConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
