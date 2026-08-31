# Middleware and execution logging

The Payroll AI Agent uses middleware to observe the execution of the
agent and its tools.

Middleware runs around another operation. It can execute logic before
the operation begins, pass control to the next component, and continue
after that component has finished.

The middleware is implemented in
[`middleware.py`](../src/payroll-agent-ai-search/middleware.py) and
registered with the agent in
[`main.py`](../src/payroll-agent-ai-search/main.py).


## Agent execution middleware

### `logging_middleware`

`logging_middleware` uses the Agent Framework `@agent_middleware`
decorator.

It records two technical events:

```text
Agent execution started.
Agent execution finished.