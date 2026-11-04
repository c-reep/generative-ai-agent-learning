# Generative AI Agent Learning

这是我的生成式 AI Agent 工程学习记录。学习主线来自 Microsoft 的
[Generative AI for Beginners](https://github.com/microsoft/generative-ai-for-beginners)，
并使用 DeepSeek API 完成本地 Python 实践。

当前目标不是一次学完全部课程，而是先完成一条最小、可验证的 Agent 主线：

```text
LLM 基础 → Prompt → 单轮 API → 多轮聊天 → Function Calling → 最小 Agent
```

Embedding、向量数据库和 RAG 暂时不在本阶段范围内。

## 学习进度

| 章节 | 状态 | 主要产出 |
| --- | --- | --- |
| Part 01：LLM 基础 | 已完成 | 理解 Token、自回归生成、上下文窗口和幻觉 |
| Part 04：Prompt 基础 | 理论完成 | 理解消息角色、Few-shot、结构化输出和 Prompt 边界 |
| Part 06：文本生成应用 | 已完成 | DeepSeek 单轮文本生成程序 |
| Part 07：聊天应用 | 已完成 | DeepSeek 多轮聊天、历史管理、清空与错误恢复 |
| Part 11：Function Calling | 已完成 | 实现计算、保存笔记、查询天气和工具调用闭环 |
| 最小 Agent 项目 | 已完成 | `genai-starter` 已模块化并通过自动测试 |
|Agents SDK 入门项目| 已完成 |使用 OpenAI Agents SDK 驱动 DeepSeek，实现 Agent、Runner、Session 和自动工具调用|

## 仓库结构

```text
generative-ai-agent-learning/
├── README.md
├── notes/
│   ├── 01-llm-basics.md
│   ├── 04-prompt-engineering.md
│   ├── 06-text-generation.md
│   ├── 07-chat-applications.md
│   └── 11-integrating-with-function-calling.md
├── part06-deepseek/
├── part07-deepseek/
├── part11-deepseek/
├── genai-starter/                    # 手动实现工具调用闭环
└── openai-agents-starter-deepseek/   # 使用 Agents SDK 驱动 DeepSeek
```

## 运行环境

- Windows 11
- Python 3.9+
- VS Code
- DeepSeek API
- OpenAI Python SDK（通过兼容接口调用 DeepSeek）

## 快速开始

以下命令以 Part 07 为例，在 PowerShell 中运行：

```powershell
cd part07-deepseek
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

然后在 `.env` 中填写自己的 Key：

```env
DEEPSEEK_API_KEY=你的APIKey
DEEPSEEK_MODEL=deepseek-flash
```

启动程序：

```powershell
.\.venv\Scripts\python.exe app.py
```

Part 07 支持以下命令：

- `clear`：清空聊天历史，但保留 System 消息。
- `exit` 或 `quit`：退出程序。

## 当前形成的工程认识

1. LLM 生成候选文本或动作，不等于真正执行 Python。
2. API 是服务约定，SDK 是帮助程序调用 API 的客户端工具。
3. 多轮对话不是模型永久记忆，而是程序保存并重新发送历史。
4. Prompt 可以引导输出，但校验、权限和异常处理必须由代码负责。
5. API 失败时，不应把失败轮次写入正式聊天历史。
6. API Key 只保存在本地 `.env`，不会提交到 Git。

## 声明

这是个人学习记录，不是 Microsoft 或 DeepSeek 的官方课程答案。代码以教学和理解协议为主要目的，尚未按生产环境要求完成身份认证、持久化、并发控制和完整测试。
