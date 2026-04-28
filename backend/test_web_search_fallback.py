import app.web_search as web_search


def run_tests():
    original_get = web_search.requests.get

    class DummyResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    def fake_get(url: str, headers=None, timeout=10):
        assert "format=rss" in url
        return DummyResponse(
            """<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0">
  <channel>
    <item>
      <title>IPL 2026 | Live Cricket Scores</title>
      <link>https://www.espncricinfo.com/live-cricket-score</link>
      <description>Catch the fastest live cricket scores and ball-by-ball commentary.</description>
    </item>
  </channel>
</rss>"""
        )

    web_search.requests.get = fake_get

    try:
        variants = web_search._query_variants("What is the current live match score of the Indian Premier League (IPL)?")
        assert "IPL live score today" in variants

        results = web_search._search_bing_rss("IPL live score today", max_results=5)
        assert results == [
            {
                "title": "IPL 2026 | Live Cricket Scores",
                "body": "Catch the fastest live cricket scores and ball-by-ball commentary.",
                "href": "https://www.espncricinfo.com/live-cricket-score",
            }
        ]
        print("WEB SEARCH FALLBACK TESTS PASSED")
    finally:
        web_search.requests.get = original_get


if __name__ == "__main__":
    run_tests()
