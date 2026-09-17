import base64
import logging
import os
import concurrent.futures
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import Persona, default_config
from .schemas import GlobalAgentState, PersonaResponse, PydanticAnalysisResult, PydanticForecastResult
from .utils import load_prompt
from .llm_factory import get_chat_model

logger = logging.getLogger(default_config.SESS_LOG_NAME)

class DiagramSelection(BaseModel):
    selected_paths: List[str] = Field(description="The list of file paths that are most relevant to answer the query")
    reasoning: str = Field(description="Brief reason for this selection")

class AnalysisAgent:
    """
    Multimodal visual analysis agent. Uses Google Gemini to interpret generated charts
    through contrasting cognitive persona lenses (The Optimistic, The Pessimistic, The Skeptic).
    """
    def __init__(self, model: Optional[str] = None):
        self.system_prompt = load_prompt(agent_name=default_config.AGENT_NAME_ANALYSIS)
        self.system_prompt_forecast = load_prompt(agent_name=default_config.AGENT_NAME_ANALYSIS, key=default_config.PROMPT_KEY_FORECAST)
        self.prompt_user_instruction = load_prompt(agent_name=default_config.AGENT_NAME_ANALYSIS, key=default_config.PROMPT_KEY_ANALYSIS_USER)
        self.model_name = model or default_config.GEMINI_MODEL
        self.llm = get_chat_model(model_name=self.model_name)

    def _encode_image(self, image_path: str) -> str:
        """Helper function to encode image to base64 string."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def select_key_diagrams(self, state: GlobalAgentState, max_items: int = 5) -> List[str]:
        """
        Filters all generated visualization files down to the top key diagrams
        most relevant to answering the user's analytical objective.
        """
        all_paths = state.get("visualization_paths", [])
        if len(all_paths) <= max_items:
            return all_paths

        structured_curator = self.llm.with_structured_output(DiagramSelection)
        prompt = (
            "You are a Senior Visual Data Curator. Multiple diagrams were generated during analysis.\n"
            f"User Goal: '{state['requirement']}'\n\n"
            f"Available Diagram Paths:\n{all_paths}\n\n"
            f"Select the top {max_items} diagrams that provide the strongest evidence for answering the query."
        )

        try:
            selection: DiagramSelection = structured_curator.invoke([HumanMessage(content=prompt)]) # type: ignore
            valid_paths = [p for p in selection.selected_paths if p in all_paths]
            if valid_paths:
                return valid_paths
        except Exception as e:
            logger.warning(f"Diagram curator error: {e}. Falling back to recent diagrams.")

        return all_paths[-max_items:]

    def analyze_diagrams_with_persona(self, diagram_paths: List[str], persona: Persona, user_prompt: str) -> PydanticAnalysisResult:
        """
        Submits visual diagrams to Gemini with an injected persona instruction
        (e.g., The Optimistic, The Pessimistic, The Skeptic).
        """
        image_content = []
        for path in diagram_paths:
            filename = os.path.basename(path)
            try:
                encoded = self._encode_image(path)
                image_content.extend([
                    {"type": "text", "text": f"Chart: {filename}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"}
                    }
                ])
            except Exception as e:
                logger.warning(f"Failed to read image {path}: {e}")

        dynamic_system_prompt = (
            f"You are acting as: {persona.role}.\n"
            f"Your Core Cognitive Bias: {persona.injected_persona}.\n\n"
            f"{self.system_prompt}\n"
            f"{self.prompt_user_instruction}"
        )

        user_instruction = f"User Request: {user_prompt}\n"

        messages = [
            SystemMessage(content=dynamic_system_prompt),
            HumanMessage(content=[
                {"type": "text", "text": user_instruction},
                *image_content 
            ])
        ]

        structured_llm = self.llm.with_structured_output(PydanticAnalysisResult)
        result: PydanticAnalysisResult = structured_llm.invoke(messages) # type: ignore
        return result

    def analyze_diagrams_with_all_personas(
        self,
        workflow_state: dict,
        diagram_paths: List[str],
        personas: List[Persona],
        logger: logging.Logger
    ) -> List[PersonaResponse]:
        """
        Consults all personas concurrently using a thread pool to minimize latency.
        """
        collected_insights: List[PersonaResponse] = []

        def _consult_persona(p_config: Persona) -> Optional[PersonaResponse]:
            try:
                analysis = self.analyze_diagrams_with_persona(
                    diagram_paths=diagram_paths,
                    persona=p_config,
                    user_prompt=workflow_state.get("requirement", "")
                )
                return PersonaResponse(
                    role=p_config.role,
                    persona=p_config.injected_persona,
                    icon=p_config.icon,
                    content=analysis
                )
            except Exception as e:
                logger.error(f"Error consulting persona {p_config.role}: {e}", exc_info=True)
                return None

        workers = min(len(personas), 5)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_consult_persona, p) for p in personas]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    collected_insights.append(res)

        return collected_insights
