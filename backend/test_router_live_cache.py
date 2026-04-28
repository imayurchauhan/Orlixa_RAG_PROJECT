import app.router as router


def run_tests():
    original_get_history_str = router.get_history_str
    original_refine_query = router.refine_query
    original_get_session_images = router._get_session_images
    original_get_cached = router.get_cached
    original_has_documents = router.has_documents
    original_try_document = router._try_document
    original_try_llm = router._try_llm
    original_try_web = router._try_web
    original_store_cache = router.store_cache
    original_add_history = router.add_history

    store_calls = []
    history_calls = []

    def fake_get_history_str(session_id: str) -> str:
        return ""

    def fake_refine_query(question: str, history: str = "") -> str:
        return "What is the current live IPL score?"

    def fake_get_session_images(session_id: str):
        return []

    def fake_get_cached(session_id: str, question: str, context: str = ""):
        return {
            "answer": "I could not find a reliable answer. Please try rephrasing your question.",
            "source": "web",
        }

    def fake_has_documents(session_id: str) -> bool:
        return False

    def fake_try_document(session_id: str, question: str, history: str, images=None):
        return None

    def fake_try_llm(question: str, history: str, images=None):
        return None

    def fake_try_web(question: str, history: str, images=None):
        assert question == "What is the current live IPL score?"
        return {"answer": "KKR 102/2 after 12 overs.", "source": "web"}

    def fake_store_cache(session_id: str, question: str, answer: str, source: str, context: str = ""):
        store_calls.append((session_id, question, answer, source, context))

    def fake_add_history(session_id: str, question: str, answer: str):
        history_calls.append((session_id, question, answer))

    router.get_history_str = fake_get_history_str
    router.refine_query = fake_refine_query
    router._get_session_images = fake_get_session_images
    router.get_cached = fake_get_cached
    router.has_documents = fake_has_documents
    router._try_document = fake_try_document
    router._try_llm = fake_try_llm
    router._try_web = fake_try_web
    router.store_cache = fake_store_cache
    router.add_history = fake_add_history

    try:
        result = router.route_query("live-cache-test", "search \"IPL live match score\" and give me the live score update")
        assert result == {"answer": "KKR 102/2 after 12 overs.", "source": "web"}
        assert store_calls == []
        assert history_calls == [
            ("live-cache-test", 'search "IPL live match score" and give me the live score update', "KKR 102/2 after 12 overs.")
        ]
        print("ROUTER LIVE CACHE TESTS PASSED")
    finally:
        router.get_history_str = original_get_history_str
        router.refine_query = original_refine_query
        router._get_session_images = original_get_session_images
        router.get_cached = original_get_cached
        router.has_documents = original_has_documents
        router._try_document = original_try_document
        router._try_llm = original_try_llm
        router._try_web = original_try_web
        router.store_cache = original_store_cache
        router.add_history = original_add_history


if __name__ == "__main__":
    run_tests()
