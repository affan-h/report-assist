import os
import logging
from typing import Optional
from langchain_core.language_models.chat_models import BaseChatModel
from core.config import default_config

logger = logging.getLogger(default_config.CENTRAL_LOG_NAME)

def get_chat_model(
    model_name: Optional[str] = None,
    temperature: float = 0.3,
    max_retries: int = 2,
    timeout: Optional[int] = 300
) -> BaseChatModel:
    """
    Factory to construct a unified LangChain chat model.
    Defaults to Google Gemini via langchain_google_genai.
    Falls back to ChatOpenAI if OPENAI_API_KEY is provided.
    """
    gemini_key = (
        os.getenv("GEMINI_API_KEY") 
        or os.getenv("GOOGLE_API_KEY") 
        or default_config.GEMINI_API_KEY
    )
    openai_key = os.getenv("OPENAI_API_KEY") or default_config.OPENAI_API_KEY

    # 1. Primary Provider: Google Gemini
    if gemini_key or default_config.LLM_PROVIDER.lower() == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        target_model = model_name or default_config.GEMINI_MODEL or "gemini-2.5-flash"
        return ChatGoogleGenerativeAI(
            model=target_model,
            google_api_key=gemini_key,
            temperature=temperature,
            max_retries=max_retries,
            timeout=timeout,
        )

    # 2. Secondary Provider: OpenAI
    if openai_key:
        from langchain_openai import ChatOpenAI
        target_model = model_name or default_config.OPENAI_MODEL or "gpt-4o-mini"
        return ChatOpenAI(
            model=target_model,
            openai_api_key=openai_key,
            temperature=temperature,
            max_retries=max_retries,
            timeout=timeout,
        )

    # 3. Default fallback (attempts Gemini with environment)
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_name or "gemini-2.5-flash",
        temperature=temperature,
        max_retries=max_retries,
        timeout=timeout,
    )
