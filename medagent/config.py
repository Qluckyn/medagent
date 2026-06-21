import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_TEMPERATURE = 0.2


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _qwen_extra_body() -> dict:
    """DashScope/Qwen OpenAI-compatible options."""
    return {"enable_thinking": _env_bool("QWEN_ENABLE_THINKING", False)}


def _openai_compatible_llm(
    *,
    model: str,
    api_key: str | None,
    base_url: str | None,
    extra_body: dict | None = None,
):
    kwargs = {
        "model": model,
        "temperature": LLM_TEMPERATURE,
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = base_url
    if extra_body:
        kwargs["extra_body"] = extra_body
    return ChatOpenAI(**kwargs)


def get_llm():
    if LLM_PROVIDER == "openai":
        extra_body = _qwen_extra_body() if "qwen" in LLM_MODEL.lower() else None
        return _openai_compatible_llm(
            model=LLM_MODEL,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            extra_body=extra_body,
        )

    elif LLM_PROVIDER == "qwen":
        return _openai_compatible_llm(
            model=os.getenv("QWEN_MODEL", LLM_MODEL if LLM_MODEL != "gpt-4o" else "qwen-plus"),
            api_key=(
                os.getenv("QWEN_API_KEY")
                or os.getenv("DASHSCOPE_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            ),
            base_url=(
                os.getenv("QWEN_BASE_URL")
                or os.getenv("DASHSCOPE_BASE_URL")
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            extra_body=_qwen_extra_body(),
        )

    elif LLM_PROVIDER == "anthropic":
        kwargs = {
            "model": os.getenv("ANTHROPIC_MODEL", LLM_MODEL),
            "temperature": LLM_TEMPERATURE,
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url
        return ChatAnthropic(**kwargs)

    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")
