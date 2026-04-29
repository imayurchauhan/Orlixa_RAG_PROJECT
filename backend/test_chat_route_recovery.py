import asyncio

import app.main as main


def run_tests():
    original_chat_exists = main.chat_exists
    original_get_chat_messages = main.get_chat_messages
    original_ensure_chat_record = main._ensure_chat_record
    original_add_message = main.add_message
    original_route_query = main.route_query

    state = {
        "existing": set(),
        "messages": [],
        "ensured": [],
    }

    def fake_chat_exists(chat_id: str) -> bool:
        return chat_id in state["existing"]

    def fake_get_chat_messages(chat_id: str):
        return [m for m in state["messages"] if m["chat_id"] == chat_id]

    def fake_ensure_chat_record(chat_id: str, title: str = "New Chat") -> None:
        state["existing"].add(chat_id)
        state["ensured"].append((chat_id, title))

    def fake_add_message(chat_id: str, role: str, content: str, source=None):
        msg = {
            "chat_id": chat_id,
            "role": role,
            "content": content,
            "source": source,
        }
        state["messages"].append(msg)
        return msg

    def fake_route_query(session_id: str, question: str):
        return {"answer": f"Echo: {question}", "source": "llm"}

    main.chat_exists = fake_chat_exists
    main.get_chat_messages = fake_get_chat_messages
    main._ensure_chat_record = fake_ensure_chat_record
    main.add_message = fake_add_message
    main.route_query = fake_route_query

    try:
        result = asyncio.run(main.api_get_chat("missing-chat"))
        assert result == {"messages": []}
        assert state["ensured"] == []

        result = asyncio.run(
            main.chat_scoped(
                "missing-chat",
                main.ChatRequest(message="hello"),
            )
        )
        assert result.answer == "Echo: hello"
        assert result.source == "llm"
        assert state["ensured"] == [("missing-chat", "New Chat")]
        assert state["messages"] == [
            {"chat_id": "missing-chat", "role": "user", "content": "hello", "source": None},
            {"chat_id": "missing-chat", "role": "assistant", "content": "Echo: hello", "source": "llm"},
        ]

        result = asyncio.run(main.api_delete_chat("missing-chat"))
        assert result == {"status": "deleted"}

        print("CHAT ROUTE RECOVERY TESTS PASSED")
    finally:
        main.chat_exists = original_chat_exists
        main.get_chat_messages = original_get_chat_messages
        main._ensure_chat_record = original_ensure_chat_record
        main.add_message = original_add_message
        main.route_query = original_route_query


if __name__ == "__main__":
    run_tests()
