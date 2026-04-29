from src.recommender import Song, UserProfile, Recommender, score_song, recommend_songs

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ---------------------------------------------------------------------------
# score_song
# ---------------------------------------------------------------------------

POP_SONG = {
    "id": 1, "title": "Test", "artist": "X",
    "genre": "pop", "mood": "happy",
    "energy": 0.8, "tempo_bpm": 120,
    "valence": 0.9, "danceability": 0.8, "acousticness": 0.2,
}

def test_score_song_genre_match_adds_2():
    prefs = {"genre": "pop", "mood": "other", "energy": None, "valence": None, "danceability": None}
    score, reasons = score_song(prefs, POP_SONG)
    assert score == 2.0
    assert any("Genre" in r for r in reasons)


def test_score_song_mood_match_adds_1_5():
    prefs = {"genre": "other", "mood": "happy", "energy": None, "valence": None, "danceability": None}
    score, reasons = score_song(prefs, POP_SONG)
    assert score == 1.5
    assert any("Mood" in r for r in reasons)


def test_score_song_genre_and_mood_match_adds_3_5():
    prefs = {"genre": "pop", "mood": "happy", "energy": None, "valence": None, "danceability": None}
    score, _ = score_song(prefs, POP_SONG)
    assert score == 3.5


def test_score_song_exact_energy_match_adds_1():
    prefs = {"genre": "", "mood": "", "energy": 0.8, "valence": None, "danceability": None}
    score, _ = score_song(prefs, POP_SONG)
    assert abs(score - 1.0) < 0.01


def test_score_song_far_energy_adds_near_zero():
    prefs = {"genre": "", "mood": "", "energy": 0.0, "valence": None, "danceability": None}
    score, _ = score_song(prefs, POP_SONG)
    # energy diff = 0.8 → score = max(0, 1 - 0.8) = 0.2
    assert abs(score - 0.2) < 0.01


def test_score_song_no_match_returns_zero():
    prefs = {"genre": "jazz", "mood": "sad", "energy": None, "valence": None, "danceability": None}
    score, _ = score_song(prefs, POP_SONG)
    assert score == 0.0


def test_score_song_returns_reasons_list():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.8}
    score, reasons = score_song(prefs, POP_SONG)
    assert isinstance(reasons, list)
    assert len(reasons) > 0


# ---------------------------------------------------------------------------
# recommend_songs
# ---------------------------------------------------------------------------

CATALOG = [
    {"id": 1, "title": "Pop Hit",   "artist": "A", "genre": "pop",  "mood": "happy",
     "energy": 0.8, "tempo_bpm": 120, "valence": 0.9, "danceability": 0.8, "acousticness": 0.1},
    {"id": 2, "title": "Lofi Chill","artist": "B", "genre": "lofi", "mood": "chill",
     "energy": 0.4, "tempo_bpm": 80,  "valence": 0.6, "danceability": 0.5, "acousticness": 0.8},
    {"id": 3, "title": "Rock Storm","artist": "C", "genre": "rock", "mood": "intense",
     "energy": 0.9, "tempo_bpm": 150, "valence": 0.4, "danceability": 0.6, "acousticness": 0.1},
]

def test_recommend_songs_returns_k_results():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.8}
    results = recommend_songs(prefs, CATALOG, k=2)
    assert len(results) == 2


def test_recommend_songs_returns_tuples_of_three():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.8}
    results = recommend_songs(prefs, CATALOG, k=3)
    for item in results:
        assert len(item) == 3


def test_recommend_songs_top_result_matches_best_prefs():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.8}
    results = recommend_songs(prefs, CATALOG, k=3)
    top_song, _, _ = results[0]
    assert top_song["genre"] == "pop"


def test_recommend_songs_sorted_by_score_descending():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.8}
    results = recommend_songs(prefs, CATALOG, k=3)
    scores = [score for _, score, _ in results]
    assert scores == sorted(scores, reverse=True)


def test_recommend_songs_k_larger_than_catalog_returns_all():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.9, "danceability": 0.8}
    results = recommend_songs(prefs, CATALOG, k=100)
    assert len(results) == len(CATALOG)
