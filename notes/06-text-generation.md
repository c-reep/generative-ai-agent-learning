# Part 06：单轮文本生成应用

## 项目流程

```text
终端输入学习需求
  → Python 读取输入
  → SDK 调用 DeepSeek API
  → 模型生成学习计划
  → 终端显示结果
```

## API 与 SDK

- API 是客户端与服务端通信的接口和约定。
- SDK 是封装 API 请求、认证、错误和响应对象的客户端工具包。

项目使用 OpenAI Python SDK 调用 DeepSeek 的 OpenAI 兼容接口：

```python
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)
```

## 配置安全

- `.env`：本地真实 Key，不提交。
- `.env.example`：变量模板，可以提交。
- `.gitignore`：避免 Git 追踪 `.env`、虚拟环境和缓存。
- `requirements.txt`：记录项目所需 Python 包。

## 单轮的含义

单轮不一定要求每问一次就重新启动程序。它表示每次 API 请求彼此独立，没有把上一轮用户输入和模型回答作为下一轮上下文。

## 异常处理

项目区分认证失败、限流、网络失败、超时和其他 API 状态错误。即使 API 请求成功，也要检查 `response.output_text` 是否为空。

## 验收结果

- 已在 VS Code 中完成真实 API 调用。
- API Key 未写入代码。
- 能解释 `base_url`、`api_key`、`model` 和 `max_output_tokens`。
- 理解模型输出逻辑自洽不代表事实正确。
