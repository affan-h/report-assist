import base64
from contextlib import contextmanager
import logging
from typing import Any, Dict, List, Union, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, messages_to_dict, messages_from_dict
from core.config import default_config, AppSettings, LlmConfig, GraphConfig, Persona
from .schemas import MultiPersonaResponse, PersonaResponse, PydanticForecastResult
from .utils import load_prompt, SessionWorkspace
from .file_utils import FileUtils
from .graph import TaskGraph
from .sub_agents import AnalysisAgent
from langchain_google_genai import ChatGoogleGenerativeAI

c_logger = logging.getLogger(default_config.CENTRAL_LOG_NAME)

ProviderType = Literal["openai", "gemini", "grok"]

class ForecastAgent:
    def __init__(self, config: AppSettings, model: str = default_config.OPENAI_MODEL, provider: ProviderType = "openai"):
        self.system_prompt_forecast = load_prompt(agent_name=default_config.AGENT_NAME_ANALYSIS,key=default_config.PROMPT_KEY_FORECAST)
        self.personas: List[Persona] = config.personas
        self.provider = provider
        self.model_name = model
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        """Factory method to return the correct LangChain chat model."""
        if self.provider == "openai":
            return ChatOpenAI(
                model=self.model_name,
                openai_api_key=default_config.OPENAI_API_KEY,
                temperature=default_config.OPENAI_TEMPERATURE,
                max_completion_tokens=default_config.OPENAI_MAX_COMPLETION_TOKENS,
                timeout=default_config.OPENAI_TIMEOUT,
                max_retries=default_config.OPENAI_MAX_RETRIES
            )
            
        elif self.provider == "gemini":
            return ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=default_config.GEMINI_API_KEY, # Ensure this exists in your config
                temperature=default_config.OPENAI_TEMPERATURE,
                max_output_tokens=default_config.OPENAI_MAX_COMPLETION_TOKENS,
                timeout=default_config.OPENAI_TIMEOUT,
                convert_system_message_to_human=True # Sometimes needed for older Gemini models
            )

        elif self.provider == "grok":
            return ChatOpenAI(
                model=self.model_name, # e.g., "grok-vision-beta"
                openai_api_key=default_config.XAI_API_KEY, # Ensure this exists in your config
                base_url="https://api.x.ai/v1",
                temperature=default_config.OPENAI_TEMPERATURE,
                max_completion_tokens=default_config.OPENAI_MAX_COMPLETION_TOKENS,
                timeout=default_config.OPENAI_TIMEOUT
            )
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _encode_image(self, image_path: str):
        """Helper function to encode image to base64."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
    def forecast_with_persona(self, diagram_paths: List[str], persona: Persona, user_prompt: str) -> str:
        """
        Encodes the image and asks the vision model a question about it.
        """
        import os

        image_content = []
        for path in diagram_paths:
            filename = os.path.basename(path)
            image_content.extend([
                {
                    "type": "text", 
                    "text": f"Image Filename: {filename}"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{self._encode_image(path)}"
                    }
                }
            ])

        dynamic_system_prompt = (
            f"You are acting as: {persona.role}.\n"
            f"Your Core Bias: {persona.bias_instruction}.\n"
            f"{self.system_prompt_forecast}"
        )

        user_instruction = (
            f"User Request: {user_prompt}\n\n"
        )

        messages = [
            SystemMessage(content=dynamic_system_prompt),
            HumanMessage(content=[
                {"type": "text", "text": user_instruction},
                *image_content 
            ])
        ]

        structured_llm = self.llm.with_structured_output(PydanticForecastResult)

        pydantic_response: PydanticForecastResult = structured_llm.invoke(messages) # type: ignore

        return pydantic_response
    
    def forecast_diagrams_with_all_persona(self, requirement, diagram_paths: list[str], personas: List[Persona], logger) -> List[PersonaResponse]:
        import concurrent.futures

        collected_results: List[PersonaResponse] = []
        
        def _consult_persona(persona_config):
            try:
                # Perform the Analysis (Blocking I/O)
                analysis_content = self.forecast_with_persona(
                    diagram_paths=diagram_paths, 
                    persona=persona_config, 
                    user_prompt=requirement
                )
                
                return PersonaResponse(
                    role=persona_config.role, 
                    bias=persona_config.bias_instruction, 
                    icon=persona_config.icon, 
                    content=analysis_content
                )
            except Exception as e:
                logger.error(f"Error consulting {persona_config.role}: {e}")
                return None

        max_workers = min(len(personas), 5) 
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_consult_persona, p) for p in personas]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    collected_results.append(result)

        return collected_results 
    
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

    def run_request(self, 
                    human_input: str, 
                    workspace: SessionWorkspace) -> MultiPersonaResponse:
        
        with self._session_logger(workspace) as logger:
            try:
                diagram_paths = workspace.list_figures()
                collected_results: List[PersonaResponse] = self.forecast_diagrams_with_all_persona(requirement=human_input, diagram_paths=diagram_paths, personas=self.personas, logger=logger)
                final_output = MultiPersonaResponse(
                    run_id=workspace.run_id,
                    text='Placeholder',
                    perspectives=collected_results,
                )

                return final_output
                    
            except Exception as e:
                c_logger.error(f"Run failed: {e}")
                logger.error(f"Run failed: {e}", exc_info=True)
                raise RuntimeError(default_config.ERROR_MSG_EXECUTION_FAILED)