"""Provide execution logging middleware for the payroll agent.

The middleware records when an agent run or tool invocation starts
and finishes. It logs technical execution events without recording
user messages, tool parameters, payroll records, or tool results.
"""

from collections.abc import Awaitable, Callable

from agent_framework import (
    AgentContext,
    FunctionInvocationContext,
    agent_middleware,
    function_middleware,
)



#=====================================================
# Agent execution logging middleware
#=====================================================
@agent_middleware
async def logging_middleware(
    context: AgentContext,
    call_next: Callable[[], Awaitable[None]],
) -> None:
    """Log the beginning and end of an agent execution."""

    print("Agent execution started.")

    await call_next()

    print("Agent execution finished.")


#=====================================================
# Tool execution logging middleware
#=====================================================
@function_middleware
async def tool_logging_middleware(
    context: FunctionInvocationContext,
    call_next: Callable[[], Awaitable[None]],
) -> None:
    """Log the beginning and end of each tool invocation."""

    tool_name = context.function.name

    print(f"Tool execution started: {tool_name}")

    await call_next()

    print(f"Tool execution finished: {tool_name}")





