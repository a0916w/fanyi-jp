"""术语表（GPT字典）管理"""

import csv
from pathlib import Path
from typing import Optional


class Glossary:
    """管理翻译术语表，保持人名和专有名词翻译一致性"""

    def __init__(self):
        self._entries: list[tuple[str, str]] = []

    @classmethod
    def from_csv(cls, path: str | Path) -> "Glossary":
        """
        从 CSV 文件加载术语表。

        CSV 格式：原文,译文
        示例：
            桐ヶ谷和人,桐谷和人
            アスナ,亚丝娜
        """
        glossary = cls()
        file_path = Path(path)

        if not file_path.exists():
            return glossary

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and not row[0].startswith("#"):
                    source = row[0].strip()
                    target = row[1].strip()
                    if source and target:
                        glossary._entries.append((source, target))

        return glossary

    def add(self, source: str, target: str) -> None:
        """添加一条术语"""
        self._entries.append((source.strip(), target.strip()))

    @property
    def is_empty(self) -> bool:
        return len(self._entries) == 0

    def to_prompt_string(self) -> Optional[str]:
        """
        将术语表转为 Sakura LLM prompt 格式。

        格式：原文->译文（每行一条）
        """
        if self.is_empty:
            return None
        return "\n".join(f"{src}->{tgt}" for src, tgt in self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"Glossary(entries={len(self._entries)})"
