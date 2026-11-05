# Human-in-the-loop 学习笔记

## 本项目增加了什么

`save_note` 会写入本地文件，因此它现在必须取得用户明确批准：

```python
@function_tool(needs_approval=True)
def save_note(content: str) -> str:
    ...
```

计算器和天气查询保持自动执行，因为它们不会修改本地笔记。

## 执行流程

```text
生活助手提出 save_note 工具调用
  ↓
SDK 暂停运行，尚未写文件
  ↓
result.interruptions 返回待审批动作
  ↓
终端展示工具名称和参数
  ├── 批准：state.approve(interruption)
  └── 拒绝：state.reject(interruption)
  ↓
Runner.run(agent, state, session=原会话)
  ↓
恢复同一轮运行并生成最终回答
```

## 必须理解

- `needs_approval=True` 负责声明工具有审批要求。
- `interruptions` 表示这次运行暂停了，不代表运行失败或已经结束。
- `to_state()` 保存未完成运行的状态，包括原工具调用。
- 审批完成后必须恢复 `state`，不能新建一条普通用户消息。
- 默认回车代表拒绝；没有明确同意时，不执行副作用操作。
- Guardrail 是自动检查，Human-in-the-loop 是人工决定，两者不能互相替代。

## 手动测试

1. 输入“保存笔记：今天学习了 Human-in-the-loop”。
2. 检查审批界面是否展示 `save_note` 和准确的 `content`。
3. 输入 `n`，确认 `notes.txt` 没有新增内容。
4. 再次请求保存并输入 `y`，确认文件只新增一次。
5. 审批完成后继续提出计算问题，确认聊天循环仍可继续使用。
