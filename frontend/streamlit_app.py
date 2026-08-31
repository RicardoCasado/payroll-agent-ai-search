import os
from typing import Any
from uuid import uuid4

import requests
import streamlit as st
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from streamlit_persistence import (
    CONVERSATIONS_FILE,
    load_streamlit_conversations,
    save_streamlit_conversations,
)


load_dotenv()


DEFAULT_AGENT_ENDPOINT = (
    "https://ricardo286malaga-9265-resource.services.ai.azure.com/"
    "api/projects/ricardo286malaga-9265/"
    "agents/payroll-agent-ai-search/"
    "endpoint/protocols/openai/responses"
    "?api-version=v1"
)

AGENT_ENDPOINT = os.getenv(
    "FOUNDRY_AGENT_ENDPOINT",
    DEFAULT_AGENT_ENDPOINT,
)

AZURE_AI_SCOPE = "https://ai.azure.com/.default"

USER_AVATAR = ":material/person:"
ASSISTANT_AVATAR = ":material/smart_toy:"


st.set_page_config(
    page_title="Payroll AI Agent",
    page_icon="💼",
    layout="centered",
)


st.markdown(
    """
    <style>
        .main .block-container {
            max-width: 950px;
            padding-top: 2rem;
        }

        [data-testid="stChatMessage"] {
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 12px;
            padding: 0.75rem;
            margin-bottom: 0.75rem;
        }

        [data-testid="stSidebar"] {
            min-width: 310px;
        }

        .payroll-subtitle {
            color: #6b7280;
            margin-bottom: 1.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_azure_credential() -> DefaultAzureCredential:
    """Create and reuse the Azure credential."""

    return DefaultAzureCredential()


def extract_response_text(
    response_data: dict[str, Any],
) -> str:
    """Extract assistant text from a Responses API response."""

    text_parts: list[str] = []

    for output_item in response_data.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "output_text":
                text = content_item.get("text")

                if text:
                    text_parts.append(text)

    if text_parts:
        return "\n".join(text_parts)

    raise RuntimeError(
        "The agent returned a response, but no output text "
        "could be extracted."
    )


def call_payroll_agent(
    user_message: str,
    previous_response_id: str | None,
) -> tuple[str, str]:
    """Send a message to the deployed payroll agent."""

    access_token = get_azure_credential().get_token(
        AZURE_AI_SCOPE
    ).token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    request_body: dict[str, Any] = {
        "input": user_message,
        "store": True,
    }

    if previous_response_id:
        request_body["previous_response_id"] = (
            previous_response_id
        )

    response = requests.post(
        AGENT_ENDPOINT,
        headers=headers,
        json=request_body,
        timeout=240,
    )

    if not response.ok:
        raise RuntimeError(
            f"Agent request failed with HTTP "
            f"{response.status_code}:\n{response.text}"
        )

    response_data = response.json()
    response_id = response_data.get("id")

    if not response_id:
        raise RuntimeError(
            "The agent response did not include a response ID."
        )

    return (
        extract_response_text(response_data),
        response_id,
    )


def create_new_conversation() -> str:
    """Create a new independent Foundry conversation chain."""

    conversation_id = str(uuid4())

    st.session_state.conversations[conversation_id] = {
        "title": "New conversation",
        "messages": [],
        "previous_response_id": None,
    }

    return conversation_id


def create_conversation_title(
    user_message: str,
    maximum_length: int = 40,
) -> str:
    """Create a short title from the first user message."""

    clean_message = " ".join(user_message.split())

    if len(clean_message) <= maximum_length:
        return clean_message

    return clean_message[:maximum_length].rstrip() + "..."


def save_current_conversations() -> None:
    """Save the current Streamlit conversation state."""

    save_streamlit_conversations(
        conversations=st.session_state.conversations,
        current_conversation_id=(
            st.session_state.current_conversation_id
        ),
    )


if "conversations" not in st.session_state:
    (
        restored_conversations,
        restored_current_id,
    ) = load_streamlit_conversations()

    st.session_state.conversations = restored_conversations
    st.session_state.current_conversation_id = (
        restored_current_id
    )


if not st.session_state.conversations:
    first_conversation_id = create_new_conversation()
    st.session_state.current_conversation_id = (
        first_conversation_id
    )
    save_current_conversations()

elif (
    not st.session_state.current_conversation_id
    or st.session_state.current_conversation_id
    not in st.session_state.conversations
):
    st.session_state.current_conversation_id = next(
        iter(st.session_state.conversations)
    )


if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

if "ui_notice" not in st.session_state:
    st.session_state.ui_notice = None

if "last_error" not in st.session_state:
    st.session_state.last_error = None


current_conversation_id = (
    st.session_state.current_conversation_id
)

current_conversation = st.session_state.conversations[
    current_conversation_id
]


with st.sidebar:
    st.title("💼 Payroll Agent")

    st.caption(
        "Payroll analysis, validation, comparison "
        "and regulatory document search."
    )

    if st.button(
        "Start new conversation",
        use_container_width=True,
    ):
        new_conversation_id = create_new_conversation()
        st.session_state.current_conversation_id = (
            new_conversation_id
        )
        st.session_state.pending_question = None
        st.session_state.ui_notice = (
            "A new conversation was created."
        )
        save_current_conversations()
        st.rerun()

    st.divider()

    number_of_conversations = len(
        st.session_state.conversations
    )

    st.subheader(
        f"Conversations ({number_of_conversations})"
    )

    for conversation_id, conversation in reversed(
        list(st.session_state.conversations.items())
    ):
        is_current = (
            conversation_id
            == st.session_state.current_conversation_id
        )

        button_label = conversation["title"]

        if is_current:
            button_label = f"💬 {button_label}"

        if st.button(
            button_label,
            key=f"conversation_{conversation_id}",
            use_container_width=True,
        ):
            st.session_state.current_conversation_id = (
                conversation_id
            )
            st.session_state.pending_question = None
            save_current_conversations()
            st.rerun()

    with st.expander("Manage conversation"):
        new_title = st.text_input(
            "Conversation title",
            value=current_conversation["title"],
            key=f"title_{current_conversation_id}",
            max_chars=60,
        )

        if st.button(
            "Rename conversation",
            key=f"rename_{current_conversation_id}",
            use_container_width=True,
        ):
            cleaned_title = new_title.strip()

            if cleaned_title:
                current_conversation["title"] = cleaned_title
                st.session_state.ui_notice = (
                    "The conversation was renamed."
                )
                save_current_conversations()
                st.rerun()
            else:
                st.warning(
                    "The conversation title cannot be empty."
                )

        confirm_deletion = st.checkbox(
            "Confirm conversation deletion",
            key=f"confirm_delete_{current_conversation_id}",
        )

        if st.button(
            "Delete conversation",
            key=f"delete_{current_conversation_id}",
            use_container_width=True,
            disabled=not confirm_deletion,
        ):
            del st.session_state.conversations[
                current_conversation_id
            ]

            if st.session_state.conversations:
                next_conversation_id = next(
                    reversed(st.session_state.conversations)
                )
            else:
                next_conversation_id = create_new_conversation()

            st.session_state.current_conversation_id = (
                next_conversation_id
            )
            st.session_state.pending_question = None
            st.session_state.ui_notice = (
                "The conversation was deleted."
            )
            save_current_conversations()
            st.rerun()

    st.divider()
    st.subheader("Example questions")

    if st.button(
        "📊 Salary statistics",
        use_container_width=True,
    ):
        st.session_state.pending_question = (
            "Calculate the Annual Base Salary statistics "
            "for Pay Grade 13 in 2026."
        )

    if st.button(
        "✅ Validate payroll data",
        use_container_width=True,
    ):
        st.session_state.pending_question = (
            "Run the general payroll data validation for 2026."
        )

    if st.button(
        "📈 Compare payroll periods",
        use_container_width=True,
    ):
        st.session_state.pending_question = (
            "Compare the 2025 and 2026 payroll periods."
        )

    if st.button(
        "📚 Search payroll regulations",
        use_container_width=True,
    ):
        st.session_state.pending_question = (
            "Search the indexed payroll documentation for "
            "overtime rules applicable to public employees "
            "and cite the document title and source."
        )

    st.divider()

    with st.expander("⚙️ Technical panel"):
        current_message_count = len(
            current_conversation["messages"]
        )

        st.metric(
            "Stored conversations",
            number_of_conversations,
        )

        st.metric(
            "Messages in current conversation",
            current_message_count,
        )

        st.write("**Hosted agent:**")
        st.code(
            "payroll-agent-ai-search",
            language=None,
        )

        st.write("**Foundry agent endpoint:**")
        st.code(AGENT_ENDPOINT, language=None)

        st.write("**Previous response ID:**")
        st.code(
            current_conversation.get(
                "previous_response_id"
            )
            or "Not created yet",
            language=None,
        )

        st.write("**Local conversation ID:**")
        st.code(current_conversation_id, language=None)

        st.write("**Conversation file:**")
        st.code(
            str(CONVERSATIONS_FILE),
            language=None,
        )

        if CONVERSATIONS_FILE.exists():
            file_size = CONVERSATIONS_FILE.stat().st_size
            st.write(f"**JSON size:** {file_size:,} bytes")
        else:
            st.warning(
                "The conversation JSON file does not exist."
            )

        if st.session_state.last_error:
            st.error("Latest application error:")
            st.code(
                st.session_state.last_error,
                language=None,
            )
        else:
            st.success(
                "No application errors have been recorded "
                "in this Streamlit session."
            )


st.title("💼 Payroll AI Agent")

st.markdown(
    """
    <div class="payroll-subtitle">
        Analyse payroll data and indexed regulations using
        the hosted Microsoft Foundry payroll agent.
    </div>
    """,
    unsafe_allow_html=True,
)


if st.session_state.ui_notice:
    st.success(st.session_state.ui_notice)
    st.session_state.ui_notice = None


if not current_conversation["messages"]:
    st.info(
        "Start by writing a payroll question or select "
        "one of the examples from the sidebar."
    )


for message in current_conversation["messages"]:
    avatar = (
        USER_AVATAR
        if message["role"] == "user"
        else ASSISTANT_AVATAR
    )

    with st.chat_message(
        message["role"],
        avatar=avatar,
    ):
        st.markdown(message["content"])


typed_question = st.chat_input(
    "Ask a question about payroll data..."
)

user_input = (
    typed_question
    or st.session_state.pending_question
)

st.session_state.pending_question = None


if user_input:
    if not current_conversation["messages"]:
        current_conversation["title"] = (
            create_conversation_title(user_input)
        )

    current_conversation["messages"].append({
        "role": "user",
        "content": user_input,
    })

    save_current_conversations()

    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(user_input)

    with st.chat_message(
        "assistant",
        avatar=ASSISTANT_AVATAR,
    ):
        with st.spinner(
            "Analysing payroll information..."
        ):
            try:
                (
                    response_text,
                    response_id,
                ) = call_payroll_agent(
                    user_message=user_input,
                    previous_response_id=(
                        current_conversation.get(
                            "previous_response_id"
                        )
                    ),
                )

                st.markdown(response_text)

                current_conversation["messages"].append({
                    "role": "assistant",
                    "content": response_text,
                })

                current_conversation[
                    "previous_response_id"
                ] = response_id

                st.session_state.last_error = None
                save_current_conversations()

            except Exception as error:
                error_message = (
                    "The payroll agent could not complete "
                    "the request. Check Azure CLI "
                    "authentication, the agent endpoint, "
                    "and your Foundry permissions."
                )

                st.error(error_message)

                current_conversation["messages"].append({
                    "role": "assistant",
                    "content": error_message,
                })

                st.session_state.last_error = repr(error)
                save_current_conversations()

                print(
                    "Streamlit payroll agent error:",
                    repr(error),
                )
