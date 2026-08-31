"""Configure and run the hosted Microsoft Foundry payroll agent.

The agent combines payroll analysis tools backed by CSV files in
Azure Blob Storage with regulatory document retrieval through
Azure AI Search.
"""

import os

from agent_framework import Agent
from agent_framework.foundry import (
    FoundryChatClient,
    FoundryToolbox,
)
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv



from agent_tools import (
    get_salary_statistics,
    validate_payroll_values,
    validate_payroll_data,
    find_exempt_employees_with_overtime
)

from memory_providers import PayrollContextProvider

from middleware import (
    logging_middleware,
    tool_logging_middleware,
)

from workflow import run_payroll_comparison_workflow

from payroll_hooks import tool_budget_hooks

# Load local development settings from .env when the file exists.
# In Microsoft Foundry, the hosted environment supplies the equivalent configuration through deployment and platform-managed variables.
load_dotenv()


PAYROLL_AGENT_INSTRUCTIONS = """
You are a payroll data analysis and payroll regulations assistant.

Available tools:

- get_salary_statistics:
  Calculate Annual Base Salary statistics for a payroll year and
  Pay Grade.

- validate_payroll_values:
  Find missing and negative values in a selected payroll column.

- validate_payroll_data:
  Check missing Pay Grades, impossible Birth Years, and invalid
  position date ranges.

- find_exempt_employees_with_overtime:
  Find exempt payroll records that contain Overtime Pay.

- payroll_search:
  Search indexed payroll regulations, employment policies, FLSA
  guidance, and related documents.

- run_payroll_comparison_workflow:
  Validate and compare the configured 2025 and 2026 payroll datasets.

Tool-selection rules:

- Use payroll data tools for calculations and data-quality checks.
- Use payroll_search for regulatory, documentary, or policy questions.
- When a request combines data analysis and regulatory interpretation,
  use both types of tools when necessary.
- Use only the tools required to answer the request.
- Ask a concise clarification if a required parameter is missing and
  is not available from the conversation context.

Response rules:

- Never invent payroll values, records, citations, or conclusions.
- State the filters used and distinguish payroll records from unique
  employees.
- Clearly separate calculated results from documentary information.
- Cite the document title and source URL for regulatory claims.
- Treat workflow interpretations as hypotheses rather than proven
  causes.
- Do not present regulatory information as legal advice.
- If a tool returns no data or an error, state it explicitly.
- Keep answers clear, structured, and concise.

For greetings or unrelated conversational messages, answer normally
without using a tool.
"""


def main():

    # Prefer the deployment variable used by Microsoft Foundry.
    # FOUNDRY_MODEL_NAME remains available as a local fallback.
    model_name = (
        os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        or os.getenv("FOUNDRY_MODEL_NAME")
    )

    if not model_name:
        raise RuntimeError(
            "Model deployment name is not configured. Set "
            "AZURE_AI_MODEL_DEPLOYMENT_NAME or FOUNDRY_MODEL_NAME."
        )

    toolbox_endpoint = os.getenv(
        "TOOLBOX_PAYROLL_SEARCH_TOOLBOX_MCP_ENDPOINT"
    )

    if not toolbox_endpoint:
        raise RuntimeError(
            "Payroll Search toolbox endpoint is not configured. Set "
            "TOOLBOX_PAYROLL_SEARCH_TOOLBOX_MCP_ENDPOINT."
        )

    # DefaultAzureCredential uses the developer's Azure CLI credentials
    # locally and the hosted agent's managed identity in Azure.
    credential = DefaultAzureCredential()

    # Create the chat client that communicates with the configured model
    # deployment in the Microsoft Foundry project.
    client = FoundryChatClient(
        project_endpoint=os.environ[
            "FOUNDRY_PROJECT_ENDPOINT"
        ],
        model=model_name,
        credential=credential,
    )

    # Connect to the Foundry Toolbox that exposes payroll_search through MCP.
    payroll_search_toolbox = FoundryToolbox(
        credential,
        url=toolbox_endpoint,
    )

    # Assemble the model client, payroll tools, contextual memory, middleware, etc
    agent = Agent(
        client=client,
        instructions=PAYROLL_AGENT_INSTRUCTIONS,
        tools=[
            payroll_search_toolbox,
            get_salary_statistics,
            validate_payroll_values,
            validate_payroll_data,
            find_exempt_employees_with_overtime,
            run_payroll_comparison_workflow,
        ],

        # Disable model-response storage. Conversation state required by the
        # hosted application is handled separately by the hosting infrastructure
        default_options={
            "store": False,
        },
        context_providers=[
            PayrollContextProvider(),
        ],        
        middleware=[            
            tool_budget_hooks,
            logging_middleware,
            tool_logging_middleware,
        ]
    )

    # Expose the agent through the Responses Protocol used by Foundry
    # hosting and external clients.
    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()