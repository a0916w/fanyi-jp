"""核心翻译逻辑"""

import re
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from src.api_client import SakuraAPIClient
from src.glossary import Glossary

console = Console()


class Translator:
    """日文→中文翻译器，封装分段翻译和进度管理"""

    def __init__(
        self,
        client: SakuraAPIClient,
        glossary: Optional[Glossary] = None,
        lines_per_chunk: int = 10,
    ):
        """
        Args:
            client: Sakura LLM API 客户端
            glossary: 术语表（可选）
            lines_per_chunk: 每次翻译的行数（分段大小）
        """
        self.client = client
        self.glossary = glossary
        self.lines_per_chunk = lines_per_chunk

    @property
    def glossary_prompt(self) -> Optional[str]:
        """获取术语表的 prompt 字符串"""
        if self.glossary and not self.glossary.is_empty:
            return self.glossary.to_prompt_string()
        return None

    def translate_text(self, text: str) -> str:
        """
        翻译单段文本。

        Args:
            text: 日文文本

        Returns:
            中文翻译结果
        """
        if not text.strip():
            return ""

        return self.client.translate(text, glossary=self.glossary_prompt)

    def translate_lines(self, lines: list[str]) -> list[str]:
        """
        按行翻译文本，支持分段批量翻译和进度显示。

        将多行文本按 lines_per_chunk 分段，合并发送给 API，
        然后按行拆分结果。

        Args:
            lines: 日文文本行列表

        Returns:
            中文翻译结果行列表
        """
        if not lines:
            return []

        # 分段
        chunks = self._split_chunks(lines)
        translated_lines: list[str] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("翻译中...", total=len(chunks))

            for i, chunk in enumerate(chunks):
                chunk_text = "\n".join(chunk)

                try:
                    result = self.translate_text(chunk_text)
                    result_lines = result.split("\n")

                    # 如果翻译结果行数与原文不一致，尝试对齐
                    if len(result_lines) != len(chunk):
                        console.print(
                            f"  [yellow]⚠ 第 {i + 1} 段：原文 {len(chunk)} 行，"
                            f"译文 {len(result_lines)} 行，行数不一致[/yellow]"
                        )

                    translated_lines.extend(result_lines)

                except Exception as e:
                    console.print(f"  [red]✗ 第 {i + 1} 段翻译失败: {e}[/red]")
                    # 翻译失败时保留原文
                    translated_lines.extend(chunk)

                progress.update(task, advance=1)

        return translated_lines

    def _split_chunks(self, lines: list[str]) -> list[list[str]]:
        """将行列表按 lines_per_chunk 分段"""
        chunks = []
        for i in range(0, len(lines), self.lines_per_chunk):
            chunks.append(lines[i : i + self.lines_per_chunk])
        return chunks
