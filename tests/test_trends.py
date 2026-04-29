"""
Tests for src/trends.py — genre normalisation, trending boost, analytics,
and CSV round-trip persistence.
No network calls are made; fetch_internet_trends is not exercised here.
"""

import os
import tempfile

import pytest

from src.trends import (
    _normalize_genre,
    _normalize_track,
    fetch_trending,
    apply_trending_boost,
    get_top_genres,
    recommend_from_trends,
    save_trends_csv,
    load_trends_csv,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def _make_tracks(n: int = 5) -> list:
    genres = ["pop", "hip-hop", "pop", "country", "hip-hop"]
    return [
        {
            "id": 1000 + i,
            "title": f"Track {i}",
            "artist": f"Artist {i}",
            "genre": genres[i % len(genres)],
            "mood": "happy",
            "energy": 0.7,
            "tempo_bpm": 120.0,
            "valence": 0.7,
            "danceability": 0.7,
            "acousticness": 0.2,
            "popularity": round((n - i) / n, 2),
            "chart_rank": i + 1,
        }
        for i in range(n)
    ]


SCORED_SONGS = [
    ({"id": 1, "title": "A", "artist": "X", "genre": "pop",    "mood": "happy",
      "energy": 0.8, "tempo_bpm": 120, "valence": 0.8, "danceability": 0.8, "acousticness": 0.1},
     3.0, "Genre match (+2.0); Mood match (+1.5)"),
    ({"id": 2, "title": "B", "artist": "Y", "genre": "rock",   "mood": "intense",
      "energy": 0.9, "tempo_bpm": 150, "valence": 0.4, "danceability": 0.6, "acousticness": 0.1},
     1.5, "Energy match (+1.5)"),
    ({"id": 3, "title": "C", "artist": "Z", "genre": "hip-hop","mood": "confident",
      "energy": 0.8, "tempo_bpm": 96, "valence": 0.6, "danceability": 0.85, "acousticness": 0.1},
     2.0, "Mood match (+1.5); Energy match (+0.5)"),
]

TRENDING = {"trending_genres": ["pop", "hip-hop"], "trending_items": [], "source": "simulated"}


# ---------------------------------------------------------------------------
# _normalize_genre
# ---------------------------------------------------------------------------

def test_normalize_genre_known_mapping():
    assert _normalize_genre("Hip-Hop/Rap") == "hip-hop"
    assert _normalize_genre("R&B/Soul") == "r&b"
    assert _normalize_genre("Dance/Electronic") == "electronic"
    assert _normalize_genre("Pop") == "pop"
    assert _normalize_genre("Country") == "country"


def test_normalize_genre_case_insensitive():
    assert _normalize_genre("POP") == "pop"
    assert _normalize_genre("COUNTRY") == "country"


def test_normalize_genre_unknown_passes_through():
    result = _normalize_genre("SomeUnknownGenre")
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# _normalize_track
# ---------------------------------------------------------------------------

def test_normalize_track_has_all_required_fields():
    raw = {"name": "Test Song", "artistName": "Test Artist", "genres": [{"name": "Pop"}]}
    track = _normalize_track(raw, rank=1)
    required = ["id", "title", "artist", "genre", "mood", "energy", "tempo_bpm",
                "valence", "danceability", "acousticness", "popularity", "chart_rank"]
    for field in required:
        assert field in track, f"Missing field: {field}"


def test_normalize_track_popularity_decreases_with_rank():
    t1 = _normalize_track({"name": "A", "artistName": "X", "genres": [{"name": "Pop"}]}, rank=1)
    t50 = _normalize_track({"name": "B", "artistName": "Y", "genres": [{"name": "Pop"}]}, rank=50)
    assert t1["popularity"] > t50["popularity"]


def test_normalize_track_rank1_has_max_popularity():
    t = _normalize_track({"name": "A", "artistName": "X", "genres": [{"name": "Pop"}]}, rank=1)
    assert t["popularity"] == 1.0


def test_normalize_track_id_offset_by_1000():
    t = _normalize_track({"name": "A", "artistName": "X", "genres": []}, rank=5)
    assert t["id"] == 1005


def test_normalize_track_energy_within_bounds():
    for rank in range(1, 11):
        t = _normalize_track({"name": "A", "artistName": "X", "genres": [{"name": "Pop"}]}, rank=rank)
        assert 0.0 <= t["energy"] <= 1.0


# ---------------------------------------------------------------------------
# fetch_trending
# ---------------------------------------------------------------------------

def test_fetch_trending_returns_none_on_simulate_failure():
    result = fetch_trending(simulate_failure=True)
    assert result is None


def test_fetch_trending_returns_dict_with_required_keys():
    result = fetch_trending(simulate_failure=False)
    if result is not None:  # may be None if trends.csv is empty/absent
        assert "trending_genres" in result
        assert "trending_items" in result
        assert "source" in result
        assert "timestamp" in result


def test_fetch_trending_genres_is_a_list():
    result = fetch_trending(simulate_failure=False)
    if result is not None:
        assert isinstance(result["trending_genres"], list)


# ---------------------------------------------------------------------------
# apply_trending_boost
# ---------------------------------------------------------------------------

def test_boost_increases_score_for_matching_genre():
    boosted = apply_trending_boost(SCORED_SONGS, TRENDING, boost=0.5)
    pop_entry = next(s for s, _, _ in boosted if s["genre"] == "pop")
    original_score = next(score for s, score, _ in SCORED_SONGS if s["genre"] == "pop")
    boosted_score  = next(score for s, score, _ in boosted   if s["genre"] == "pop")
    assert boosted_score == pytest.approx(original_score + 0.5)


def test_boost_does_not_change_score_for_non_matching_genre():
    boosted = apply_trending_boost(SCORED_SONGS, TRENDING, boost=0.5)
    rock_original = next(score for s, score, _ in SCORED_SONGS if s["genre"] == "rock")
    rock_boosted  = next(score for s, score, _ in boosted   if s["genre"] == "rock")
    assert rock_boosted == pytest.approx(rock_original)


def test_boost_result_is_sorted_descending():
    boosted = apply_trending_boost(SCORED_SONGS, TRENDING, boost=0.5)
    scores = [score for _, score, _ in boosted]
    assert scores == sorted(scores, reverse=True)


def test_boost_returns_original_list_when_no_trending_data():
    result = apply_trending_boost(SCORED_SONGS, None, boost=0.5)
    assert result == SCORED_SONGS


def test_boost_adds_note_to_explanation():
    boosted = apply_trending_boost(SCORED_SONGS, TRENDING, boost=0.5)
    pop_explanation = next(exp for s, _, exp in boosted if s["genre"] == "pop")
    assert "Trending genre boost" in pop_explanation


# ---------------------------------------------------------------------------
# get_top_genres
# ---------------------------------------------------------------------------

def test_get_top_genres_returns_correct_count():
    tracks = _make_tracks(5)
    result = get_top_genres(tracks, top_n=2)
    assert len(result) == 2


def test_get_top_genres_returns_tuples_of_genre_and_score():
    tracks = _make_tracks(5)
    result = get_top_genres(tracks, top_n=3)
    for genre, score in result:
        assert isinstance(genre, str)
        assert isinstance(score, float)


def test_get_top_genres_sorted_descending():
    tracks = _make_tracks(5)
    result = get_top_genres(tracks, top_n=5)
    scores = [s for _, s in result]
    assert scores == sorted(scores, reverse=True)


def test_get_top_genres_pop_ranks_high_in_sample():
    tracks = _make_tracks(5)
    result = get_top_genres(tracks, top_n=5)
    genres = [g for g, _ in result]
    # pop appears at ranks 1 and 3 (higher popularity) vs hip-hop at ranks 2 and 5
    assert genres.index("pop") < genres.index("country")


# ---------------------------------------------------------------------------
# recommend_from_trends
# ---------------------------------------------------------------------------

def test_recommend_from_trends_returns_correct_count():
    tracks = _make_tracks(10)
    result = recommend_from_trends(tracks, top_n=5)
    assert len(result) == 5


def test_recommend_from_trends_sorted_by_chart_rank():
    tracks = _make_tracks(10)
    result = recommend_from_trends(tracks, top_n=5)
    ranks = [t["chart_rank"] for t in result]
    assert ranks == sorted(ranks)


def test_recommend_from_trends_first_is_rank_1():
    tracks = _make_tracks(5)
    result = recommend_from_trends(tracks, top_n=1)
    assert result[0]["chart_rank"] == 1


# ---------------------------------------------------------------------------
# save_trends_csv / load_trends_csv  (round-trip)
# ---------------------------------------------------------------------------

def test_save_and_load_round_trip(tmp_path):
    path = str(tmp_path / "test_trends.csv")
    tracks = _make_tracks(3)
    assert save_trends_csv(tracks, path=path) is True

    loaded = load_trends_csv(path=path)
    assert loaded is not None
    assert len(loaded) == 3


def test_load_preserves_field_types(tmp_path):
    path = str(tmp_path / "test_trends.csv")
    tracks = _make_tracks(2)
    save_trends_csv(tracks, path=path)
    loaded = load_trends_csv(path=path)

    for t in loaded:
        assert isinstance(t["id"],           int)
        assert isinstance(t["energy"],        float)
        assert isinstance(t["popularity"],    float)
        assert isinstance(t["chart_rank"],    int)
        assert isinstance(t["title"],         str)


def test_load_preserves_values(tmp_path):
    path = str(tmp_path / "test_trends.csv")
    tracks = _make_tracks(1)
    save_trends_csv(tracks, path=path)
    loaded = load_trends_csv(path=path)

    assert loaded[0]["title"]      == tracks[0]["title"]
    assert loaded[0]["genre"]      == tracks[0]["genre"]
    assert loaded[0]["chart_rank"] == tracks[0]["chart_rank"]


def test_load_returns_none_for_missing_file(tmp_path):
    result = load_trends_csv(path=str(tmp_path / "nonexistent.csv"))
    assert result is None


def test_load_returns_none_for_header_only_file(tmp_path):
    path = str(tmp_path / "empty.csv")
    with open(path, "w") as f:
        f.write("id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness,popularity,chart_rank\n")
    result = load_trends_csv(path=path)
    assert result is None
