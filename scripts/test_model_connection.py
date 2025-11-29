
import os
import pytest
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from agent.base_agent.base_agent import DeepSeekChatOpenAI

# Load environment variables
load_dotenv()

MODELS_CONFIG = [
    {
        "name": "deepseek-chat",
        "basemodel": "deepseek-chat",
        "signature": "deepseek-chat-guoweilong",
        "enabled": False
    },
    {
        "name": "gemini-3-pro-preview",
        "basemodel": "gemini-3-pro-preview[x6]",
        "signature": "gemini-3-pro-preview[x6]-guoweilong",
        "enabled": False
    },
    {
        "name": "MiniMax-M2",
        "basemodel": "MiniMax-M2",
        "signature": "MiniMax-M2-guoweilong",
        "enabled": True
    }
]

@pytest.mark.parametrize("model_config", MODELS_CONFIG)
def test_model_configuration_and_initialization(model_config):
    """
    Test that model configuration correctly resolves API credentials from .env
    and that the model class can be initialized without errors.
    """
    model_name = model_config.get("name", "unknown")
    basemodel = model_config.get("basemodel")
    
    print(f"\nTesting Model: {model_name}")

    # 1. Logic from main.py to resolve credentials
    openai_base_url = model_config.get("openai_base_url", None)
    openai_api_key = model_config.get("openai_api_key", None)

    if not openai_base_url or not openai_api_key:
        env_prefix = None
        model_name_lower = model_name.lower()
        if "deepseek" in model_name_lower:
            env_prefix = "DEEPSEEK"
        elif "minimax" in model_name_lower:
            env_prefix = "MINMAX"
        elif "gemini" in model_name_lower:
            env_prefix = "GEMINI"
        
        if env_prefix:
            if not openai_base_url:
                openai_base_url = os.getenv(f"{env_prefix}_API_BASE")
            if not openai_api_key:
                openai_api_key = os.getenv(f"{env_prefix}_API_KEY")

    # Assertions for Credentials
    assert openai_base_url is not None, f"Failed to resolve API Base for {model_name}. Check .env file."
    assert openai_api_key is not None, f"Failed to resolve API Key for {model_name}. Check .env file."
    
    # Basic validation that they look correct (e.g. Base URL is a URL)
    assert openai_base_url.startswith("http"), f"API Base for {model_name} does not look like a URL: {openai_base_url}"
    
    # 2. Initialize Model (Logic from base_agent.py)
    try:
        if "deepseek" in basemodel.lower():
            llm = DeepSeekChatOpenAI(
                model=basemodel,
                base_url=openai_base_url,
                api_key=openai_api_key,
                max_retries=1,
                timeout=10,
            )
        else:
            llm = ChatOpenAI(
                model=basemodel,
                base_url=openai_base_url,
                api_key=openai_api_key,
                max_retries=1,
                timeout=10,
            )
        assert llm is not None
    except Exception as e:
        pytest.fail(f"Model initialization failed for {model_name}: {e}")

@pytest.mark.integration
@pytest.mark.parametrize("model_config", MODELS_CONFIG)
def test_model_connection_live(model_config):
    """
    Live connection test. This attempts to actually call the API.
    Use pytest -m integration to run this (or just run all).
    """
    model_name = model_config.get("name", "unknown")
    basemodel = model_config.get("basemodel")
    
    # Resolve Credentials
    openai_base_url = model_config.get("openai_base_url", None)
    openai_api_key = model_config.get("openai_api_key", None)

    if not openai_base_url or not openai_api_key:
        env_prefix = None
        model_name_lower = model_name.lower()
        if "deepseek" in model_name_lower:
            env_prefix = "DEEPSEEK"
        elif "minimax" in model_name_lower:
            env_prefix = "MINMAX"
        elif "gemini" in model_name_lower:
            env_prefix = "GEMINI"
        
        if env_prefix:
            if not openai_base_url:
                openai_base_url = os.getenv(f"{env_prefix}_API_BASE")
            if not openai_api_key:
                openai_api_key = os.getenv(f"{env_prefix}_API_KEY")
    
    if not openai_api_key:
        pytest.skip(f"Skipping live test for {model_name}: No API Key found")

    # Initialize
    if "deepseek" in basemodel.lower():
        llm = DeepSeekChatOpenAI(
            model=basemodel,
            base_url=openai_base_url,
            api_key=openai_api_key,
            max_retries=1,
            timeout=10,
        )
    else:
        llm = ChatOpenAI(
            model=basemodel,
            base_url=openai_base_url,
            api_key=openai_api_key,
            max_retries=1,
            timeout=10,
        )

    # Invoke
    try:
        response = llm.invoke("Hello")
        assert response is not None
        assert response.content is not None
        print(f"[{model_name}] Response: {response.content}")
    except Exception as e:
        pytest.fail(f"Live API call failed for {model_name}: {e}")

