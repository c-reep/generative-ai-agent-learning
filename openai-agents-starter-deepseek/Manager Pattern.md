# Manager Pattern / Agents as tools 学习笔记

## 为什么增加这个版本

原来的 Routing 使用 Handoff：分流 Agent 把控制权交给专业 Agent，本轮由专业 Agent 直接回答。

Manager Pattern 把专业 Agent 暴露成工具：Manager 调用专家取得结果，控制权随后回到 Manager，由它综合多个结果并统一回答。

```text
Handoff
用户 → 分流 Agent → 专业 Agent → 用户

Manager Pattern
用户 → Manager → 专业 Agent 工具 → Manager → 用户
```

## 最关键的代码

```python
manager_agent = Agent(
    name="manager_agent",
    tools=[
        calculation_agent.as_tool(
            tool_name="ask_calculation_specialist",
            tool_description="处理需要可靠数学计算的请求。",
        ),
        life_agent.as_tool(
            tool_name="ask_life_specialist",
            tool_description="处理当前天气查询或保存笔记请求。",
        ),
    ],
)
```

- `calculation_agent` 和 `life_agent` 仍然是真正的 Agent 对象。
- `as_tool()` 为它们创建 Manager 可以调用的工具接口。
- 专业 Agent 内部仍可以继续调用普通 Python 工具。
- 专业 Agent 返回后，Manager 的运行循环继续，由 Manager 生成最终回答。

## 当前项目中的执行路径

```text
用户复合请求
  ↓
manager_agent 判断需要哪些能力
  ├─ ask_calculation_specialist
  │    └─ calculation_agent → calculator → Python 计算
  └─ ask_life_specialist
       ├─ life_agent → get_weather → 天气服务
       └─ life_agent → save_note → 人工审批 → 写文件
  ↓
manager_agent 汇总所有专业结果
  ↓
最终回答
```

## 与现有安全机制的关系

- 输入 Guardrail 绑定入口 `manager_agent`。
- 最终输出 Guardrail 绑定负责最终回答的 `manager_agent`。
- `save_note` 的 `needs_approval=True` 仍在真实副作用边界生效。
- 嵌套专业 Agent 提出保存操作时，整条运行会暂停；审批后恢复同一状态。

## 必须能够回答的问题

1. Handoff 与 Agents as tools 的控制权有什么区别？
2. 为什么 Manager 可以一次调用多个专业 Agent？
3. `as_tool()` 是否把专业 Agent 变成了普通 Python 函数？
4. 专业 Agent 调用完成后，谁负责最终回答？
5. Manager、专业 Agent、普通工具和 Python 各自负责什么？
6. 为什么 `save_note` 放在嵌套专业 Agent 中仍需要人工审批？

## 运行方式

```powershell
.\.venv\Scripts\python.exe manager_pattern.py
```

建议使用复合问题测试：

```text
计算 (10+15)/5*6，同时查询上海现在的天气。
```

预期现象：Manager 分别调用计算专家和生活专家，最后由“总控助手”统一回答。
