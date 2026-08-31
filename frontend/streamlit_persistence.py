import json
from pathlib import Path
from typing import Any


PROJECT_DIRECTORY = Path(__file__).resolve().parent

CONVERSATIONS_FILE = (
    PROJECT_DIRECTORY
    / "Database"
    / "streamlit_foundry_conversations.json"
)


def save_streamlit_conversations(
    conversations: dict[str, dict[str, Any]],
    current_conversation_id: str,
) -> None:
    """Save all Streamlit conversations to JSON."""

    CONVERSATIONS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serializable_conversations = {}

    for conversation_id, conversation in (
        conversations.items()
    ):
        serializable_conversations[conversation_id] = {
            "title": conversation["title"],
            "messages": conversation["messages"],
            "previous_response_id": conversation.get(
                "previous_response_id"
            ),
        }

    data = {
        "current_conversation_id": (
            current_conversation_id
        ),
        "conversations": serializable_conversations,
    }

    temporary_file = (
        CONVERSATIONS_FILE.with_suffix(".tmp")
    )

    with temporary_file.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )

    temporary_file.replace(CONVERSATIONS_FILE)


def load_streamlit_conversations() -> tuple[
    dict[str, dict[str, Any]],
    str | None,
]:
    """Load saved Streamlit conversations from JSON."""

    if not CONVERSATIONS_FILE.exists():
        return {}, None

    try:
        with CONVERSATIONS_FILE.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        restored_conversations = {}

        for conversation_id, conversation in (
            data.get("conversations", {}).items()
        ):
            restored_conversations[conversation_id] = {
                "title": conversation.get(
                    "title",
                    "Conversation",
                ),
                "messages": conversation.get(
                    "messages",
                    [],
                ),
                "previous_response_id": conversation.get(
                    "previous_response_id"
                ),
            }

        current_conversation_id = data.get(
            "current_conversation_id"
        )

        if (
            current_conversation_id
            not in restored_conversations
        ):
            current_conversation_id = None

        return (
            restored_conversations,
            current_conversation_id,
        )

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(
            "Could not restore Streamlit conversations:",
            repr(error),
        )

        return {}, None
