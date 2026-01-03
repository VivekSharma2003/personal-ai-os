"""
Personal AI OS - Multi-Provider LLM Client

Supports OpenAI, Google Gemini (new SDK), and Anthropic Claude.
"""
import json
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from app.config import get_settings

settings = get_settings()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        pass
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )
        return response.choices[0].message.content
    
    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=settings.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def extract_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)


class GeminiProvider(LLMProvider):
    """Google Gemini provider using new google.genai SDK."""
    
    def __init__(self):
        from google import genai
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = settings.gemini_model
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        from google.genai import types
        
        # Extract system instruction and convert messages
        system_instruction = None
        contents = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=msg["content"])]
                ))
            elif msg["role"] == "assistant":
                contents.append(types.Content(
                    role="model", 
                    parts=[types.Part(text=msg["content"])]
                ))
        
        config = types.GenerateContentConfig(
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_output_tokens=max_tokens or settings.llm_max_tokens,
            system_instruction=system_instruction,
        )
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return response.text
    
    async def generate_embedding(self, text: str) -> List[float]:
        result = await self.client.aio.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        return result.embeddings[0].values
    
    async def extract_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        from google.genai import types
        
        config = types.GenerateContentConfig(
            temperature=0.3,
            system_instruction=system_prompt + "\nRespond ONLY with valid JSON, no markdown formatting.",
        )
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        
        text = response.text.strip()
        # Clean up potential markdown formatting
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        # Extract system message
        system = ""
        chat_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)
        
        response = await self.client.messages.create(
            model=self.model,
            system=system,
            messages=chat_messages,
            temperature=temperature if temperature is not None else settings.llm_temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
        )
        return response.content[0].text
    
    async def generate_embedding(self, text: str) -> List[float]:
        # Anthropic doesn't have embeddings, fall back to OpenAI
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def extract_json(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        response = await self.client.messages.create(
            model=self.model,
            system=system_prompt + "\nRespond ONLY with valid JSON, no explanation.",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=settings.llm_max_tokens,
        )
        text = response.content[0].text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())


# Provider factory
def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider."""
    provider = settings.llm_provider.lower()
    
    if provider == "openai":
        return OpenAIProvider()
    elif provider == "gemini":
        return GeminiProvider()
    elif provider == "anthropic":
        return AnthropicProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# Convenience functions
_provider: Optional[LLMProvider] = None


def _get_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = get_llm_provider()
    return _provider


async def generate_response(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    stream: bool = False
) -> str:
    """Generate a response from the configured LLM provider."""
    provider = _get_provider()
    return await provider.generate_response(messages, temperature, max_tokens)


async def generate_embedding(text: str) -> List[float]:
    """Generate an embedding vector for the given text."""
    provider = _get_provider()
    return await provider.generate_embedding(text)


async def extract_json_response(
    prompt: str,
    system_prompt: str = "You are a helpful assistant that responds in valid JSON.",
    model: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a JSON response from the LLM."""
    provider = _get_provider()
    if hasattr(provider, 'extract_json'):
        return await provider.extract_json(prompt, system_prompt)
    else:
        # Fallback
        response = await provider.generate_response(
            [
                {"role": "system", "content": system_prompt + "\nRespond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return json.loads(response)


async def evaluate_relevance(
    rule_content: str,
    context: str,
    model: Optional[str] = None
) -> bool:
    """Evaluate if a rule is relevant to the current context."""
    prompt = f"""Evaluate if this rule should be applied to the current context.

RULE: {rule_content}
CONTEXT: {context}

Is this rule relevant? Answer with a JSON object: {{"relevant": true/false, "reason": "brief explanation"}}"""

    result = await extract_json_response(prompt)
    return result.get("relevant", False)
