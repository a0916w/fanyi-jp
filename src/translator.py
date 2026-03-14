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

        空行会被保留在原位（不发送给 LLM），确保字幕等格式不被破坏。

        Args:
            lines: 日文文本行列表

        Returns:
            中文翻译结果行列表
        """
        if not lines:
            return []

        # 1. 记录每一行是空行还是内容行
        #    empty_map[i] = True 表示第 i 行是空行
        empty_map: dict[int, bool] = {}
        content_lines: list[str] = []
        content_indices: list[int] = []

        for i, line in enumerate(lines):
            if line.strip() == "":
                empty_map[i] = True
            else:
                empty_map[i] = False
                content_lines.append(line)
                content_indices.append(i)

        console.print(
            f"  共 [bold]{len(lines)}[/bold] 行，"
            f"其中内容行 [bold]{len(content_lines)}[/bold] 行，"
            f"空行 [bold]{len(lines) - len(content_lines)}[/bold] 行（保留）"
        )

        # 2. 只对内容行进行分段翻译
        chunks = self._split_chunks(content_lines)
        translated_content: list[str] = []

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

                    # 去除翻译结果中的多余空行（LLM 可能产生）
                    result_lines = [l for l in result_lines if l.strip() != ""]

                    if len(result_lines) != len(chunk):
                        console.print(
                            f"  [yellow]⚠ 第 {i + 1} 段：原文 {len(chunk)} 行，"
                            f"译文 {len(result_lines)} 行，行数不一致[/yellow]"
                        )

                    translated_content.extend(result_lines)

                except Exception as e:
                    console.print(f"  [red]✗ 第 {i + 1} 段翻译失败: {e}[/red]")
                    translated_content.extend(chunk)

                progress.update(task, advance=1)

        # 3. 将翻译结果填回原位，空行保持不变
        result_lines: list[str] = []
        content_idx = 0

        for i in range(len(lines)):
            if empty_map[i]:
                # 空行原样保留
                result_lines.append("")
            else:
                # 填入翻译结果（如果有的话，否则保留原文）
                if content_idx < len(translated_content):
                    result_lines.append(translated_content[content_idx])
                else:
                    result_lines.append(lines[i])
                content_idx += 1

        return result_lines

    def _split_chunks(self, lines: list[str]) -> list[list[str]]:
        """将行列表按 lines_per_chunk 分段（仅内容行）"""
        chunks = []
        for i in range(0, len(lines), self.lines_per_chunk):
            chunks.append(lines[i : i + self.lines_per_chunk])
        return chunks
