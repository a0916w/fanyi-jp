"""Sakura LLM API 客户端"""

import httpx
from typing import Optional


class SakuraAPIClient:
    """与本地 Sakura LLM API 交互的客户端"""

    SYSTEM_PROMPT = (
        "你是一个轻小说翻译模型，可以流畅通顺地以日本轻小说的风格"
        "将日文翻译成简体中文，并联系上下文正确使用人称代词，"
        "不擅自添加原文中没有的代词。"
    )

    SYSTEM_PROMPT_WITH_GLOSSARY = (
        "你是一个轻小说翻译模型，可以流畅通顺地以日本轻小说的风格"
        "将日文翻译成简体中文，并联系上下文正确使用人称代词，"
        "注意不要擅自添加原文中没有的代词，也不要擅自增加或减少换行。"
    )

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        endpoint: str = "/v1/chat/completions",
        model: str = "sakura",
        temperature: float = 0.1,
        top_p: float = 0.3,
        max_tokens: int = 1024,
        frequency_penalty: float = 0.0,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.frequency_penalty = frequency_penalty
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def api_url(self) -> str:
        return f"{self.base_url}{self.endpoint}"

    def _build_user_prompt(
        self, text: str, glossary: Optional[str] = None
    ) -> str:
        """构建用户 prompt"""
        if glossary:
            return (
                f"根据以下术语表（可以为空）：\n{glossary}\n\n"
                f"将下面的日文文本翻译成中文：{text}"
            )
        return f"将下面的日文文本翻译成中文：{text}"

    def translate(
        self, text: str, glossary: Optional[str] = None
    ) -> str:
        """
        调用 Sakura LLM 翻译日文文本为中文。

        Args:
            text: 要翻译的日文文本
            glossary: 术语表字符串，格式为 "原文->译文" 每行一条

        Returns:
            翻译后的中文文本
        """
        system_prompt = (
            self.SYSTEM_PROMPT_WITH_GLOSSARY if glossary else self.SYSTEM_PROMPT
        )
        user_prompt = self._build_user_prompt(text, glossary)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "frequency_penalty": self.frequency_penalty,
        }

        response = self._client.post(self.api_url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def check_health(self) -> bool:
        """检查 API 服务是否可用"""
        try:
            resp = self._client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def close(self):
        """关闭 HTTP 客户端"""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
