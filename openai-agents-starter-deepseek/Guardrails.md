# Guardrails 学习笔记

## 本项目增加了什么

- Input Guardrail：在入口 Agent 启动前，阻止疑似 API Key 被发送给模型或工具。
- Output Guardrail：在最终回答展示前，阻止疑似 API Key 离开应用。
- 终端异常处理：捕获输入和输出的 Tripwire 异常，并显示明确原因。

当前检查由 Python 正则完成，不会增加审核模型调用，也不会把命中的疑似密钥写入日志。

## 执行边界

```text
用户输入
  ↓
Input Guardrail（routing_agent）
  ├── tripwire=False → 进入 Routing / Handoff / Tool 流程
  └── tripwire=True  → 抛出 InputGuardrailTripwireTriggered

最终 Agent 生成候选回答
  ↓
Output Guardrail（routing / calculation / life）
  ├── tripwire=False → 输出给用户
  └── tripwire=True  → 抛出 OutputGuardrailTripwireTriggered
```

## 关键代码关系

```python
@input_guardrail(run_in_parallel=False)
def block_exposed_secrets(...) -> GuardrailFunctionOutput:
    ...
```

`run_in_parallel=False` 表示输入检查结束后才启动入口 Agent，避免被阻断的内容仍提前产生模型用量或进入后续流程。

```python
GuardrailFunctionOutput(
    output_info={...},
    tripwire_triggered=blocked,
)
```

- `output_info`：保存可用于日志和用户提示的检查信息。
- `tripwire_triggered`：真正决定是否阻断；为 `True` 时 SDK 抛出对应异常。

```python
Agent(
    input_guardrails=[block_exposed_secrets],
    output_guardrails=[block_secret_output],
)
```

只定义 Guardrail 不会自动生效，还必须把它配置给对应 Agent。

## Routing 项目中的绑定规则

- Input Guardrail 只绑定 `routing_agent`，因为它是每次运行的第一个 Agent。
- Output Guardrail 同时绑定三个 Agent，因为路由 Agent 可以直接回答，两个专业 Agent 也可能在 Handoff 后完成最终回答。
- 工具参数、文件路径和真实副作用仍由 `tools.py` 自己校验；Agent 级 Guardrail 不能替代工具边界。

## 自测问题（不含答案）

1. `output_info` 和 `tripwire_triggered` 分别承担什么职责？
2. 为什么本项目把 `run_in_parallel` 设置为 `False`？
3. 为什么 Output Guardrail 需要同时绑定三个 Agent？
4. Guardrail 触发后，为什么还需要在 `app.py` 中捕获异常？
5. 为什么 Guardrail 不能替代 `save_note` 内部的参数和文件路径校验？
