import asyncio

import app.main as main


def run_tests():
    original_chat_exists = main.chat_exists
    original_get_chat_messages = main.get_chat_messages
    original_ensure_chat = main.ensure_chat
    original_add_message = main.add_message
    original_route_query = main.route_query
    original_delete_chat = main.delete_chat

    current_user = {"id": "user-1", "email": "user1@example.com"}
    state = {
        "existing": set(),
        "messages": [],
        "ensured": [],
        "deleted": [],
    }

    def fake_chat_exists(user_id: str, chat_id: str) -> bool:
        return (user_id, chat_id) in state["existing"]

    def fake_get_chat_messages(user_id: str, chat_id: str):
        return [
            m for m in state["messages"]
            if m["chat_id"] == chat_id and m["user_id"] == user_id
        ]

    def fake_ensure_chat(user_id: str, chat_id: str, title: str = "New Chat"):
        state["existing"].add((user_id, chat_id))
        state["ensured"].append((user_id, chat_id, title))
        return {"id": chat_id, "title": title, "user_id": user_id}

    def fake_add_message(chat_id: str, role: str, content: str, source=None):
        msg = {
            "chat_id": chat_id,
            "user_id": current_user["id"],
            "role": role,
            "content": content,
            "source": source,
        }
        state["messages"].append(msg)
        return msg

    def fake_route_query(session_id: str, question: str):
        return {"answer": f"Echo: {question}", "source": "llm"}

    def fake_delete_chat(user_id: str, chat_id: str):
        state["deleted"].append((user_id, chat_id))
        return True

    main.chat_exists = fake_chat_exists
    main.get_chat_messages = fake_get_chat_messages
    main.ensure_chat = fake_ensure_chat
    main.add_message = fake_add_message
    main.route_query = fake_route_query
    main.delete_chat = fake_delete_chat

    try:
        result = asyncio.run(main.api_get_chat("missing-chat", current_user))
        assert result == {"messages": []}
        assert state["ensured"] == []

        result = asyncio.run(
            main.chat_scoped(
                "missing-chat",
                main.ChatRequest(message="hello"),
                current_user,
            )
        )
        assert result.answer == "Echo: hello"
        assert result.source == "llm"
        assert state["ensured"] == [("user-1", "missing-chat", "New Chat")]
        assert state["messages"] == [
            {
                "chat_id": "missing-chat",
                "user_id": "user-1",
                "role": "user",
                "content": "hello",
                "source": None,
            },
            {
                "chat_id": "missing-chat",
                "user_id": "user-1",
                "role": "assistant",
                "content": "Echo: hello",
                "source": "llm",
            },
        ]

        result = asyncio.run(main.api_delete_chat("missing-chat", current_user))
        assert result == {"status": "deleted"}
        assert state["deleted"] == [("user-1", "missing-chat")]

        print("CHAT ROUTE RECOVERY TESTS PASSED")
    finally:
        main.chat_exists = original_chat_exists
        main.get_chat_messages = original_get_chat_messages
        main.ensure_chat = original_ensure_chat
        main.add_message = original_add_message
        main.route_query = original_route_query
        main.delete_chat = original_delete_chat


if __name__ == "__main__":
    run_tests()
