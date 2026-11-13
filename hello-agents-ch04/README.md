# Hello-Agents 第四章：经典 Agent 范式

这是对 Hello-Agents 第四章的独立最小实践，不使用 Agent 框架，目的是看清
SDK 内部通常会隐藏的运行循环。

原章地址：[Chapter 4: Building Classic Agent Paradigms](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/Chapter4-Building-Classic-Agent-Paradigms.md)

本章完成后的个人总结见：[Chapter4.md](./Chapter4.md)。

## 三种范式

```text
ReAct
模型决定下一步 → Python执行工具 → Observation回到模型 → 继续或结束
1.ReAct 的巧妙之处在于认识到思考与行动是相互补充的。思考指导行动，而行动则反过来促进正确的思考。
2.该代理会不断重复这一思维→行动→观察的循环过程，将新的观察结果添加到历史记录中，从而形成一个不断扩展的上下文。当它确定已经找到了最终答案时，就会输出结果。这个过程形成了一个强大的协同效应：推理使得行动更有目标性，而行动则为推理提供了事实依据。
3.能够利用外部工具来回答那些大型语言模型仅凭自身知识库无法直接解答的问题。

Plan-and-Solve
模型生成完整计划 → Python按顺序逐步执行 → 汇总最终答案

Reflection
生成初稿 → 模型审查 → 根据反馈修改 → 通过或达到次数上限
```

| 范式 | 适合任务 | 主要风险 | Python必须控制的部分 |
| --- | --- | --- | --- |
| ReAct | 需要根据工具结果动态调整 | 格式错误、工具误用、无限循环 | 工具白名单、参数校验、`max_steps` |
| Plan-and-Solve | 可以提前拆解的多步骤任务 | 计划错误会影响后续全部步骤 | 计划解析、步骤上限、执行顺序 |
| Reflection | 对最终质量要求较高的任务 | 调用次数、延迟和自我确认偏差 | 输出校验、修改次数上限、停止条件 |

## 项目结构

```text
hello-agents-ch04/
├── app.py                 # 三种范式的统一命令行入口
├── config.py              # .env 配置读取
├── contracts.py           # LLM最小接口，便于替换和测试
├── llm.py                 # OpenAI兼容接口封装
├── tools.py               # 工具白名单、安全计算器、时间与文本统计
├── react.py               # Thought/Action/Observation循环
├── plan_and_solve.py      # Planner、Executor与结果汇总
├── reflection.py          # Draft/Critique/Refine循环
├── Chapter4.md            # 第四章学习总结与三种范式对比
├── tests/
│   └── test_chapter4.py   # 不调用API的离线测试
├── .env.example
├── requirements.txt
└── README.md
```

## 安装

在 PowerShell 中执行：

```powershell
cd C:\Users\danger\Documents\ChatGPT\test\generative-ai-agent-learning\hello-agents-ch04
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

然后只在 `.env` 中填写自己的 API Key。不要提交 `.env`。

## 运行

```powershell
# ReAct：必须重点观察工具结果怎样成为下一轮上下文
.\.venv\Scripts\python.exe app.py react "计算 (10+15)/5*6"

# Plan-and-Solve：观察计划先完整生成，再由Python按顺序执行
.\.venv\Scripts\python.exe app.py plan "制定一个两天的Python异常处理学习方案"

# Reflection：对比初稿、审查意见和修改稿
.\.venv\Scripts\python.exe app.py reflection "写一个返回1到n之间所有质数的Python函数"
```

不传任务时会使用内置示例：

```powershell
.\.venv\Scripts\python.exe app.py react
```

## 离线测试

测试使用 `FakeLLM`，不需要 API Key，也不会产生模型费用：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 相比原章做的工程化调整

1. 不接入 SerpApi，避免为了学习运行循环再申请第二个 Key；ReAct 使用本地安全工具。
2. 计划使用 JSON 数组而非可执行的 Python 表达式，解析后检查类型和步骤上限。
3. Reflection 的审查结果使用固定 JSON 字段，并由 Python 校验。
4. 所有循环都有明确次数上限，工具只允许通过白名单执行。
5. 增加离线测试，将模型输出当作不可信数据进行验证。

## 你必须亲自完成的练习

- 在 `tools.py` 新增一个无副作用工具，并注册到 `build_default_tool_executor()`。
- 故意让 `FakeLLM` 返回错误 Action，观察 ReAct 如何把解析错误变成 Observation。
- 把 Plan-and-Solve 的 `max_steps` 改小，验证过长计划会被拒绝。
- 修改 Reflection 的评价标准，对比修改前后的输出。

## 学完必须能回答的问题

1. ReAct 中模型、Python和工具分别负责什么？
2. 为什么 Observation 必须加入下一轮上下文？
3. 为什么即使 Prompt 要求固定格式，Python仍然必须解析和校验？
4. ReAct 的 `max_steps` 和 Reflection 的 `max_iterations` 分别防止什么？
5. Plan-and-Solve 与 Python 写死的 Deterministic Flow 有什么区别？
6. 为什么 Reflection 可以改善答案，却不能代替外部事实校验和自动测试？
7. 面对一个具体任务，你会根据什么选择三种范式？
