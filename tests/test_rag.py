"""
Tests for src/rag.py — index building, retrieval, and confidence scoring.
Gemini generation is NOT called; these tests cover everything up to that boundary.
"""

from src.rag import build_rag_index, retrieve, confidence_check

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SONGS = [
    {"id": 1, "title": "Midnight Coding", "artist": "LoRoom",   "genre": "lofi",  "mood": "chill",
     "energy": 0.42, "tempo_bpm": 78, "valence": 0.56, "danceability": 0.62, "acousticness": 0.71},
    {"id": 2, "title": "Storm Runner",    "artist": "Voltline", "genre": "rock",  "mood": "intense",
     "energy": 0.91, "tempo_bpm": 152, "valence": 0.48, "danceability": 0.66, "acousticness": 0.10},
    {"id": 3, "title": "Sunrise City",    "artist": "Neon Echo","genre": "pop",   "mood": "happy",
     "energy": 0.82, "tempo_bpm": 118, "valence": 0.84, "danceability": 0.79, "acousticness": 0.18},
]

TREND_SONG = {
    "id": 1001, "title": "Doors", "artist": "Noah Kahan", "genre": "alternative", "mood": "moody",
    "energy": 0.74, "tempo_bpm": 118, "valence": 0.51, "danceability": 0.62, "acousticness": 0.36,
    "popularity": 0.97, "chart_rank": 4,
}

TRENDING_DATA = {"trending_genres": ["pop", "lofi"], "trending_items": [], "source": "simulated"}


# ---------------------------------------------------------------------------
# build_rag_index
# ---------------------------------------------------------------------------

def test_build_rag_index_creates_one_doc_per_song():
    docs = build_rag_index(SONGS)
    assert len(docs) == len(SONGS)


def test_build_rag_index_doc_has_required_keys():
    docs = build_rag_index(SONGS)
    for doc in docs:
        assert "song" in doc
        assert "text" in doc
        assert "tokens" in doc


def test_build_rag_index_tokens_are_lowercase():
    docs = build_rag_index(SONGS)
    for doc in docs:
        for token in doc["tokens"]:
            assert token == token.lower()


def test_build_rag_index_text_contains_title_and_artist():
    docs = build_rag_index(SONGS)
    assert "Midnight Coding" in docs[0]["text"]
    assert "LoRoom" in docs[0]["text"]


def test_build_rag_index_trend_song_text_contains_trending_keyword():
    docs = build_rag_index([TREND_SONG])
    assert "Trending" in docs[0]["text"]
    assert "Chart rank" in docs[0]["text"]


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------

def test_retrieve_returns_matching_docs():
    docs = build_rag_index(SONGS)
    results = retrieve("lofi chill", docs, top_k=3)
    genres = [r["song"]["genre"] for r in results]
    assert "lofi" in genres


def test_retrieve_respects_top_k():
    docs = build_rag_index(SONGS)
    results = retrieve("rock pop lofi storm", docs, top_k=2)
    assert len(results) <= 2


def test_retrieve_returns_empty_list_when_no_overlap():
    docs = build_rag_index(SONGS)
    results = retrieve("zzzznonexistentterm", docs, top_k=3)
    assert results == []


def test_retrieve_ranks_best_match_first():
    docs = build_rag_index(SONGS)
    # "rock" and "intense" both appear in Storm Runner's text
    results = retrieve("rock intense", docs, top_k=3)
    assert results[0]["song"]["genre"] == "rock"


def test_retrieve_trend_song_matches_trending_query():
    docs = build_rag_index([TREND_SONG])
    results = retrieve("trending popular chart", docs, top_k=1)
    assert len(results) == 1
    assert results[0]["song"]["title"] == "Doors"


# ---------------------------------------------------------------------------
# confidence_check
# ---------------------------------------------------------------------------

def test_confidence_high_when_all_good():
    docs = build_rag_index(SONGS)
    retrieved = retrieve("lofi chill", docs, top_k=3)
    level, warnings = confidence_check("lofi chill", retrieved, TRENDING_DATA)
    assert level == "high"
    assert warnings == []


def test_confidence_flags_vague_query():
    level, warnings = confidence_check("music", [], TRENDING_DATA)
    assert level in ("medium", "low")
    assert any("vague" in w.lower() for w in warnings)


def test_confidence_flags_no_retrieved_docs():
    level, warnings = confidence_check("specific query with no match", [], TRENDING_DATA)
    assert level in ("medium", "low")
    assert any("keyword" in w.lower() or "no" in w.lower() for w in warnings)


def test_confidence_flags_missing_trending_data():
    docs = build_rag_index(SONGS)
    retrieved = retrieve("lofi chill", docs, top_k=3)
    level, warnings = confidence_check("lofi chill", retrieved, None)
    assert level in ("medium", "low")
    assert any("trending" in w.lower() for w in warnings)


def test_confidence_low_when_vague_and_no_docs():
    level, warnings = confidence_check("ok", [], None)
    assert level == "low"
    assert len(warnings) >= 2
