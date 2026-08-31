# Architecture diagrams

These diagrams provide a visual overview of the main component dependencies and the hosted agent initialization process.

## Component dependencies

The payroll agent combines Microsoft Foundry services, local Python tools, structured payroll data and regulatory document retrieval.

```mermaid
flowchart TB
    UI["Streamlit frontend"] --> RP["Responses Protocol"]
    RP --> HOST["ResponsesHostServer"]
    HOST --> AGENT["Payroll Agent"]

    AGENT --> CLIENT["FoundryChatClient"]
    AGENT --> TOOLBOX["Foundry Toolbox"]
    AGENT --> TOOLS["Python payroll tools"]
    AGENT --> CONTEXT["PayrollContextProvider"]
    AGENT --> CONTROLS["Middleware and hooks"]
    AGENT --> WORKFLOW["Comparison workflow"]

    CLIENT --> MODEL["Foundry model deployment"]

    TOOLBOX --> SEARCH["Azure AI Search"]
    SEARCH --> DOCUMENTS["Regulatory documents"]

    TOOLS --> DATA["payroll_data.py"]
    WORKFLOW --> DATA
    WORKFLOW --> CLIENT
    DATA --> STORAGE["Azure Blob Storage"]
```

### Component responsibilities

- `main.py` assembles and starts the hosted payroll agent.
- `FoundryChatClient` connects the agent to the configured model deployment.
- `FoundryToolbox` exposes the `payroll_search` retrieval tool.
- Python tools perform deterministic calculations and validations.
- `payroll_data.py` provides shared access to payroll CSV files.
- Middleware, hooks and the context provider add execution controls and conversational context.
- Streamlit communicates with the hosted agent through the Responses Protocol.

## Agent initialization flow

The hosted agent is initialized when the container starts `main.py`.

<div align="center">

```mermaid
flowchart TD
    START["`Start
    main.py`"] --> ENV["`Load configuration
    local or hosted environment`"]

    ENV --> VALIDATE{"`Required variables
    available?`"}

    VALIDATE -- No --> ERROR["`Stop with
    configuration error`"]

    VALIDATE -- Yes --> IDENTITY["`Create credential
    DefaultAzureCredential`"]

    IDENTITY --> CLIENTS["`Create Foundry clients
    FoundryChatClient
    FoundryToolbox`"]

    CLIENTS --> ASSEMBLE["`Register agent components
    instructions and tools
    context and middleware`"]

    ASSEMBLE --> SERVER["`Create response server
    ResponsesHostServer`"]

    SERVER --> RUN["`Start hosted agent
    and accept requests`"]
```
</div>

### Initialization result

After initialization, the server exposes the agent through the Responses Protocol. The agent can then select local payroll tools, execute the comparison workflow or retrieve regulatory documents through Azure AI Search.
