# Part 07：多轮聊天应用

## 多轮对话的本质

DeepSeek API 是无状态的：服务端不会自动把前一次独立请求当作下一次请求的上下文。

程序需要维护消息列表，并在每轮请求中重新发送相关历史：

```text
system
→ user 第一次提问
→ assistant 第一次回答
→ user 第二次提问
→ assistant 第二次回答
```

模型并没有获得永久记忆，是 Python 程序制造了连续对话的效果。

## 三种消息角色

- `system`：稳定的身份、任务、格式和行为边界。
- `user`：用户当前或历史输入。
- `assistant`：模型过去的回答。

如果只保存用户消息，模型会看不到自己之前回答过什么，无法可靠处理“把你刚才的第二点解释一下”之类的追问。

## 候选历史与正式历史

本项目不会在发送请求前直接修改正式历史：

```python
request_messages = history.copy()
request_messages.append(
    {"role": "user", "content": user_input}
)
```

API 成功后，才提交本轮用户消息和助手回答：

```python
history = request_messages + [
    {"role": "assistant", "content": answer}
]
```

这样请求失败时不会污染上下文。

## 程序控制

- `while True`：持续等待用户输入。
- `continue`：本轮结束，开始下一轮。
- `break`：退出聊天循环。
- `clear`：重置历史，但保留 System 消息。
- `exit` / `quit`：结束程序。

## 历史增长带来的问题

- 输入 Token 和调用成本增加。
- 响应时间增加。
- 可能超过上下文窗口。
- 早期信息可能被裁剪或干扰当前回答。
- 敏感信息可能被反复发送。

可以通过最近消息窗口、早期对话摘要和相关信息筛选控制历史长度。

## 实际验收

- 连续追问可以引用上一轮内容。
- 每轮成功后增加一条 `user` 和一条 `assistant` 消息。
- `clear` 后模型不再知道清空前的对话。
- `exit` 和 `quit` 可以正常退出。
- API 失败不会写入正式历史，也不会让程序直接崩溃。

##  从天气问题理解 Function Calling
- 在运行 Part 07 多轮聊天程序时，我询问模型：南京的天气怎么样？
- 聊天程序无法获取实时天气，因为 LLM 只能根据输入和已有知识生成回答，不能直接访问天气 API。
- 而Function Calling把流程扩展到：
LLM 生成工具名称和参数
→ Python 校验并执行工具
→ 执行结果返回给 LLM
→ LLM 生成最终回答
