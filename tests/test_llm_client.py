import pytest

from harness.llm_client import LLMSettings, OpenAICompatibleLLMClient


def test_openai_client_allows_missing_key_for_local_url():
    settings = LLMSettings(backend="openai", api_key=None, base_url="http://127.0.0.1:8000/v1")
    client = OpenAICompatibleLLMClient(settings=settings)
    assert client.backend_name == "openai"


def test_openai_client_requires_key_for_non_local_url():
    settings = LLMSettings(backend="openai", api_key=None, base_url="https://api.openai.com/v1")
    with pytest.raises(ValueError):
        OpenAICompatibleLLMClient(settings=settings)


def test_openai_client_accepts_key_for_non_local_url():
    settings = LLMSettings(
        backend="openai",
        api_key="dummy-key",
        base_url="https://api.openai.com/v1",
    )
    client = OpenAICompatibleLLMClient(settings=settings)
    assert client.backend_name == "openai"
