# Hello-Agents 第四章学习总结

## 完成情况

本章从零实现并运行了三种经典 Agent 范式：

- ReAct：模型逐轮提出 Action，Python 执行工具，再把 Observation 交回模型。
- Plan-and-Solve：模型先生成完整计划，Python 校验后按顺序逐步执行并汇总。
- Reflection：模型生成初稿、审查并修改，直到审查通过或达到次数上限。

项目同时实现了工具白名单、JSON 解析与校验、明确的停止条件，以及不调用真实 API 的离线测试。

## 三种范式对比

| 范式 | 谁决定步骤 | 中途是否调整 | 停止条件 | 适用任务 | 主要风险 |
| --- | --- | --- | --- | --- | --- |
| ReAct | 模型每轮提出下一步，Python 控制执行边界 | 是，根据 Observation 调整 | 模型输出 `Finish` 或达到 `max_steps` | 实时信息、工具调用、路径不确定的动态任务 | 错误工具调用、格式错误、循环不结束、成本和延迟增加 |
| Plan-and-Solve | 模型通过 Planner 一次性生成计划，Python 按顺序执行 | 当前实现不调整 | 所有步骤执行并完成最终汇总；计划解析失败则提前终止 | 可以提前拆解、步骤依赖清晰、目标稳定的任务 | 初始计划错误会影响后续步骤，当前实现不能重新规划 |
| Reflection | Python 固定“初稿→审查→修改”流程，模型生成内容和评价 | 是，根据审查意见修改 | 审查通过或达到 `max_iterations` | 代码、报告等对最终质量要求较高的任务 | 调用成本和延迟增加；自我认同、幻觉和评价标准不可靠 |

## ReAct：行动与环境反馈的闭环

核心流程：

```text
组装 Prompt
→ 调用 LLM
→ 解析 Thought 和 Action
→ Python 检查白名单并执行工具
→ 保存 Observation
→ 下一轮重新调用 LLM
→ Finish 或达到 max_steps
```

关键认识：

1. 模型返回的 `Action` 只是调用意愿，不代表工具已经执行。
2. `ToolExecutor.execute()` 才拥有真实执行权，并负责拒绝未知工具。
3. `Observation` 是工具结果或错误反馈，必须进入下一轮上下文，模型才能调整决策。
4. `max_steps` 是 Python 设置的安全阀，不能只依赖 Prompt 要求模型主动停止。
5. 当前实现使用 Prompt 约定的文本协议，因此需要正则解析，稳定性弱于 API 原生 Function Calling。

变量区别：

```text
step    = 当前一轮的 Thought、Action、Observation 记录
steps   = Python 保存的本次运行全部结构化记录
history = 下一轮发送给模型的 Action 和 Observation 文本
```

## Plan-and-Solve：先规划，再按顺序执行

核心流程：

```text
用户问题
→ Planner.plan() 生成 JSON 计划
→ parse_plan() 解析并校验
→ Executor.execute() 按列表顺序执行
→ 前一步结果传给后一步
→ 最终汇总
```

关键认识：

1. 模型返回的是 JSON 文本，`json.loads()` 将其转换为可校验、可遍历的 Python 列表。
2. Python检查计划是否为列表、步骤数是否超限、每一步是否为非空字符串。
3. 有 `n` 个步骤时，共进行 `n + 2` 次模型调用：一次规划、`n` 次执行、一次汇总。
4. 当前实现不会根据执行结果重新规划；错误的初始计划可能影响全部后续步骤。
5. 当前 `Executor` 只调用 LLM 生成文本，没有工具执行器，因此不能真的发送邮件或查询实时天气。

与 Deterministic Flow 的区别：

```text
Deterministic Flow：开发者提前在 Python 中写死步骤和判断条件。
Plan-and-Solve：模型先生成计划，随后 Python 固定按照该计划执行。
```

## Reflection：用审查意见修改初稿

核心流程：

```text
生成初稿
→ 生成结构化审查结果
→ needs_revision=false：结束
→ needs_revision=true：根据 feedback 修改
→ 再次审查
→ 通过或达到 max_iterations
```

关键认识：

1. `max_iterations` 是最多修改次数，不是至少修改一次；初稿合格时可以零次修改。
2. 当前版本并没有独立的评审模型，而是同一个 `self.llm` 使用不同 Prompt 扮演生成者和审查者。
3. Reflection 增加模型调用、延迟和 Token 消耗。
4. 自我审查可能出现自我认可或幻觉，不能代替可信 API、单元测试、静态检查和事实来源。
5. 更可靠的工程流程应把外部测试失败结果作为反馈，再交给模型修改。

## 与 Function Calling 和 Agents SDK 的关系

```text
genai-starter
= API 原生 function_call/function_call_output
+ 手写模型—工具循环

hello-agents-ch04
= Prompt 定义 Thought/Action/Observation 文本协议
+ 手写 ReAct、Plan-and-Solve、Reflection 循环

openai-agents-starter-deepseek
= API 原生结构化工具调用
+ Runner 自动管理模型调用、工具结果回传和 Handoff
```

Agents SDK并未使用本项目的正则文本协议。它封装的主要是 API 原生 Function Calling 循环，但其“模型行动→工具结果→再次决策”过程与 ReAct 在结构上相似。

## 工程边界

三种范式都遵循同一条原则：

```text
模型负责生成候选计划、动作、内容和评价；
Python负责解析、校验、授权、执行、状态管理、异常处理和停止条件。
```

Python本身也不会自动判断事实真假。事实验证仍需要可信数据源、API、数据库、测试或确定性工具。

## 验收结果

- 三种范式均提供独立命令行入口。
- ReAct包含工具白名单、错误反馈和最大步数。
- Plan-and-Solve包含JSON计划校验、步骤上限和结果传递。
- Reflection包含结构化审查结果和最大修改次数。
- 离线测试不调用真实模型，不消耗API额度。
- API Key只保存在被Git忽略的`.env`中。

## 下一阶段

下一步在现有 Agents SDK 项目上实现 Manager Pattern / Agent as Tool：主 Agent 调用专业 Agent 完成子任务，并在取得结果后收回控制权。完成该实践后，再精选学习 Hello-Agents 第七章“构建你的 Agent 框架”。
