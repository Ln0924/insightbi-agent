from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    @abstractmethod
    def structured(self, *, system: str, user: str, schema: type[T], model: str) -> T:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """适配支持 OpenAI Chat Completions 协议的企业内网或云端模型。"""

    def __init__(self, api_key: str, base_url: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def structured(self, *, system: str, user: str, schema: type[T], model: str) -> T:
        completion = self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format=schema,
            temperature=0,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("模型未返回符合 Schema 的结构化结果")
        return parsed

