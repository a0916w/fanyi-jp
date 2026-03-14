# fanyi-jp — 日文翻译中文工具

基于 **Sakura LLM** 的日文→简体中文翻译工具。

---

## 📖 项目简介

本项目使用 [SakuraLLM](https://github.com/SakuraLLM/SakuraLLM) 作为翻译引擎，实现日文文本到简体中文的高质量翻译。Sakura LLM 是专门为日中翻译优化的大语言模型，特别适合轻小说、Galgame 等文本的翻译。

---

## 🏗️ 系统架构

```
┌──────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  输入源       │ ──▶  │  fanyi-jp 翻译器  │ ──▶  │  翻译结果输出        │
│  (txt/文本)   │      │  (Python 脚本)    │      │  (txt/文本)          │
└──────────────┘      └───────┬──────────┘      └─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Sakura LLM API  │
                    │  (本地部署)       │
                    │  localhost:8080   │
                    └──────────────────┘
```

---

## 🤖 关于 Sakura LLM

### 模型信息

| 项目 | 说明 |
|------|------|
| 模型名称 | Sakura-14B-Qwen2.5-v1.0-GGUF |
| 参数规模 | 14B |
| 量化版本 | **Q6_K / Q8**（16GB 显存适用） |
| 模型格式 | GGUF（量化格式） |
| 显存要求 | **16GB VRAM** |
| 下载地址 | [HuggingFace](https://huggingface.co/SakuraLLM/Sakura-14B-Qwen2.5-v1.0-GGUF) |
| 许可证 | **非商用** |

### 核心特性

- **日中翻译专精**：针对日→中翻译任务专门微调
- **术语表支持**（GPT字典）：保持人名、专有名词翻译一致性
- **格式保留**：保留原文中的换行符等控制符
- **高效推理**：采用 GQA 技术，推理速度快、显存占用低

---

## 🔌 API 接口规范

Sakura LLM 通过本地部署提供 **OpenAI 兼容** 的 API 接口。

### 端点

```
POST http://localhost:8080/v1/chat/completions
```

### Prompt 模板

**System Prompt（无术语表时）：**

```
你是一个轻小说翻译模型，可以流畅通顺地以日本轻小说的风格将日文翻译成简体中文，并联系上下文正确使用人称代词，不擅自添加原文中没有的代词。
```

**System Prompt（有术语表时）：**

```
你是一个轻小说翻译模型，可以流畅通顺地以日本轻小说的风格将日文翻译成简体中文，并联系上下文正确使用人称代词，注意不要擅自添加原文中没有的代词，也不要擅自增加或减少换行。
```

**User Prompt（无术语表）：**

```
将下面的日文文本翻译成中文：{japanese_text}
```

**User Prompt（有术语表）：**

```
根据以下术语表（可以为空）：
{术语表内容，格式：原文->译文}

将下面的日文文本翻译成中文：{japanese_text}
```

### 请求示例

```json
{
  "model": "sakura",
  "messages": [
    {
      "role": "system",
      "content": "你是一个轻小说翻译模型，可以流畅通顺地以日本轻小说的风格将日文翻译成简体中文，并联系上下文正确使用人称代词，不擅自添加原文中没有的代词。"
    },
    {
      "role": "user",
      "content": "将下面的日文文本翻译成中文：彼女は静かに窓の外を見つめていた。"
    }
  ],
  "temperature": 0.1,
  "top_p": 0.3,
  "max_tokens": 1024,
  "frequency_penalty": 0.0,
  "do_sample": true
}
```

### 响应示例

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "她静静地凝视着窗外。"
      }
    }
  ]
}
```

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| **Python 3.10+** | 主要开发语言 |
| **httpx / requests** | 调用 Sakura LLM API |
| **llama.cpp** | 本地模型推理后端 |
| **Sakura_Launcher_GUI** | 模型部署管理工具（可选） |

---

## 📋 功能规划

### Phase 1 — 基础翻译（MVP）

- [ ] 单段文本翻译（输入日文 → 输出中文）
- [ ] 连接本地 Sakura LLM API
- [ ] 命令行界面（CLI）

### Phase 2 — 文件批量翻译

- [ ] 支持 `.txt` 文件输入/输出
- [ ] 按行/按段落分割翻译
- [ ] 翻译进度显示
- [ ] 断点续翻（避免重复翻译已完成的部分）

### Phase 3 — 高级功能

- [ ] 术语表（GPT字典）支持
- [ ] 上下文关联翻译（多段一起送入，提高连贯性）
- [ ] 翻译结果缓存
- [ ] 多文件批量处理

### Phase 4 — 可选扩展

- [ ] Web UI 界面
- [ ] 支持更多文件格式（`.epub`、`.srt` 字幕等）
- [ ] 翻译质量评估/对比

---

## 🚀 Sakura LLM 本地部署指南

### 方式一：使用 Sakura_Launcher_GUI（推荐，Windows）

1. 下载 [Sakura_Launcher_GUI](https://github.com/PiDanShouRouZhouXD/Sakura_Launcher_GUI/releases)
2. 下载 GGUF 模型文件
3. 下载对应的 [llama.cpp](https://github.com/ggerganov/llama.cpp/releases) 后端
4. 将模型和 llama.cpp 放在同一目录
5. 启动 GUI，选择模型，点击运行
6. 默认 API 地址：`http://localhost:8080`

### 方式二：使用 llama.cpp 命令行

```bash
# 启动 llama.cpp server
./llama-server \
  -m Sakura-14B-Qwen2.5-v1.0-Q6_K.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -ngl 999 \
  -c 2048
```

### 方式三：使用 vLLM（需要较大显存）

```bash
python -m vllm.entrypoints.openai.api_server \
  --model SakuraLLM/Sakura-14B-Qwen2.5-v1.0 \
  --host 0.0.0.0 \
  --port 8080
```

---

## 📂 项目结构（规划）

```
fanyi-jp/
├── README.md              # 项目说明文档
├── requirements.txt       # Python 依赖
├── config.yaml            # 配置文件（API地址、模型参数等）
├── src/
│   ├── __init__.py
│   ├── translator.py      # 核心翻译逻辑
│   ├── api_client.py      # Sakura LLM API 客户端
│   ├── file_handler.py    # 文件读写处理
│   └── glossary.py        # 术语表管理
├── glossary/
│   └── default.csv        # 默认术语表
├── input/                 # 输入文件目录
├── output/                # 输出文件目录
└── main.py                # 程序入口
```

---

## ⚙️ 配置文件示例（config.yaml）

```yaml
# Sakura LLM API 配置
api:
  base_url: "http://localhost:8080"
  endpoint: "/v1/chat/completions"
  model: "sakura"

# 翻译参数
translation:
  temperature: 0.1
  top_p: 0.3
  max_tokens: 1024
  frequency_penalty: 0.0

# 文件处理
file:
  input_dir: "./input"
  output_dir: "./output"
  encoding: "utf-8"

# 术语表
glossary:
  enabled: false
  path: "./glossary/default.csv"
```

---

## 📝 注意事项

1. **非商用**：Sakura LLM 仅限非商业使用
2. **显存要求**：16GB VRAM，使用 Q6_K 或 Q8 量化版本
3. **翻译质量**：建议使用较低的 `temperature`（0.1）以获得稳定输出
4. **分段翻译**：长文本需要按段落分割，避免超出模型上下文窗口（2048~4096 tokens）
