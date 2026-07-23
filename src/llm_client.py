import os
import time
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_default_model() -> str:
    model = os.getenv("MODEL_ID")
    if not model:
        raise ValueError("MODEL_ID is not set")
    return model

def get_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> OpenAI:
    api_key = api_key or os.getenv("LLM_API_KEY")
    base_url = base_url or os.getenv("LLM_BASE_URL")

    kwargs = {}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url

    return OpenAI(**kwargs)


def _build_messages(instructions: str, user_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "developer", "content": instructions},
        {"role": "user", "content": user_prompt},
    ]


def _normalize_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(text)
            else:
                parts.append(str(item))
        return "\n".join(parts).strip()
    return str(content)


def llm_structured(
    instructions: str,
    user_prompt: str,
    output_type: Any,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
):
    client = client or get_client()
    model = model or get_default_model()

    response = client.chat.completions.parse(
        model=model,
        messages=_build_messages(instructions, user_prompt),
        response_format=output_type,
    )

    parsed = response.choices[0].message.parsed
    usage = response.usage
    return parsed, usage


def llm_structured_retry(
    instructions: str,
    user_prompt: str,
    output_type: Any,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
    max_retries: int = 5,
    initial_wait: int = 45,
    retry_wait: int = 5,
    verbose: bool = True,
):
    client = client or get_client()
    model = model or get_default_model()

    for attempt in range(max_retries):
        try:
            return llm_structured(
                instructions=instructions,
                user_prompt=user_prompt,
                output_type=output_type,
                model=model,
                client=client,
            )
        except Exception as e:
            if verbose:
                print(f"Retry {attempt + 1}/{max_retries} failed: {type(e).__name__}: {e}")

            if attempt == max_retries - 1:
                if verbose:
                    print("Max retries reached. Raising exception.")
                raise

            wait_time = initial_wait if attempt == 0 else retry_wait
            if verbose:
                print(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)


def llm_text(
    instructions: str,
    user_prompt: str,
    model: Optional[str] = None,
    client: Optional[OpenAI] = None,
):
    client = client or get_client()
    model = model or get_default_model()

    response = client.chat.completions.create(
        model=model,
        messages=_build_messages(instructions, user_prompt),
    )

    content = response.choices[0].message.content
    text = _normalize_text_content(content)
    usage = response.usage
    return text, usage