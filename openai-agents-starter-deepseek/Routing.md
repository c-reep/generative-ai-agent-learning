# Routing 学习笔记

## 当前项目结构

```text
routing_agent（分流助手）
├── calculation_agent（计算助手）
│   └── calculator
└── life_agent（生活助手）
    ├── get_weather
    └── save_note
```

三个 Agent 可以共用同一个底层模型。它们的主要区别是 `instructions`、可用工具和职责范围，而不是分别使用三个不同的模型平台。

## 必须搞懂的问题

### 1. 计算请求经过了哪些步骤？

```text
用户输入
  ↓
分流 Agent 判断意图
  ↓ Handoff
计算 Agent 接管本轮任务
  ↓ Tool Call
calculator 工具
  ↓
Python 函数真正执行计算
  ↓
工具结果返回计算 Agent
  ↓
计算 Agent 整理并输出最终答案
```

Handoff 后，本轮通常由专业 Agent 直接完成回答，不会再回到分流 Agent。下一轮之所以又从分流 Agent 开始，是因为 `app.py` 再次把分流 Agent 传给了 `Runner.run()`。

### 2. `handoffs` 和 `tools` 有什么区别？

- `handoffs`：当前 Agent 可以把本轮控制权移交给哪些专业 Agent。
- `tools`：当前 Agent 可以调用哪些函数或外部能力。

简记：

```text
Handoff = 换一个 Agent 继续负责
Tool    = 当前 Agent 借用能力后继续负责
```

具体选择哪个 Handoff 或 Tool，通常由模型结合指令和用户输入决定，并不是 Python `if/else` 的确定性路由。

### 3. 为什么分流 Agent 不直接配置业务工具？

为了隔离职责和权限：

- 分流 Agent 只判断任务应该交给谁。
- 计算 Agent 只能使用计算器。
- 生活 Agent 只能查询天气和保存笔记。

这样可以减少工具选择干扰，也能避免某个 Agent 使用职责之外的工具。

### 4. 计算结果究竟是谁算出来的？

Python 函数负责计算。模型只生成类似下面的工具调用意图：

```text
calculator(expression="(10+15)/5*8")
```

`Runner` 接收到工具调用后执行 Python 函数，再把执行结果交给模型整理成自然语言。

### 5. 为什么同一个 Session 可以保持多轮上下文？

相同的 `SQLiteSession` 使用相同的 Session ID。SDK会在运行前读取对应历史，并在运行后保存本轮新增内容。

当前项目每次启动都会生成新的随机 ID，因此：

- 同一次程序运行中可以保持历史。
- `/new` 会创建新 ID，不继承旧历史。
- 关闭并重新启动程序后，也不会自动恢复上次会话。

### 6. `@function_tool` 是依赖注入吗？

不是。现阶段可以把它理解为“给普通 Python 函数办理 Agent 工具证”。

```python
@function_tool
def calculator(expression: str) -> str:
    ...
```

它会让 SDK 识别函数名称、参数类型、说明和执行逻辑。之后还需要通过下面的配置，把工具授权给指定 Agent：

```python
Agent(tools=[calculator])
```

简记：

```text
@function_tool      = 制作 SDK 能识别的工具
tools=[calculator] = 把工具授权给 Agent
```

依赖注入可以暂时不学，不影响理解和完成当前项目。

### 7. 为什么 Agent 的内部名称使用英文？

SDK 会根据专业 Agent 的 `name` 生成 Handoff 工具名。中文名称可能被转换成相同的下划线名称，造成工具名冲突。

因此内部使用唯一的英文标识：

```text
routing_agent
calculation_agent
life_agent
```

终端显示时再映射为“分流助手”“计算助手”和“生活助手”。

## 一句话总结

> 分流 Agent 决定把任务交给谁，Handoff 转移控制权，专业 Agent 选择工具，Python 执行真实动作，Runner 驱动完整循环，Session 保存对话状态。

## 完成标准

不看答案也能解释以下内容：

1. 一道计算题从用户输入到最终输出的完整路径。
2. Handoff 和 Tool 的本质区别。
3. 为什么分流 Agent 不拥有业务工具。
4. 模型、Runner 和 Python 工具各自负责什么。
5. Session 如何保存历史，以及 `/new` 为什么会清空上下文。
6. `@function_tool` 和 `tools=[...]` 分别做什么。
