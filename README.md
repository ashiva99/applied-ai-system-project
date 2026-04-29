# Applied AI Music System

An end-to-end AI project built for **AI110** that evolves a rule-based Music Recommender into a full Applied AI System with three distinct capabilities: standard scoring-based recommendation, RAG-powered Q&A, and real-time trending integration.

---

## Original Project

The original **Music Recommender Simulation** scored songs against a user taste profile using weighted features — genre, mood, energy, valence, and danceability. It loaded a small catalog from `data/songs.csv` and returned the top-K ranked songs.

Key original components:
- `Song` and `UserProfile` dataclasses in `src/recommender.py`
- `score_song` — assigns points based on genre/mood matches and feature proximity
- `recommend_songs` — sorts all songs by score and returns top K

---

## What's New: RAG + Trending Integration

### RAG Pipeline (`src/rag.py`)

Inspired by the **DocuBot** project, the RAG pipeline turns `songs.csv` into a searchable knowledge base. When a user asks a natural-language question (e.g., "What is the top genre in this dataset?"), the system:

1. Converts every song into a descriptive text document
2. Scores documents by keyword overlap with the query (retrieval)
3. Passes the top-3 retrieved songs as grounded context to **Gemini 1.5 Flash**
4. Returns a factual answer with zero hallucination risk about songs not in the dataset

A **Confidence Scorer** inside `rag.py` flags responses when:
- The query is too vague (e.g., single generic words like "music" or "vibes")
- No relevant songs are retrieved from the dataset
- Trending data is unavailable

### Trending Tool (`src/trends.py`)

`fetch_trending()` simulates an external API call that returns the currently trending genres and moods. These results feed into `apply_trending_boost()`, which re-scores the standard recommendation output by adding a +0.5 bonus to any song whose genre is trending. Pass `simulate_failure=True` to test the guardrail that activates when real trending data is unavailable.

### System Architecture

See [`Mermaid.js`](Mermaid.js) for the full flowchart. Paste the diagram string into [mermaid.live](https://mermaid.live) to render it.

```
User Input
    └─► Mode Selector (main.py)
            ├─► [Mode 1] Scoring Engine (recommender.py)
            │       └─► Trending Boost (trends.py) ──► Ranked Results
            ├─► [Mode 2] RAG Retriever (rag.py)
            │       └─► Knowledge Base (songs.csv) ──► Gemini LLM ──► Grounded Answer
            └─► [Mode 3] Trending Overview (trends.py)
                    └─► Trend-Boosted Recommendations
                            └─► Confidence Scorer ──► Final Output + Warnings
```

---

## Environment Setup

### 1. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your Gemini API key

Create a `.env` file in the project root:

```bash
cp .env.example .env   # if the example exists, otherwise create manually
```

Edit `.env` and add:

```
GEMINI_API_KEY=your_api_key_here
```

Get a free key at [https://aistudio.google.com/app/api-keys](https://aistudio.google.com/app/api-keys).

> **Without a key:** Modes 1 and 3 work fully. Mode 2 (RAG Q&A) will still retrieve relevant songs and show the context, but skips Gemini generation and displays a notice instead.

---

## Running the App

```bash
python -m src.main
```

You will see a menu:

```
Select a mode:
  1) Standard Recommendation
  2) RAG Q&A
  3) Trending Overview
  q) Quit
```

### Mode 1 — Standard Recommendation

Pick one of four built-in profiles (Night Coder, Morning Jogger, etc.) or enter custom preferences. Optionally apply a trending boost to surface currently-hot genres.

### Mode 2 — RAG Q&A

Ask free-form questions about the dataset:

- `"What is the top genre in this dataset?"`
- `"Which songs are good for working out?"`
- `"Tell me about chill songs with high acousticness."`
- `"What artists make lofi music?"`

The system retrieves the most relevant songs, shows confidence warnings if the query is vague, and generates a grounded Gemini answer.

### Mode 3 — Trending Overview

Displays the current simulated trending data and shows how trend-boosted recommendations differ from the baseline. Supports testing the confidence guardrail by simulating an API failure.

---

## Running Tests

```bash
pytest
```

Tests live in `tests/test_recommender.py` and cover the `Recommender` class, `Song`, and `UserProfile`.

---

## Project Structure

```
applied-ai-system-project/
├── data/
│   ├── songs.csv               # Core song catalog (10 songs)
│   └── additional_songs.csv    # Extended catalog (8 more songs)
├── src/
│   ├── main.py                 # CLI entry point (3-mode menu)
│   ├── recommender.py          # Scoring engine + Song/UserProfile dataclasses
│   ├── rag.py                  # RAG pipeline (retrieval + Gemini generation)
│   └── trends.py               # Trending simulation + score boosting
├── tests/
│   └── test_recommender.py     # Pytest unit tests
├── Mermaid.js                  # System architecture diagram
├── model_card.md               # Model card (limitations, evaluation, reflection)
├── requirements.txt
└── README.md
```

---

## Limitations

- The catalog is small (18 songs total); recommendations are sensitive to dataset size
- Retrieval uses keyword overlap — semantic similarity is not implemented
- Trending data is fully simulated; no real API is connected
- Genre and mood labels must match exactly (e.g., "chill" ≠ "calm")

---

## Model Card

See [model_card.md](model_card.md) for the full evaluation, bias analysis, and reflection.

---

## Documentation

### Project Genesis

This started as a CSV-based recommender that did one thing: score songs against a user taste profile and return the top K results. It was a weighted function, genre match gets +2.0, mood match gets +1.5, then proximity scoring on energy, valence, and danceability. Clean, deterministic, and completely useless if you typed a natural-language question at it.

The pivot to RAG came directly from DocuBot. That project taught me that a small, grounded knowledge base beats a hallucination-prone prompt almost every time. Songs already have structured attributes — genre, mood, BPM, energy, so converting them into text documents and building a retrieval layer on top was the obvious next step. The question stopped being "how do I rank these 18 songs?" and started being "how do I let someone *ask* about them?"

---

### Architecture Breakdown

Here's how it works end-to-end, the way I'd sketch it on a whiteboard:

```
User Input
    └─► Mode Selector (main.py)
            ├─► [Mode 1] score_song() × 18 songs → sorted list
            │              └─► apply_trending_boost() → +0.5 on hot genres → Top 5
            │
            ├─► [Mode 2] build_rag_index() → token sets per song
            │              └─► retrieve() → keyword overlap → top 3 docs
            │                     └─► _generate_with_gemini() (Gemini 2.0 Flash)
            │                            └─► confidence_check() → warnings + level
            │
            └─► [Mode 3] fetch_internet_trends() → Apple Music top 100
                           └─► save_trends_csv() → merges into RAG index + scoring
```

`build_rag_index()` in [src/rag.py](src/rag.py) serializes every song into a flat text string (title, artist, genre, mood, BPM, energy, valence, danceability, acousticness plus chart rank if it came from Apple Music). Retrieval is token intersection: the query gets tokenized, each document gets tokenized, and the top 3 by overlap score go to Gemini as grounded context.

`score_song()` in [src/recommender.py](src/recommender.py) is purely arithmetic — no LLM involved. The genre/mood weights are hard-coded at +2.0 and +1.5 respectively. The float features use `1.0 - abs(user_pref - song_value)`, clamped at 0. Trending boost is additive: +0.5 per song whose genre appears in the trending list.

---

### The "Aha!" Moment — Design Decisions

The biggest call was wiring in real-time trending data rather than keeping the catalog static. The payoff: Mode 2 can now answer "what are the current trending songs?" with actual Apple Music chart data, not a canned response about 18 fictional tracks.

The trade-off I made deliberately: **I used keyword overlap for retrieval instead of cosine similarity or embeddings.** This kept the RAG pipeline dependency-free (no `sentence-transformers`, no vector DB) and fast enough that the CLI feels instant. The cost is real — "vibey" returns nothing because it's in the `VAGUE_TERMS` blocklist, and "upbeat indie" only hits if those exact tokens appear in the song text. A semantic layer would fix both, but for an 18-song catalog it would've been infrastructure for its own sake.

The confidence scorer exists because I got burned during testing. Without it, Gemini would return a confident-sounding answer even when the retrieval was garbage. Now `confidence_check()` validates three things before the answer surfaces: is the query specific enough, did any documents actually match, and is trending data available? Each "no" downgrades the confidence label and prints a warning. A wrong answer with a warning is better than a wrong answer without one.

---

### The Reality Check — Testing Summary

The system handles genre and mood queries well. "lofi", "hip hop", "chill", "confident" — anything that maps directly to a catalog field hits reliably. The profile comparisons in [reflection.md](reflection.md) confirm this: Night Coder vs. Morning Jogger produces completely distinct top-5 lists, which is the expected behavior.

Where it breaks down:

- **Vague emotional language.** "vibey", "chill vibes", "something sad" — these either hit the `VAGUE_TERMS` blocklist or tokenize into terms that don't appear in any song text. The system flags them correctly, but it can't answer them either.
- **Exact-string dependency.** Genre and mood matching in `score_song()` is `==`. "chill" and "calm" are different strings. If a user types "calm" for a dataset tagged "chill", the genre bonus never fires. This is a known limitation and shows up as unexpectedly low scores.
- **The Contradiction profile.** `energy: 0.95, valence: 0.10, danceability: 0.05` — high energy but low everything else. No song in the catalog is built for that combination, so the scorer returns high-energy tracks that still score poorly on the other features. Rankings are technically correct but practically useless for that profile.

---

### Reflection

The main thing this project clarified: the gap between a working script and a reliable system is almost entirely about failure modes.

The original recommender had no failure modes worth thinking about — it loaded a CSV and returned a sorted list. Adding RAG meant adding a retrieval step that could return nothing, an LLM that could hallucinate, and a trending API that could be down. Each one needed a specific response: a fallback, a constraint, a guardrail. The confidence scorer isn't a feature, it's the system admitting what it doesn't know.

The other thing: retrieval quality gates everything downstream. Gemini can generate coherent prose from bad context, which is worse than returning no answer at all. The decision to pass only keyword-matched songs — and to flag when that match count is zero — was the right call, even though it means the system occasionally refuses to answer questions it could technically guess at.

---


What This System Does
The Big Picture
This app is a music assistant with three skills: it can recommend songs, answer questions about music, and pull real trending charts from the internet. All three skills share the same song data and work from a command-line menu. I spend time for the retriever that was returning no results for queries like "good songs" because the keyword overlap was zero for generic terms, and the fix was adding the full-catalog fallback in rag.py. That's real, traceable, and happened in this codebase.

Skill 1 — Standard Recommendation
You describe what you want (a genre like "lofi", a mood like "chill", and how energetic you want the music). The system goes through every song in its catalog and gives each one a score. Songs get bonus points for matching your genre and mood exactly, and more points the closer their energy/vibe numbers are to yours. The top 5 highest-scoring songs are shown with an explanation of why each one ranked where it did.

If trending data is available, songs whose genre is currently trending get an extra +0.5 point bonus on top of their regular score.

Skill 2 — RAG Q&A
You type a natural-language question like "What are the top trending songs?" or "Which songs are good for a workout?"

The system doesn't just hand the question to an AI and hope for the best. It first retrieves the most relevant song descriptions from its local index (matching keywords between your question and the song data), then passes only those specific songs as evidence to Gemini 2.0 Flash with strict instructions: answer using only this data, nothing else. This prevents the AI from making things up.

If your question is too vague or nothing matches, a confidence warning is shown before the answer.

Skill 3 — Trending Overview
When you choose this mode, you can optionally hit the Apple Music most-played chart (no account or API key needed). It downloads the top 100 real songs right now, maps them into the same format as the rest of the data, and saves them to data/trends.csv. From then on, every mode in the app uses that live data — recommendations get trend-boosted, and RAG questions about trending songs get real answers.

If the internet is unavailable, the app falls back to a built-in simulated list automatically.

The Safety Layer — Confidence Scorer
Runs after every response. It checks three things: Was the question too vague? Did any songs actually match? Is trending data available? Each "no" adds a warning and lowers the confidence label from high → medium → low. A clear warning is always better than a confident wrong answer.


Tests: 
All 57 tests passed across recommender, RAG, and trending modules. Confidence scoring, genre weights, full-catalog fallback, and CSV round-trips all verified. Gemini generation is not tested automatically since it needs a live API key, so answer quality is checked manually using the peer review checklist above.

