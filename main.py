"""fanyi-jp — 基于 Sakura LLM 的日文翻译中文工具"""

import argparse
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.api_client import SakuraAPIClient
from src.file_handler import FileHandler
from src.glossary import Glossary
from src.translator import Translator

console = Console()

# ── 配置加载 ──────────────────────────────────────────────


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        console.print(f"[red]配置文件 {config_path} 不存在，使用默认配置[/red]")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_client(config: dict) -> SakuraAPIClient:
    """根据配置创建 API 客户端"""
    api_cfg = config.get("api", {})
    trans_cfg = config.get("translation", {})

    return SakuraAPIClient(
        base_url=api_cfg.get("base_url", "http://localhost:8080"),
        endpoint=api_cfg.get("endpoint", "/v1/chat/completions"),
        model=api_cfg.get("model", "sakura"),
        temperature=trans_cfg.get("temperature", 0.1),
        top_p=trans_cfg.get("top_p", 0.3),
        max_tokens=trans_cfg.get("max_tokens", 1024),
        frequency_penalty=trans_cfg.get("frequency_penalty", 0.0),
    )


# ── 命令：翻译单段文本 ───────────────────────────────────────


def cmd_text(args, config: dict):
    """翻译单段文本"""
    with build_client(config) as client:
        glossary = _load_glossary(args, config)
        translator = Translator(client, glossary=glossary)

        console.print("[bold blue]原文：[/bold blue]")
        console.print(f"  {args.text}\n")

        result = translator.translate_text(args.text)

        console.print("[bold green]译文：[/bold green]")
        console.print(f"  {result}")


# ── 命令：翻译文件 ────────────────────────────────────────


def cmd_file(args, config: dict):
    """翻译单个文件"""
    file_cfg = config.get("file", {})
    handler = FileHandler(
        input_dir=file_cfg.get("input_dir", "./input"),
        output_dir=file_cfg.get("output_dir", "./output"),
        encoding=file_cfg.get("encoding", "utf-8"),
    )

    input_path = Path(args.input)
    if not input_path.exists():
        console.print(f"[red]文件不存在: {input_path}[/red]")
        sys.exit(1)

    output_path = Path(args.output) if args.output else handler.get_output_path(input_path)

    console.print(Panel(
        f"[bold]输入：[/bold] {input_path}\n[bold]输出：[/bold] {output_path}",
        title="📄 文件翻译",
    ))

    # 读取文件
    lines = handler.read_lines(input_path)
    console.print(f"共 [bold]{len(lines)}[/bold] 行\n")

    # 断点续翻检查
    start_index = 0
    translated_lines: list[str] = []

    if not args.no_resume:
        progress = handler.load_progress(input_path)
        if progress and progress.get("translated_count", 0) > 0:
            translated_count = progress["translated_count"]
            console.print(
                f"[yellow]发现未完成的翻译进度：已翻译 {translated_count}/{progress['total_lines']} 行[/yellow]"
            )
            translated_lines = progress["translated_lines"]
            start_index = translated_count

    if start_index >= len(lines):
        console.print("[green]该文件已全部翻译完成！[/green]")
        return

    remaining_lines = lines[start_index:]

    # 翻译
    with build_client(config) as client:
        glossary = _load_glossary(args, config)
        translator = Translator(
            client,
            glossary=glossary,
            lines_per_chunk=args.chunk_size,
        )

        new_translated = translator.translate_lines(remaining_lines)
        translated_lines.extend(new_translated)

    # 保存结果
    handler.write_lines(output_path, translated_lines)
    handler.clear_progress(input_path)

    console.print(f"\n[bold green]✓ 翻译完成！[/bold green] 输出: {output_path}")


# ── 命令：批量翻译 ────────────────────────────────────────


def cmd_batch(args, config: dict):
    """批量翻译 input 目录下的所有文件"""
    file_cfg = config.get("file", {})
    handler = FileHandler(
        input_dir=file_cfg.get("input_dir", "./input"),
        output_dir=file_cfg.get("output_dir", "./output"),
        encoding=file_cfg.get("encoding", "utf-8"),
    )

    files = handler.list_input_files(pattern=args.pattern)
    if not files:
        console.print(f"[yellow]输入目录 {handler.input_dir} 中没有匹配的文件[/yellow]")
        return

    # 显示文件列表
    table = Table(title="📁 待翻译文件")
    table.add_column("序号", style="dim", width=4)
    table.add_column("文件名", style="cyan")
    table.add_column("大小", justify="right")

    for i, f in enumerate(files, 1):
        size = f.stat().st_size
        table.add_row(str(i), f.name, f"{size:,} B")

    console.print(table)
    console.print(f"\n共 [bold]{len(files)}[/bold] 个文件\n")

    with build_client(config) as client:
        glossary = _load_glossary(args, config)
        translator = Translator(
            client,
            glossary=glossary,
            lines_per_chunk=args.chunk_size,
        )

        for i, input_path in enumerate(files, 1):
            output_path = handler.get_output_path(input_path)
            console.rule(f"[bold]({i}/{len(files)}) {input_path.name}[/bold]")

            lines = handler.read_lines(input_path)
            console.print(f"  共 {len(lines)} 行")

            translated = translator.translate_lines(lines)
            handler.write_lines(output_path, translated)

            console.print(f"  [green]✓ 已保存 → {output_path}[/green]\n")

    console.print("[bold green]✓ 全部翻译完成！[/bold green]")


# ── 命令：检查 API 状态 ──────────────────────────────────────


def cmd_check(args, config: dict):
    """检查 Sakura LLM API 是否可用"""
    with build_client(config) as client:
        console.print(f"正在检查 API: [bold]{client.api_url}[/bold] ...")

        if client.check_health():
            console.print("[bold green]✓ API 服务正常运行[/bold green]")

            # 尝试一句测试翻译
            console.print("\n测试翻译：「こんにちは世界」")
            try:
                result = client.translate("こんにちは世界")
                console.print(f"翻译结果：[bold]{result}[/bold]")
            except Exception as e:
                console.print(f"[yellow]翻译测试失败: {e}[/yellow]")
        else:
            console.print("[bold red]✗ API 服务不可用[/bold red]")
            console.print(
                "请确认 Sakura LLM 已启动并运行在 "
                f"[bold]{client.base_url}[/bold]"
            )
            sys.exit(1)


# ── 工具函数 ──────────────────────────────────────────────


def _load_glossary(args, config: dict) -> Glossary | None:
    """加载术语表"""
    glossary_cfg = config.get("glossary", {})

    # 命令行参数优先
    glossary_path = getattr(args, "glossary", None)

    if not glossary_path and glossary_cfg.get("enabled"):
        glossary_path = glossary_cfg.get("path")

    if glossary_path:
        glossary = Glossary.from_csv(glossary_path)
        if not glossary.is_empty:
            console.print(f"[cyan]已加载术语表: {glossary_path} ({len(glossary)} 条)[/cyan]")
            return glossary

    return None


# ── CLI 入口 ──────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="fanyi-jp",
        description="基于 Sakura LLM 的日文→中文翻译工具",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── text: 翻译单段文本 ──
    p_text = subparsers.add_parser("text", help="翻译单段文本")
    p_text.add_argument("text", help="要翻译的日文文本")
    p_text.add_argument("-g", "--glossary", help="术语表 CSV 文件路径")

    # ── file: 翻译单个文件 ──
    p_file = subparsers.add_parser("file", help="翻译单个文件")
    p_file.add_argument("input", help="输入文件路径")
    p_file.add_argument("-o", "--output", help="输出文件路径（默认自动生成）")
    p_file.add_argument("-g", "--glossary", help="术语表 CSV 文件路径")
    p_file.add_argument(
        "--chunk-size", type=int, default=10,
        help="每次翻译的行数 (默认: 10)",
    )
    p_file.add_argument(
        "--no-resume", action="store_true",
        help="不使用断点续翻，从头开始",
    )

    # ── batch: 批量翻译 ──
    p_batch = subparsers.add_parser("batch", help="批量翻译 input 目录下的文件")
    p_batch.add_argument(
        "-p", "--pattern", default="*.txt",
        help="文件匹配模式 (默认: *.txt)",
    )
    p_batch.add_argument("-g", "--glossary", help="术语表 CSV 文件路径")
    p_batch.add_argument(
        "--chunk-size", type=int, default=10,
        help="每次翻译的行数 (默认: 10)",
    )

    # ── check: 检查 API ──
    subparsers.add_parser("check", help="检查 Sakura LLM API 是否可用")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 加载配置
    config = load_config(args.config)

    # Banner
    console.print(Panel(
        "[bold magenta]fanyi-jp[/bold magenta] — 日文→中文翻译工具\n"
        "[dim]Powered by Sakura LLM (14B-Qwen2.5-v1.0 Q6_K/Q8)[/dim]",
        border_style="magenta",
    ))

    # 分发命令
    commands = {
        "text": cmd_text,
        "file": cmd_file,
        "batch": cmd_batch,
        "check": cmd_check,
    }

    commands[args.command](args, config)


if __name__ == "__main__":
    main()
