# Generative AI Agent Learning

这是我的生成式 AI Agent 工程学习记录。学习主线来自 Microsoft 的
[Generative AI for Beginners](https://github.com/microsoft/generative-ai-for-beginners)，
并使用 DeepSeek API 完成本地 Python 实践。

当前目标不是一次学完全部课程，而是先完成一条最小、可验证的 Agent 工程主线：

```text
LLM 基础 → Prompt → 单轮 API → 多轮聊天 → Function Calling
→ 最小 Agent → Agents SDK → Deterministic Flow → Routing
→ Guardrails → Human-in-the-loop
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
| 最小 Agent 项目 | 已完成 | 对应 `genai-starter`，手动实现工具调用闭环并通过自动测试 |
| OpenAI Agents SDK 入门 | 已完成 | 对应 `openai-agents-starter-deepseek`，使用 DeepSeek 理解 Agent、Runner、Session 和 `function_tool` |
| Deterministic Flow | 已完成 | 理解由 Python 固定步骤、质量门和停止条件的确定性流程 |
| Routing 与 Handoff | 已完成 | 分流 Agent 将计算和生活任务交给不同专业 Agent |
| Guardrails | 已完成 | 实现输入、输出安全检查和 Tripwire 异常处理 |
| Human-in-the-loop | 已完成 | `save_note` 写文件前暂停运行并由用户批准或拒绝 |

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
    ├── app.py              # 多轮终端、审批恢复和异常边界
    ├── agent_setup.py      # Routing Agent 与两个专业 Agent
    ├── tools.py            # 计算、天气和保存笔记工具
    ├── guardrails_setup.py # 输入和输出 Guardrails
    ├── tests/              # 26 个离线测试
    ├── Deterministic flow.md
    ├── Routing.md
    ├── Guardrails.md
    └── Human-in-the-loop.md
```

## 运行环境

- Windows 11
- Python 3.10+
- VS Code
- DeepSeek API
- OpenAI Agents SDK（通过兼容接口调用 DeepSeek）

## 快速开始

以下命令运行当前最新的 Agents SDK 项目。在 PowerShell 中执行：

```powershell
cd openai-agents-starter-deepseek
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

然后在 `.env` 中填写自己的 Key：

```env
MODEL_API_KEY=你的DeepSeek_API_Key
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
```

启动程序：

```powershell
.\.venv\Scripts\python.exe app.py
```

当前终端支持以下命令：

- `/new`：开始一段不包含旧历史的新会话。
- `/help`：显示可用命令。
- `exit` 或 `quit`：退出程序。

当前 Agent 结构：

```text
分流助手
├── 计算助手
│   └── calculator
└── 生活助手
    ├── get_weather
    └── save_note（执行前需要人工批准）
```

## 当前形成的工程认识

1. LLM 生成候选文本或动作，不等于真正执行 Python。
2. API 是服务约定，SDK 是帮助程序调用 API 的客户端工具。
3. 多轮对话不是模型永久记忆，而是程序保存并重新发送历史。
4. Prompt 可以引导输出，但校验、权限和异常处理必须由代码负责。
5. API 失败时，不应把失败轮次写入正式聊天历史。
6. API Key 只保存在本地 `.env`，不会提交到 Git。
7. Handoff 会把当前运行的控制权移交给专业 Agent；下一轮由应用决定从哪个 Agent 开始。
8. Guardrail 负责自动检查，Human-in-the-loop 负责在副作用发生前交由人批准。
9. 审批产生的是一次暂停；应恢复原 `RunState`，而不是重新创建用户请求。
10. 模型负责提出工具调用，Python 负责校验、授权和执行真实动作。

## 声明

这是个人学习记录，不是 Microsoft、OpenAI 或 DeepSeek 的官方课程答案。代码以教学和理解协议为主要目的，虽然已有离线测试，仍未按生产环境要求完成身份认证、并发控制、审计和部署加固。
