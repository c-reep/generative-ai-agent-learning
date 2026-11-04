# OpenAI Agents SDK + DeepSeek 入门项目

这是把 Part 07/11 中“手写消息历史 + 手写工具调用循环”重做成 Agents SDK 版本的小项目。OpenAI Agents SDK 负责编排，DeepSeek `deepseek-flash` 负责模型推理。

## 五个学习重点

1. **Agent**：把模型、指令和可用工具组合成一个助手。
Agent不是模型，而是一份配置，将模型（手写model） + System指令（手写SYSTEM_PROMPT） + 可用工具组合在一起(手写TOOLS)
2. **Runner**：执行 Agent，并自动循环处理模型回答和工具调用。
Runner是Agent运行时,在其内部执行调用模型→ 检查工具请求→ 执行工具→ 返回工具结果→ 再次调用模型→ 得到最终答案
替代了part11中手写的 run_agent_turn() 循环
3. **function_tool**：把带类型标注的 Python 函数转换成模型可调用的工具。
例如：@function_tool
def calculator(expression: str) -> float:
    """计算数学表达式。"""
    return ...
SDK会生成模型需要的工具描述。因此不再需要手写整段 TOOLS JSON Schema和函数分发代码。
4. **Session**：保存多轮对话状态，让后续问题能够使用前文。
5. **Tracing**：查看一次运行中的模型请求、工具调用和执行过程，方便排错。
相当于给 Agent 加了“运行录像”，方便检查它为何调用工具、在哪一步失败。

## 项目结构

```text
openai-agents-starter/
├── app.py                  # 终端循环，调用 Runner
├── agent_setup.py          # Agent 的模型、指令和工具清单
├── tools.py                # 三个工具及其纯 Python 实现
├── config.py               # .env、模型和文件路径
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 安装（PowerShell）

```powershell
cd C:\Users\danger\Documents\ChatGPT\test\openai-agents-starter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

然后打开 `.env`。Base URL 和模型已经填好，只需替换 Key：

```dotenv
MODEL_API_KEY=你的真实DeepSeek_API_Key
MODEL_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
```

`.env` 已被 `.gitignore` 忽略，不能把真实 Key 写入 `.env.example` 或 Python 文件。

模型请求通过 DeepSeek 的 Responses API 发出；OpenAI 平台 Tracing 已关闭。

## 运行

```powershell
python app.py
```

建议按顺序试：

1. `你好，我叫小明`，再问 `我叫什么？`，检查多轮上下文。
2. `计算 (10+15)/5*6`，检查计算器工具。
3. `帮我记下：Agent = 模型决策 + 程序执行`，检查 `notes.txt`。
4. `上海现在天气怎么样？`，检查实时天气工具。
5. 输入 `/new`，再问 `我叫什么？`，检查新会话不继承旧上下文。

每次真实运行模型都会产生 API 用量。

## 完成标准

- 能连续对话，并能用 `/new` 开始无旧历史的新会话。
- 三个工具都能被 Agent 选择并执行。
- 工具失败不会让终端程序直接退出。
- `.env` 不会进入 Git。
- 能用自己的话解释：`Agent` 定义能力，`Runner` 执行循环，`Session` 保存上下文，工具函数执行真实动作。

## 官方资料

- [Agents SDK Quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart?lang=python)
- [Running agents 与会话状态](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [DeepSeek Responses API](https://api-docs.deepseek.com/guides/responses_api/)
- [DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)
