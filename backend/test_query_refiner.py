import app.query_refiner as query_refiner


def run_tests():
    cache_store = {}
    rewrite_calls = {"count": 0}

    original_get_cached = query_refiner.get_cached_refined_query
    original_store = query_refiner.store_refined_query
    original_rewrite = query_refiner._rewrite_query

    def fake_get_cached_refined_query(question: str, context: str = ""):
        return cache_store.get((question, context))

    def fake_store_refined_query(question: str, refined_query: str, context: str = ""):
        cache_store[(question, context)] = refined_query

    def fake_rewrite_query(question: str, history: str = "") -> str:
        rewrite_calls["count"] += 1
        if question == "what is this doc about?":
            return "Summarize the contents of the uploaded document."
        if question == "ipl today?":
            return "What IPL matches are scheduled today?"
        if question == "tell more":
            assert "Assistant: The uploaded document explains the quarterly sales summary." in history
            return "Provide additional details about the previously discussed topic."
        return question

    query_refiner.get_cached_refined_query = fake_get_cached_refined_query
    query_refiner.store_refined_query = fake_store_refined_query
    query_refiner._rewrite_query = fake_rewrite_query

    try:
        assert query_refiner.refine_query("what is this doc about?") == "Summarize the contents of the uploaded document."
        assert query_refiner.refine_query("ipl today?") == "What IPL matches are scheduled today?"

        history = "Chat History:\nAssistant: The uploaded document explains the quarterly sales summary.\n\n"
        assert query_refiner.refine_query("tell more", history) == "Provide additional details about the previously discussed topic."

        before = rewrite_calls["count"]
        assert query_refiner.refine_query("ipl today?") == "What IPL matches are scheduled today?"
        assert rewrite_calls["count"] == before

        print("QUERY REFINER TESTS PASSED")
    finally:
        query_refiner.get_cached_refined_query = original_get_cached
        query_refiner.store_refined_query = original_store
        query_refiner._rewrite_query = original_rewrite


if __name__ == "__main__":
    run_tests()
