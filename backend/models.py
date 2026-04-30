"""
Unified streaming interface across Claude, OpenAI, and Gemini.

Each stream yields events as dicts:
  {"type": "text", "content": "..."}        - token chunk
  {"type": "usage", "input": N, "output": N} - final usage data (last event)

Usage events come at the end of a successful stream. They may be missing
if the stream is interrupted - callers should handle that gracefully.
"""
import asyncio
from typing import AsyncIterator, List, Dict, Any

from anthropic import AsyncAnthropic, Anthropic, APIError as AnthropicError
from openai import AsyncOpenAI, OpenAI, OpenAIError
import google.generativeai as genai

MAX_TOKENS = 8000
# 8,000 covers all three roles comfortably. The critic role hits this ceiling
# most easily because its structured output (severity/quote/why/correction/confidence
# per issue) is verbose by design. Proposer and judge can also approach it on
# complex code/architecture questions. Worst-case debate output: 24k tokens
# (~$1.80 at Opus pricing). Lower if you want a tighter cost ceiling.

class ProviderError(Exception):
    """Wraps any provider-specific error with a user-friendly message."""
    pass


def list_available_models(provider: str, api_key: str) -> List[str]:
    """List models from a provider that support chat/text generation. Returns model IDs."""
    if not api_key:
        return []

    try:
        if provider == "claude":
            client = Anthropic(api_key=api_key)
            models = []
            for m in client.models.list(limit=100):
                models.append(m.id)
            return sorted(models, reverse=True)

        elif provider == "openai":
            client = OpenAI(api_key=api_key)
            response = client.models.list()
            # Filter to GPT/o1/o3 chat models, skip embeddings/audio/image variants.
            models = [
                m.id for m in response.data
                if (m.id.startswith("gpt-") or m.id.startswith("o1") or m.id.startswith("o3"))
                and "audio" not in m.id and "embedding" not in m.id
                and "image" not in m.id and "tts" not in m.id and "whisper" not in m.id
                and "realtime" not in m.id and "moderation" not in m.id
            ]
            return sorted(models, reverse=True)

        elif provider == "gemini":
            genai.configure(api_key=api_key)
            models = []
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods:
                    name = m.name.replace("models/", "")
                    if name.startswith("gemini") and "embedding" not in name.lower():
                        models.append(name)
            return sorted(models, reverse=True)

        else:
            return []
    except Exception as e:
        raise ProviderError(f"{provider} list error: {e}") from e


async def stream_model(
    provider: str,
    model: str,
    api_key: str,
    system: str,
    user: str,
) -> AsyncIterator[Dict[str, Any]]:
    """Stream from a provider, yielding text and usage events as dicts."""
    if provider == "claude":
        async for event in _stream_claude(model, api_key, system, user):
            yield event
    elif provider == "openai":
        async for event in _stream_openai(model, api_key, system, user):
            yield event
    elif provider == "gemini":
        async for event in _stream_gemini(model, api_key, system, user):
            yield event
    else:
        raise ProviderError(f"Unknown provider: {provider}")


async def _stream_claude(model: str, api_key: str, system: str, user: str) -> AsyncIterator[Dict[str, Any]]:
    try:
        client = AsyncAnthropic(api_key=api_key)
        async with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield {"type": "text", "content": text}
            # Usage available on the final message after stream completes
            try:
                final_message = await stream.get_final_message()
                yield {
                    "type": "usage",
                    "input": final_message.usage.input_tokens,
                    "output": final_message.usage.output_tokens,
                }
            except Exception:
                pass  # Usage capture is best-effort
    except AnthropicError as e:
        raise ProviderError(f"Claude error: {e}") from e
    except Exception as e:
        raise ProviderError(f"Claude unexpected error: {e}") from e


async def _stream_openai(model: str, api_key: str, system: str, user: str) -> AsyncIterator[Dict[str, Any]]:
    """OpenAI: requires stream_options.include_usage to get token counts during streaming."""

    async def _do_stream(use_max_completion_tokens: bool):
        client = AsyncOpenAI(api_key=api_key)
        token_param = "max_completion_tokens" if use_max_completion_tokens else "max_tokens"
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            token_param: MAX_TOKENS,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        return await client.chat.completions.create(**kwargs)

    try:
        try:
            stream = await _do_stream(use_max_completion_tokens=True)
        except OpenAIError as e:
            if "max_completion_tokens" in str(e) or "max_tokens" in str(e):
                stream = await _do_stream(use_max_completion_tokens=False)
            else:
                raise

        async for chunk in stream:
            # Token chunks: chunk.choices has the delta
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield {"type": "text", "content": chunk.choices[0].delta.content}
            # Usage chunk: comes at the end with empty choices and a usage field
            if hasattr(chunk, "usage") and chunk.usage:
                yield {
                    "type": "usage",
                    "input": chunk.usage.prompt_tokens,
                    "output": chunk.usage.completion_tokens,
                }
    except OpenAIError as e:
        raise ProviderError(f"OpenAI error: {e}") from e
    except Exception as e:
        raise ProviderError(f"OpenAI unexpected error: {e}") from e


async def _stream_gemini(model: str, api_key: str, system: str, user: str) -> AsyncIterator[Dict[str, Any]]:
    """Gemini's SDK is sync-only for streaming, so we run it in a thread executor."""
    try:
        genai.configure(api_key=api_key)
        gmodel = genai.GenerativeModel(model_name=model, system_instruction=system)

        loop = asyncio.get_event_loop()

        def _generate():
            return gmodel.generate_content(user, stream=True)

        response = await loop.run_in_executor(None, _generate)

        def _next_chunk(it):
            try:
                return next(it)
            except StopIteration:
                return None

        iterator = iter(response)
        last_chunk = None
        while True:
            chunk = await loop.run_in_executor(None, _next_chunk, iterator)
            if chunk is None:
                break
            if chunk.text:
                yield {"type": "text", "content": chunk.text}
            last_chunk = chunk

        # Gemini puts usage on the final aggregated response chunk
        if last_chunk is not None:
            try:
                metadata = getattr(last_chunk, "usage_metadata", None)
                if metadata:
                    yield {
                        "type": "usage",
                        "input": metadata.prompt_token_count,
                        "output": metadata.candidates_token_count,
                    }
            except Exception:
                pass

    except Exception as e:
        raise ProviderError(f"Gemini error: {e}") from e
