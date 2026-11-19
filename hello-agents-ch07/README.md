# Hello-Agents 第七章：构建最小 Agent 框架

这个项目不是照抄完整 HelloAgents，而是把第七章最重要的框架边界缩小为：

```text
Message → Agent 基类 → LLM 接口 → Tool/Registry → 具体 Agent
```

第四章关注“不同运行范式如何循环”；第七章关注“如何把共用能力抽象成可复用框架”。

## 当前进度

- [x] 完成第七章理论学习。
- [x] 补全 Message、Agent、Tool、ToolRegistry、SimpleAgent 和 FunctionCallAgent。
- [x] 15 个离线测试全部通过。
- [ ] 使用真实 DeepSeek 模型验证 `tool_call → Python 执行 → role=tool 回传` 完整链路。

回答正确本身不能证明模型调用了工具。真实模型验证时，应观察模型是否返回
`tool_call`，并确认 Python 注册表执行了工具且工具结果进入下一轮模型请求。

## 项目结构

```text
hello-agents-ch07/
├── core/
│   ├── message.py              # 统一消息对象
│   ├── llm.py                  # 模型通信与返回结构适配
│   ├── agent.py                # Agent 抽象基类和历史
│   └── config.py               # 行为限制和模型配置
├── agents/
│   ├── simple_agent.py         # 普通多轮对话
│   └── function_call_agent.py  # 原生 Function Calling 循环
├── tools/
│   ├── base.py                 # Tool 抽象基类和 Schema
│   ├── registry.py             # 工具注册、授权、执行和异常隔离
│   └── builtin.py              # 计算与文本统计工具
├── tests/
│   ├── fakes.py                # 不调用 API 的 FakeLLM
│   ├── test_scaffold.py        # 初始骨架测试
│   └── test_todos.py           # TODO 验收测试
├── app.py
├── architecture-map.html          # 类关系与工具调用链交互图
├── .env.example
├── .gitignore
└── requirements.txt
```

可直接在浏览器打开 `architecture-map.html`，交互查看类之间的依赖关系和
Function Calling 的两轮模型调用链。

## 你必须亲自完成的顺序

不要同时修改所有文件，按下面顺序逐步运行测试：

1. `core/message.py`：`Message.to_dict()`。
2. `core/agent.py`：三种历史管理方法。
3. `tools/base.py`：`Tool.to_schema()`。
4. `tools/registry.py`：注册、查询、Schema 和执行。
5. `tools/builtin.py`：在一个注册表中注册两个工具。
6. `agents/simple_agent.py`：普通多轮对话流程。
7. `agents/function_call_agent.py`：参数解析和工具调用循环。

所有挖空位置都可以用下面的命令查找：

```powershell
rg -n "TODO（必须由你手写）" .
```

## 安装

在 PowerShell 中执行：

```powershell
cd C:\Users\danger\Documents\ChatGPT\test\generative-ai-agent-learning\hello-agents-ch07
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

只在 `.env` 中填写自己的 API Key，不要提交 `.env`。

## 测试方式

骨架测试从项目创建时就应该通过：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_scaffold -v
```

TODO 验收测试在你补全代码前会失败，这是学习任务的一部分：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_todos -v
```

全部完成后运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 运行

先完成对应 TODO，再运行真实模型：

```powershell
# 普通多轮对话
.\.venv\Scripts\python.exe app.py simple

# 原生 Function Calling
.\.venv\Scripts\python.exe app.py function
```

建议测试：

```text
simple：
我叫小明
我叫什么？
/new

function：
计算10乘5
统计“Agent framework”这段文本
```

## 完成标准

- 能解释 `agent.py` 与 `llm.py` 的职责边界。
- 能解释为什么 `Agent` 和 `Tool` 使用 `ABC`。
- 一个 `ToolRegistry` 可以保存多个工具。
- 未注册工具、错误参数和工具异常不会直接导致程序退出。
- `SimpleAgent` 能保持并清空多轮历史。
- `FunctionCallAgent` 能完成模型、工具、模型的闭环。
- 所有离线测试通过，并且没有把 `.env` 提交到 Git。

## 心得体会
- 1.Message 是我们框架内部使用的消息对象：
   message = Message(
    role="user",
    content="计算10乘5",
    metadata={"source": "terminal"},
)
但模型 API 不需要 timestamp 和 metadata，它只需要类似：
{
    "role": "user",
    "content": "计算10乘5",
}
因此：message.to_dict()是把当前 Message 对象中需要的属性取出来，转换成 API 能接收的普通字典。
相反地，模型响应转成框架对象的过程发生在 OpenAICompatibleLLM 中：
2.tool.to_schema()表示生成一份说明书，随 API 请求发给模型。
schema = tool.to_schema()得到：
{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "对两个数字进行运算",
        "parameters": {
            "type": "object",
            ...
        },
    },
}
然后在调用complete()时将说明书一同传给模型api，如complete_with_tools(..., tools=schemas)
