import json
from pathlib import Path


def load_session_content(session_id: str) -> list[dict]:
    session_file = Path(f"sessions/{session_id}.json")

    if not session_file.exists():
        return []

    with session_file.open("r", encoding="utf-8") as file:
        return json.load(file)["messages"]


def store_session_content(session_id: str, messages: list[dict]) -> None:
    session_file = Path(f"sessions/{session_id}.json")
    session_file.parent.mkdir(exist_ok=True)

    content = {"messages": messages}

    with session_file.open("w", encoding="utf-8") as file:
        json.dump(content, file, ensure_ascii=False, indent=2)