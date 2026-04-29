"""
Applied AI Music System — CLI entry point.

Modes:
  1  Standard Recommendation  — score-based ranking with optional trending boost
  2  RAG Q&A                  — ask natural-language questions about the dataset
  3  Trending Overview         — browse current trends + get trend-boosted picks
"""

import os
import sys

# Allow plain imports regardless of how the file is invoked
sys.path.insert(0, os.path.dirname(__file__))

from recommender import load_songs, recommend_songs
from rag import build_rag_index, ask_rag
from trends import (
    fetch_trending, apply_trending_boost, format_trending_summary,
    fetch_internet_trends, save_trends_csv, load_trends_csv,
    get_top_genres, recommend_from_trends,
)

# Resolve data paths relative to this file so the script works from any directory
_SRC_DIR = os.path.dirname(__file__)
_ROOT_DIR = os.path.dirname(_SRC_DIR)
_SONGS_CSV = os.path.join(_ROOT_DIR, "data", "songs.csv")
_EXTRA_CSV  = os.path.join(_ROOT_DIR, "data", "additional_songs.csv")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_all_songs() -> list:
    songs = load_songs(_SONGS_CSV)
    if os.path.exists(_EXTRA_CSV):
        songs += load_songs(_EXTRA_CSV)
    return songs


def _print_recommendations(recommendations: list, label: str = "Top Recommendations") -> None:
    print(f"\n{label}:\n")
    for rank, (song, score, reasons) in enumerate(recommendations, 1):
        reason_list = reasons.split("; ") if isinstance(reasons, str) else reasons
        print(f"  {rank}. {song['title']} — {song['artist']}")
        print(f"     Score: {score:.2f}")
        for r in reason_list:
            print(f"       • {r}")
        print()


def _ask_float(prompt: str, lo: float = 0.0, hi: float = 1.0) -> float:
    while True:
        try:
            val = float(input(prompt).strip())
            if lo <= val <= hi:
                return val
            print(f"  Please enter a value between {lo} and {hi}.")
        except ValueError:
            print("  Invalid input — enter a decimal number.")


# ---------------------------------------------------------------------------
# Mode 1: Standard Recommendation
# ---------------------------------------------------------------------------

_DEMO_PROFILES = {
    "1": ("Night Coder",        {"genre": "lofi",      "mood": "chill",   "energy": 0.35, "valence": 0.55, "danceability": 0.55}),
    "2": ("Morning Jogger",     {"genre": "hip hop",   "mood": "confident","energy": 0.85, "valence": 0.75, "danceability": 0.85}),
    "3": ("Late-Night Melancholy",{"genre": "indie pop","mood": "happy",   "energy": 0.30, "valence": 0.20, "danceability": 0.15}),
    "4": ("The Contradiction",  {"genre": "pop",       "mood": "happy",   "energy": 0.95, "valence": 0.10, "danceability": 0.05}),
}


def mode_standard(songs: list) -> None:
    print("\n=== Standard Recommendation ===")
    print("Choose a profile or enter your own preferences:")
    for key, (name, _) in _DEMO_PROFILES.items():
        print(f"  {key}) {name}")
    print("  5) Enter custom preferences")

    choice = input("\nSelect (1-5): ").strip()

    if choice in _DEMO_PROFILES:
        profile_name, prefs = _DEMO_PROFILES[choice]
        print(f"\nUsing profile: {profile_name}")
    else:
        profile_name = "Custom"
        prefs = {
            "genre":        input("  Preferred genre (e.g. pop, lofi, rock): ").strip().lower(),
            "mood":         input("  Preferred mood (e.g. happy, chill, intense): ").strip().lower(),
            "energy":       _ask_float("  Target energy (0.0-1.0): "),
            "valence":      _ask_float("  Target valence/positivity (0.0-1.0): "),
            "danceability": _ask_float("  Target danceability (0.0-1.0): "),
        }

    use_trending = input("\nApply trending boost? (y/n): ").strip().lower() == "y"
    trending_data = fetch_trending() if use_trending else None

    recommendations = recommend_songs(prefs, songs, k=10)
    if use_trending:
        recommendations = apply_trending_boost(recommendations, trending_data)
        if trending_data:
            print(f"\nTrending data loaded ({', '.join(trending_data['trending_genres'])} are hot right now)")

    _print_recommendations(recommendations[:5], label=f"Top 5 for {profile_name}")


# ---------------------------------------------------------------------------
# Mode 2: RAG Q&A
# ---------------------------------------------------------------------------

def mode_rag(songs: list) -> None:
    print("\n=== RAG Q&A Mode ===")
    print("Ask natural-language questions about the music dataset.")
    print("Type 'quit' to return to the main menu.\n")

    # Merge trend tracks into the index so trend-related queries are answerable
    trend_tracks = load_trends_csv() or []
    all_songs = songs + trend_tracks
    docs = build_rag_index(all_songs)
    trending_data = fetch_trending()

    source_note = "trends.csv" if trend_tracks else "catalog only"
    print(f"  Index: {len(songs)} catalog songs + {len(trend_tracks)} trending tracks ({source_note})\n")

    example_questions = [
        "What is the top genre in this dataset?",
        "Which songs are good for working out?",
        "Tell me about chill songs with high acousticness.",
        "What artists make lofi music in this catalog?",
        "What are the current trending songs?",
        "Which trending songs have the highest popularity?",
    ]
    print("Example questions:")
    for q in example_questions:
        print(f"  • {q}")
    print()

    while True:
        query = input("Your question: ").strip()
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue

        result = ask_rag(query, docs, trending_data)

        # Print confidence + warnings first
        level = result["confidence_level"]
        warnings = result["warnings"]
        if warnings:
            print(f"\n  [Confidence: {level.upper()}]")
            for w in warnings:
                print(f"  ⚠  {w}")

        print(f"\n  Answer:\n  {result['answer']}\n")

        if result["retrieved_songs"]:
            print("  Retrieved context:")
            for s in result["retrieved_songs"]:
                print(f"    - {s['title']} by {s['artist']} ({s['genre']}, {s['mood']})")
        print()


# ---------------------------------------------------------------------------
# Mode 3: Trending Overview
# ---------------------------------------------------------------------------

def mode_trending(songs: list) -> None:
    print("\n=== Trending Music Overview ===")

    # --- Optional: fetch fresh data from Apple Music charts ---
    fetch_new = input("\nFetch latest trends from Apple Music charts? (y/n): ").strip().lower() == "y"
    if fetch_new:
        print("  Contacting Apple Music... ", end="", flush=True)
        tracks = fetch_internet_trends(limit=100)
        if tracks:
            if save_trends_csv(tracks):
                print(f"done — {len(tracks)} tracks saved to data/trends.csv")
            else:
                print("fetched but CSV save failed (results shown in memory only)")
        else:
            print("failed — using existing or simulated data.")
            tracks = None
    else:
        tracks = None

    # --- Simulate failure for guardrail testing ---
    if not fetch_new:
        sim_fail = input("Simulate trending API failure to test guardrail? (y/n): ").strip().lower() == "y"
    else:
        sim_fail = False

    trending_data = fetch_trending(simulate_failure=sim_fail)

    print("\nCurrent Trending Data:")
    print(format_trending_summary(trending_data))

    # --- Top genres and top 5 tracks from trends.csv ---
    trend_tracks = load_trends_csv()
    if trend_tracks:
        print(f"\n--- Top 5 Trending Genres  ({len(trend_tracks)} tracks loaded) ---")
        for genre, weight in get_top_genres(trend_tracks, top_n=5):
            print(f"  • {genre.title():<16} popularity weight: {weight:.2f}")

        print("\n--- Top 5 Trending Tracks (by chart rank) ---\n")
        for i, t in enumerate(recommend_from_trends(trend_tracks, top_n=5), 1):
            print(f"  {i}. #{t['chart_rank']:>3}  {t['title']} — {t['artist']}")
            print(f"       Genre: {t['genre']}  |  Mood: {t['mood']}  |  Popularity: {t['popularity']:.2f}")
        print()

    # --- Trend-boosted picks from local catalog ---
    print("--- Trend-Boosted Catalog Picks ---")
    print("  Trending genres get +0.5 bonus on top of base feature scoring.\n")
    base_prefs = {"genre": "", "mood": "", "energy": 0.5, "valence": 0.6, "danceability": 0.6}
    scored  = recommend_songs(base_prefs, songs, k=len(songs))
    boosted = apply_trending_boost(scored, trending_data, boost=0.5)
    _print_recommendations(boosted[:5], label="Top 5 Trend-Boosted Catalog Picks")

    # --- Confidence guardrail check ---
    from rag import confidence_check
    level, warnings = confidence_check("trending music", [], trending_data)
    if warnings:
        print(f"  [Confidence: {level.upper()}]")
        for w in warnings:
            print(f"  ⚠  {w}")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main() -> None:
    songs = _load_all_songs()
    print(f"\nApplied AI Music System — {len(songs)} songs loaded.")

    menu = {
        "1": ("Standard Recommendation", mode_standard),
        "2": ("RAG Q&A",                 mode_rag),
        "3": ("Trending Overview",        mode_trending),
    }

    while True:
        print("\n" + "=" * 50)
        print("Select a mode:")
        for key, (label, _) in menu.items():
            print(f"  {key}) {label}")
        print("  q) Quit")

        choice = input("\nEnter choice: ").strip().lower()
        if choice == "q":
            print("Goodbye!")
            break
        if choice in menu:
            _, fn = menu[choice]
            fn(songs)
        else:
            print("  Invalid choice — please enter 1, 2, 3, or q.")


if __name__ == "__main__":
    main()
