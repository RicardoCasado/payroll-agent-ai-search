"""Preserve selected payroll filters across conversation turns.

The context provider extracts payroll years and Pay Grades from user
messages, stores them in the session state, and makes them available
when interpreting subsequent requests.
"""

import re

from typing import Any

from agent_framework import (
    AgentSession,
    ContextProvider,
    SessionContext,
)

from payroll_data import AVAILABLE_PAYROLL_YEARS


class PayrollContextProvider(ContextProvider):
    """Preserve and inject payroll filters selected by the user."""

    DEFAULT_SOURCE_ID = "payroll_context"

    def __init__(self) -> None:
        """Initialize the provider with its context source identifier."""

        super().__init__(self.DEFAULT_SOURCE_ID)

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession | None,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Inject stored payroll filters before an agent execution."""

        years = state.get("years", [])
        pay_grade = state.get("pay_grade")

        selected_context: list[str] = []

        if years:
            selected_context.append(
                "Selected payroll years: "
                + ", ".join(
                    str(year) for year in years
                )
                + "."
            )

        if pay_grade:
            selected_context.append(
                f"Selected Pay Grade: {pay_grade}."
            )

        if selected_context:
            # Add the selected filters to the agent instructions without
            # claiming that the corresponding data has been accessed.
            context.extend_instructions(
                self.source_id,
                (
                    "The user has selected the following "
                    "payroll context:\n"
                    + "\n".join(selected_context)
                    + "\nUse this context when interpreting "
                    "subsequent questions. Do not claim that "
                    "payroll data has been analysed unless an "
                    "appropriate tool has accessed the dataset."
                ),
            )

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession | None,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        """Extract payroll filters from the current user input."""

        for message in context.input_messages:
            text = (
                message.text
                if hasattr(message, "text")
                else ""
            )

            if not isinstance(text, str):
                continue

            detected_years = re.findall(
                r"\b20\d{2}\b",
                text,
            )

            if detected_years:
                # Replace the previous selection when the user provides
                # one or more explicit payroll years.
                state["years"] = list(
                    dict.fromkeys(
                        int(year)
                        for year in detected_years
                        if int(year)
                        in AVAILABLE_PAYROLL_YEARS
                    )
                )

            pay_grade_match = re.search(
                r"\bpay\s+grade\s*(?:is|=|:)?\s*"
                r"([A-Za-z0-9-]+)",
                text,
                flags=re.IGNORECASE,
            )

            if pay_grade_match:
                # Normalize the Pay Grade for consistent reuse in later
                # conversation turns.
                state["pay_grade"] = (
                    pay_grade_match
                    .group(1)
                    .upper()
                )