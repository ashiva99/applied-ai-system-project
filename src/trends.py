"""
Trending music module for the Applied AI Music System.

Supports two data sources:
  - Apple Music most-played chart (live, via urllib — no API key required)
  - Simulated fallback pool (used when network is unavailable or data/trends.csv is absent)

Persistence: fetched tracks are saved to / loaded from data/trends.csv, which mirrors
the songs.csv schema plus two extra columns: popularity and chart_rank.
"""

import csv
import json
import os
import random
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional, Tuple

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TRENDS_CSV = os.path.join(_ROOT, "data", "trends.csv")

# CSV field order — matches songs.csv schema plus two trend-specific columns
_CSV_FIELDS = [
    "id", "title", "artist", "genre", "mood",
    "energy", "tempo_bpm", "valence", "danceability", "acousticness",
    "popularity", "chart_rank",
]

# ---------------------------------------------------------------------------
# Genre normalisation
# ---------------------------------------------------------------------------

_GENRE_MAP: Dict[str, str] = {
    "hip-hop/rap":        "hip-hop",
    "hip hop":            "hip-hop",
    "hip-hop":            "hip-hop",
    "rap":                "hip-hop",
    "r&b/soul":           "r&b",
    "r&b":                "r&b",
    "soul":               "r&b",
    "dance/electronic":   "electronic",
    "electronic":         "electronic",
    "edm":                "electronic",
    "house":              "electronic",
    "pop":                "pop",
    "country":            "country",
    "alternative":        "alternative",
    "alternative/indie":  "alternative",
    "indie":              "alternative",
    "rock":               "rock",
    "hard rock":          "rock",
    "latin":              "latin",
    "classical":          "classical",
    "jazz":               "jazz",
    "reggae":             "reggae",
    "reggaeton":          "latin",
    "k-pop":              "k-pop",
    "metal":              "metal",
    "folk":               "folk",
    "blues":              "blues",
    "gospel":             "gospel",
    "christian & gospel": "gospel",
    "christian":          "gospel",
    "soundtrack":         "pop",
    "world":              "world",
}

# Feature defaults keyed by normalised genre
_GENRE_DEFAULTS: Dict[str, Dict] = {
    "pop":         {"mood": "happy",      "energy": 0.78, "tempo_bpm": 120, "valence": 0.72, "danceability": 0.78, "acousticness": 0.18},
    "hip-hop":     {"mood": "confident",  "energy": 0.82, "tempo_bpm": 96,  "valence": 0.62, "danceability": 0.86, "acousticness": 0.10},
    "r&b":         {"mood": "romantic",   "energy": 0.62, "tempo_bpm": 98,  "valence": 0.70, "danceability": 0.78, "acousticness": 0.22},
    "rock":        {"mood": "intense",    "energy": 0.84, "tempo_bpm": 130, "valence": 0.52, "danceability": 0.60, "acousticness": 0.14},
    "country":     {"mood": "heartfelt",  "energy": 0.62, "tempo_bpm": 108, "valence": 0.68, "danceability": 0.64, "acousticness": 0.58},
    "electronic":  {"mood": "euphoric",   "energy": 0.88, "tempo_bpm": 128, "valence": 0.66, "danceability": 0.88, "acousticness": 0.08},
    "latin":       {"mood": "happy",      "energy": 0.80, "tempo_bpm": 105, "valence": 0.82, "danceability": 0.88, "acousticness": 0.20},
    "alternative": {"mood": "moody",      "energy": 0.72, "tempo_bpm": 118, "valence": 0.48, "danceability": 0.58, "acousticness": 0.30},
    "classical":   {"mood": "peaceful",   "energy": 0.30, "tempo_bpm": 80,  "valence": 0.60, "danceability": 0.25, "acousticness": 0.90},
    "jazz":        {"mood": "relaxed",    "energy": 0.45, "tempo_bpm": 92,  "valence": 0.65, "danceability": 0.55, "acousticness": 0.75},
    "k-pop":       {"mood": "happy",      "energy": 0.84, "tempo_bpm": 124, "valence": 0.78, "danceability": 0.84, "acousticness": 0.12},
    "gospel":      {"mood": "uplifting",  "energy": 0.68, "tempo_bpm": 104, "valence": 0.78, "danceability": 0.66, "acousticness": 0.40},
    "metal":       {"mood": "rebellious", "energy": 0.95, "tempo_bpm": 160, "valence": 0.38, "danceability": 0.52, "acousticness": 0.04},
    "folk":        {"mood": "nostalgic",  "energy": 0.42, "tempo_bpm": 90,  "valence": 0.58, "danceability": 0.44, "acousticness": 0.82},
    "reggae":      {"mood": "uplifting",  "energy": 0.60, "tempo_bpm": 92,  "valence": 0.80, "danceability": 0.72, "acousticness": 0.38},
    "blues":       {"mood": "moody",      "energy": 0.55, "tempo_bpm": 88,  "valence": 0.45, "danceability": 0.52, "acousticness": 0.60},
    "world":       {"mood": "happy",      "energy": 0.65, "tempo_bpm": 100, "valence": 0.70, "danceability": 0.70, "acousticness": 0.45},
}
_GENRE_DEFAULTS["default"] = {
    "mood": "chill", "energy": 0.65, "tempo_bpm": 110,
    "valence": 0.60, "danceability": 0.68, "acousticness": 0.25,
}


def _normalize_genre(raw: str) -> str:
    key = raw.lower().strip()
    if key in _GENRE_MAP:
        return _GENRE_MAP[key]
    # Best-effort: take the first token before "/" or "&"
    first = key.split("/")[0].split("&")[0].strip()
    return _GENRE_MAP.get(first, first)


# ---------------------------------------------------------------------------
# Internet fetch — Apple Music most-played chart (no API key required)
# ---------------------------------------------------------------------------

_APPLE_RSS = "https://rss.applemarketingtools.com/api/v2/us/music/most-played/{limit}/songs.json"


def fetch_internet_trends(limit: int = 100) -> Optional[List[Dict]]:
    """
    Fetch top trending songs from the Apple Music most-played chart.
    Returns a list of normalised song dicts, or None on any network/parse failure.
    """
    url = _APPLE_RSS.format(limit=limit)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AppliedAIMusicSystem/1.0"},
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"  [Network error: {exc}]")
        return None

    results = raw.get("feed", {}).get("results", [])
    if not results:
        print("  [Fetch returned empty results]")
        return None

    return [_normalize_track(entry, rank) for rank, entry in enumerate(results[:limit], start=1)]


def _normalize_track(entry: Dict, rank: int) -> Dict:
    """Convert a raw Apple Music RSS entry into a songs.csv-compatible row."""
    genres_list = entry.get("genres", [])
    raw_genre   = genres_list[0]["name"] if genres_list else "Pop"
    genre       = _normalize_genre(raw_genre)
    defaults    = _GENRE_DEFAULTS.get(genre, _GENRE_DEFAULTS["default"])

    # Small reproducible jitter so every song in the same genre isn't identical
    rng    = random.Random(rank)
    jitter = lambda v: round(max(0.0, min(1.0, v + rng.uniform(-0.07, 0.07))), 2)

    return {
        "id":           1000 + rank,
        "title":        entry.get("name", "Unknown"),
        "artist":       entry.get("artistName", "Unknown"),
        "genre":        genre,
        "mood":         defaults["mood"],
        "energy":       jitter(defaults["energy"]),
        "tempo_bpm":    defaults["tempo_bpm"],
        "valence":      jitter(defaults["valence"]),
        "danceability": jitter(defaults["danceability"]),
        "acousticness": jitter(defaults["acousticness"]),
        "popularity":   round((101 - rank) / 100, 2),   # rank 1 → 1.00, rank 100 → 0.01
        "chart_rank":   rank,
    }


# ---------------------------------------------------------------------------
# CSV persistence
# ---------------------------------------------------------------------------

def save_trends_csv(tracks: List[Dict], path: str = _TRENDS_CSV) -> bool:
    """Save normalised trend tracks to CSV. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(tracks)
        return True
    except Exception as exc:
        print(f"  [CSV write error: {exc}]")
        return False


def load_trends_csv(path: str = _TRENDS_CSV) -> Optional[List[Dict]]:
    """
    Load trend tracks from CSV. Returns None if the file doesn't exist or is unreadable.
    Returned dicts include the two extra fields (popularity, chart_rank).
    """
    if not os.path.exists(path):
        return None
    try:
        tracks = []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                tracks.append({
                    "id":           int(row["id"]),
                    "title":        row["title"],
                    "artist":       row["artist"],
                    "genre":        row["genre"],
                    "mood":         row["mood"],
                    "energy":       float(row["energy"]),
                    "tempo_bpm":    float(row["tempo_bpm"]),
                    "valence":      float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                    "popularity":   float(row["popularity"]),
                    "chart_rank":   int(row["chart_rank"]),
                })
        return tracks if tracks else None
    except Exception as exc:
        print(f"  [CSV read error: {exc}]")
        return None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def get_top_genres(tracks: List[Dict], top_n: int = 5) -> List[Tuple[str, float]]:
    """
    Return the top N genres weighted by track popularity scores.
    Gives more weight to chart-toppers than lower-ranked songs.
    """
    genre_scores: Dict[str, float] = {}
    for t in tracks:
        g = t.get("genre", "unknown")
        genre_scores[g] = genre_scores.get(g, 0.0) + t.get("popularity", 0.5)
    return sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]


def recommend_from_trends(tracks: List[Dict], top_n: int = 5) -> List[Dict]:
    """Return the top N tracks sorted by chart rank (rank 1 = most popular)."""
    return sorted(tracks, key=lambda t: t.get("chart_rank", 999))[:top_n]


def _find_top_artist(tracks: List[Dict], genre: str) -> str:
    """Return the artist of the highest-ranked track in a given genre."""
    genre_tracks = [t for t in tracks if t.get("genre") == genre]
    if not genre_tracks:
        return "Unknown"
    return min(genre_tracks, key=lambda t: t.get("chart_rank", 999))["artist"]


# ---------------------------------------------------------------------------
# fetch_trending — used by the rest of the system
# Prefers saved trends.csv; falls back to simulated pool.
# ---------------------------------------------------------------------------

_SIMULATED_TREND_POOL = [
    {"genre": "pop",       "mood": "happy",     "example_artist": "Neon Echo",      "hot_score": 0.95},
    {"genre": "lofi",      "mood": "chill",     "example_artist": "LoRoom",         "hot_score": 0.88},
    {"genre": "indie pop", "mood": "happy",     "example_artist": "Indigo Parade",  "hot_score": 0.82},
    {"genre": "synthwave", "mood": "moody",     "example_artist": "Neon Echo",      "hot_score": 0.79},
    {"genre": "hip-hop",   "mood": "confident", "example_artist": "Metro Cipher",   "hot_score": 0.76},
    {"genre": "r&b",       "mood": "romantic",  "example_artist": "June Ember",     "hot_score": 0.73},
    {"genre": "ambient",   "mood": "chill",     "example_artist": "Orbit Bloom",    "hot_score": 0.71},
    {"genre": "house",     "mood": "euphoric",  "example_artist": "Pulse Harbor",   "hot_score": 0.68},
]


def fetch_trending(simulate_failure: bool = False) -> Optional[Dict]:
    """
    Return a trending-data dict compatible with apply_trending_boost.
    Priority: simulate_failure=True → None → trends.csv → simulated pool.
    """
    if simulate_failure:
        return None

    saved = load_trends_csv()
    if saved:
        top_genres = get_top_genres(saved, top_n=3)
        total_pop  = sum(s for _, s in top_genres) or 1.0
        items = [
            {
                "genre":          g,
                "mood":           _GENRE_DEFAULTS.get(g, _GENRE_DEFAULTS["default"])["mood"],
                "example_artist": _find_top_artist(saved, g),
                "hot_score":      round(s / total_pop, 2),
            }
            for g, s in top_genres
        ]
        mtime = datetime.fromtimestamp(os.path.getmtime(_TRENDS_CSV)).isoformat()
        return {
            "trending_genres": [g for g, _ in top_genres],
            "trending_items":  items,
            "source":          "trends.csv",
            "timestamp":       mtime,
        }

    # Simulated fallback
    pool = _SIMULATED_TREND_POOL.copy()
    random.shuffle(pool[:5])
    top3 = pool[:3]
    return {
        "trending_genres": [t["genre"] for t in top3],
        "trending_items":  top3,
        "source":          "simulated",
        "timestamp":       datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Downstream helpers (unchanged interface)
# ---------------------------------------------------------------------------

def apply_trending_boost(
    songs_scored: List[Tuple],
    trending_data: Optional[Dict],
    boost: float = 0.5,
) -> List[Tuple]:
    """
    Boost scores for songs whose genre appears in the current trending list.
    songs_scored: list of (song_dict, score, explanation) from recommend_songs.
    Returns a new sorted list.
    """
    if not trending_data or not trending_data.get("trending_genres"):
        return songs_scored

    trending_genres = set(trending_data["trending_genres"])
    boosted = []
    for song, score, explanation in songs_scored:
        extra = 0.0
        if song.get("genre") in trending_genres:
            extra = boost
            explanation = f"{explanation}; Trending genre boost (+{boost:.1f})"
        boosted.append((song, score + extra, explanation))

    boosted.sort(key=lambda x: x[1], reverse=True)
    return boosted


def format_trending_summary(trending_data: Optional[Dict]) -> str:
    """Return a human-readable summary of the current trending data."""
    if not trending_data:
        return "  [No trending data available]"

    source = trending_data.get("source", "unknown")
    source_label = "Apple Music Charts (cached)" if source == "trends.csv" else source.title()
    lines = [
        f"  Source:  {source_label}",
        f"  Updated: {trending_data.get('timestamp', 'N/A')}",
        "  Top Trending Genres:",
    ]
    for item in trending_data.get("trending_items", []):
        lines.append(
            f"    • {item['genre'].title():<14} ({item['mood']})  "
            f"e.g. {item['example_artist']}  [hot: {item['hot_score']:.2f}]"
        )
    return "\n".join(lines)
