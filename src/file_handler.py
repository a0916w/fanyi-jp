"""文件读写处理"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class FileHandler:
    """处理输入/输出文件的读写，支持断点续翻"""

    def __init__(
        self,
        input_dir: str = "./input",
        output_dir: str = "./output",
        encoding: str = "utf-8",
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.encoding = encoding

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def list_input_files(self, pattern: str = "*.txt") -> list[Path]:
        """列出输入目录中的所有匹配文件"""
        files = sorted(self.input_dir.glob(pattern))
        return files

    def read_file(self, path: str | Path) -> str:
        """读取文件内容"""
        file_path = Path(path)
        return file_path.read_text(encoding=self.encoding)

    def read_lines(self, path: str | Path) -> list[str]:
        """按行读取文件"""
        content = self.read_file(path)
        return content.splitlines()

    def write_file(self, path: str | Path, content: str) -> None:
        """写入文件内容"""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=self.encoding)

    def write_lines(self, path: str | Path, lines: list[str]) -> None:
        """按行写入文件"""
        self.write_file(path, "\n".join(lines))

    def get_output_path(self, input_path: str | Path) -> Path:
        """根据输入文件路径生成输出文件路径"""
        input_path = Path(input_path)
        stem = input_path.stem
        suffix = input_path.suffix
        return self.output_dir / f"{stem}_zh{suffix}"

    # ── 断点续翻 ──────────────────────────────────────────

    def get_progress_path(self, input_path: str | Path) -> Path:
        """获取进度文件路径"""
        input_path = Path(input_path)
        return self.output_dir / f".{input_path.stem}.progress.json"

    def save_progress(
        self,
        input_path: str | Path,
        translated_lines: list[str],
        total_lines: int,
    ) -> None:
        """保存翻译进度"""
        progress_path = self.get_progress_path(input_path)
        data = {
            "source_file": str(input_path),
            "total_lines": total_lines,
            "translated_count": len(translated_lines),
            "translated_lines": translated_lines,
        }
        progress_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding=self.encoding,
        )

    def load_progress(
        self, input_path: str | Path
    ) -> Optional[dict]:
        """加载翻译进度"""
        progress_path = self.get_progress_path(input_path)
        if not progress_path.exists():
            return None

        try:
            data = json.loads(
                progress_path.read_text(encoding=self.encoding)
            )
            return data
        except (json.JSONDecodeError, KeyError):
            return None

    def clear_progress(self, input_path: str | Path) -> None:
        """清除翻译进度"""
        progress_path = self.get_progress_path(input_path)
        if progress_path.exists():
            progress_path.unlink()
