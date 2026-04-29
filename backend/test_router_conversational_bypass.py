import app.router as router


def run_tests():
    original_get_history_str = router.get_history_str
    original_add_history = router.add_history
    original_refine_query = router.refine_query
    original_get_session_images = router._get_session_images
    original_get_cached = router.get_cached
    original_has_documents = router.has_documents
    original_try_document = router._try_document
    original_try_llm = router._try_llm
    original_try_web = router._try_web

    history_calls = []
    refine_calls = {"count": 0}
    downstream_calls = {"document": 0, "llm": 0, "web": 0}

    def fake_get_history_str(session_id: str) -> str:
        return "Chat History:\nAssistant: Royal Challengers Bengaluru won the Indian Premier League title in 2025.\n\n"

    def fake_add_history(session_id: str, question: str, answer: str):
        history_calls.append((session_id, question, answer))

    def fake_refine_query(question: str, history: str = "") -> str:
        refine_calls["count"] += 1
        return question

    def fake_get_session_images(session_id: str):
        return []

    def fake_get_cached(session_id: str, question: str, context: str = ""):
        return None

    def fake_has_documents(session_id: str) -> bool:
        return False

    def fake_try_document(session_id: str, question: str, history: str, images=None):
        downstream_calls["document"] += 1
        return None

    def fake_try_llm(question: str, history: str, images=None):
        downstream_calls["llm"] += 1
        return {"answer": "unexpected", "source": "llm"}

    def fake_try_web(question: str, history: str, images=None, original_question: str = ""):
        downstream_calls["web"] += 1
        return {"answer": "unexpected", "source": "web"}

    router.get_history_str = fake_get_history_str
    router.add_history = fake_add_history
    router.refine_query = fake_refine_query
    router._get_session_images = fake_get_session_images
    router.get_cached = fake_get_cached
    router.has_documents = fake_has_documents
    router._try_document = fake_try_document
    router._try_llm = fake_try_llm
    router._try_web = fake_try_web

    try:
        result = router.route_query("conv-test", "ok leave it")
        assert result == {
            "answer": "Okay, we can leave it here. Let me know if you want to ask something else.",
            "source": "system",
        }
        assert refine_calls["count"] == 0
        assert downstream_calls == {"document": 0, "llm": 0, "web": 0}
        assert history_calls == [
            (
                "conv-test",
                "ok leave it",
                "Okay, we can leave it here. Let me know if you want to ask something else.",
            )
        ]

        result = router.route_query("conv-test", "ok")
        assert result == {"answer": "Okay.", "source": "system"}
        assert refine_calls["count"] == 0
        assert downstream_calls == {"document": 0, "llm": 0, "web": 0}
        assert history_calls[-1] == ("conv-test", "ok", "Okay.")

        print("ROUTER CONVERSATIONAL BYPASS TESTS PASSED")
    finally:
        router.get_history_str = original_get_history_str
        router.add_history = original_add_history
        router.refine_query = original_refine_query
        router._get_session_images = original_get_session_images
        router.get_cached = original_get_cached
        router.has_documents = original_has_documents
        router._try_document = original_try_document
        router._try_llm = original_try_llm
        router._try_web = original_try_web


if __name__ == "__main__":
    run_tests()
