# GenAI Starter

一个可在终端连续对话、调用 Python 工具并处理失败的最小 Agent 项目。

## 它比普通聊天程序多了什么？

普通聊天程序只完成：

```text
用户文本 → LLM → 助手文本
```

本项目增加了受控工具闭环：

```text
用户需求
→ LLM 选择工具并生成 JSON 参数
→ Python 校验工具名和参数
→ Python 执行真实函数
→ function_call_output 返回 LLM
→ LLM 解释执行结果
```

核心原则：**LLM 负责判断做什么，Python 负责可靠地执行。**

## 功能

- 多轮终端对话，支持 `clear`、`exit` 和 `quit`。
- `calculator`：用受限 AST 执行确定性计算，不使用 `eval()`。
- `save_note`：把笔记追加到本地 `notes.txt`。
- `get_weather`：通过 Open-Meteo 查询当前天气，无需额外 API Key。
- API、工具和文件异常不会直接终止聊天程序。
- 工具调用有白名单、参数校验和最大轮数限制。

## 项目结构

```text
genai-starter/
├── app.py                 # 命令行交互，只管理输入输出和会话提交
├── llm.py                 # DeepSeek 客户端与模型/工具循环
├── tools.py               # 工具实现、工具说明书、白名单和安全执行入口
├── config.py              # 环境变量、路径和运行参数
├── tests/
│   ├── test_tools.py      # 工具正常与异常路径
│   └── test_llm.py        # 不联网测试 Agent 闭环和停止条件
├── .env.example           # 可提交的环境变量模板
├── .gitignore             # 排除 Key、虚拟环境、缓存和用户笔记
├── requirements.txt       # 可复现的 Python 依赖范围
└── README.md              # 安装、运行、测试与验收说明
```

拆分原因：

- `app.py` 不应同时承担 API、工具和配置逻辑。
- `llm.py` 只关心模型协议和工具循环。
- `tools.py` 是模型输出进入真实世界前的安全边界。
- `config.py` 让 Key 和运行参数不散落在代码中。
- `tests/` 让“看起来能运行”变成“可以重复验证”。

## 核心安全边界

[tools.py](tools.py) 中的 `execute_tool_call()` 集中完成以下工作：

- 解析模型生成的 JSON 参数。
- 使用白名单限制可执行函数。
- 拒绝缺失或多余参数。
- 捕获计算、文件和天气服务异常。
- 使用 `call_id` 返回对应的 `function_call_output`。

完成标准不只是“没有语法错误”，还需要下面的测试全部通过：

```powershell
python -m unittest discover -s tests -v
```

## 安装

以下命令在 PowerShell 中执行：

```powershell
cd "C:\Users\danger\Documents\ChatGPT\test\generative-ai-agent-learning\genai-starter"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

打开 `.env`，填写自己的 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=你的APIKey
DEEPSEEK_MODEL=deepseek-flash
```

`.env` 已被 Git 忽略，不要把真实 Key 写进代码或 `.env.example`。

## 运行

```powershell
.\.venv\Scripts\python.exe app.py
```

可以测试：

```text
计算 (12 + 8) / 4
帮我保存笔记：Function Calling 中真正执行函数的是 Python
杭州现在天气怎么样？
```

## 测试策略

测试默认不调用 DeepSeek，也不访问真实天气服务：

- 计算器检查正常表达式、空输入、代码注入和除零。
- 笔记使用临时文件，不污染真实 `notes.txt`。
- 天气接口使用模拟响应，测试结果不会随天气变化。
- 工具执行器检查坏 JSON、未知工具、错误参数和结果配对。
- Agent 循环检查工具闭环与最大轮数停止条件。

## 交付验收

- [x] `execute_tool_call()` 已完成。
- [x] `EXERCISE_COMPLETE = True`。
- [x] `python -m unittest discover -s tests -v` 全部通过。
- [x] 可以连续对话并使用三个工具。
- [x] API Key 只存在于本地 `.env`。
- [x] 工具或 API 失败不会让程序直接退出。
- [x] `git status` 中不出现 `.env`、`notes.txt` 或 `__pycache__`。

## 外部服务

- 模型：DeepSeek Responses API。
- 天气与地理编码：Open-Meteo。

天气数据来自外部服务，可能受网络、地点歧义和服务可用性影响。
