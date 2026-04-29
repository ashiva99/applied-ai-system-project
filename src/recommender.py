from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        scored = []
        for song in self.songs:
            score = 0.0
            if song.genre == user.favorite_genre:
                score += 2.0
            if song.mood == user.favorite_mood:
                score += 1.5
            score += max(0.0, 1.0 - abs(song.energy - user.target_energy))
            acoustic_bonus = song.acousticness * 0.5 if user.likes_acoustic else (1.0 - song.acousticness) * 0.3
            score += acoustic_bonus
            scored.append((score, song))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [song for _, song in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        reasons = []
        if song.genre == user.favorite_genre:
            reasons.append(f"Genre match: {song.genre}")
        if song.mood == user.favorite_mood:
            reasons.append(f"Mood match: {song.mood}")
        if abs(song.energy - user.target_energy) < 0.2:
            reasons.append(f"Energy close to target ({song.energy:.2f} vs {user.target_energy:.2f})")
        if not reasons:
            reasons.append("General feature similarity")
        return "; ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            songs.append(
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                }
            )
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a song against user preferences; returns (score: float, reasons: List[str])."""
    score = 0.0
    reasons: List[str] = []

    if user_prefs.get("genre") == song.get("genre"):
        score += 2.0
        reasons.append("Genre match (+2.0)")

    if user_prefs.get("mood") == song.get("mood"):
        score += 1.5
        reasons.append("Mood match (+1.5)")

    for feature in ["energy", "valence", "danceability"]:
        if feature in user_prefs and user_prefs[feature] is not None:
            feature_score = 1.0 - abs(float(user_prefs[feature]) - float(song.get(feature, 0.0)))
            feature_score = max(0.0, feature_score)
            score += feature_score
            reasons.append(f"{feature.capitalize()} match (+{feature_score:.2f})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score and rank all songs; return top k as list of (song_dict, score, explanation) tuples."""
    scored_songs: List[Tuple[Dict, float, str]] = []

    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons) if reasons else "No strong feature match"
        scored_songs.append((song, score, explanation))

    scored_songs.sort(key=lambda item: item[1], reverse=True)
    return scored_songs[:k]
