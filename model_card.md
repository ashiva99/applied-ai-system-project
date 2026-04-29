# Model Card: Applied AI Music System

## 1. Model Name

**MoodPulse AI v2.0** — an Applied AI Music System combining rule-based recommendation, RAG-powered Q&A, and simulated real-time trending.

---

## 2. Intended Use

This system is designed for classroom exploration in AI110. It demonstrates how multiple AI techniques — scoring heuristics, retrieval-augmented generation, and real-time data integration — can be combined into a single, cohesive system.

**It is not intended for production use.** The catalog is small, trending data is simulated, and the retrieval logic is keyword-based rather than semantic.

Three usage modes:
- **Standard Recommendation** — suggest songs based on a user taste profile
- **RAG Q&A** — answer natural-language questions grounded in the song dataset
- **Trending Overview** — surface trending genres and boost recommendation scores accordingly

---

## 3. How the System Works

### Original Scoring Engine (Phase 1)

Each song receives a numeric score by comparing its features (genre, mood, energy, valence, danceability) against the user's preferences. Genre and mood matches are worth the most; energy, valence, and danceability contribute proportionally based on how close the values are to the user's targets. Songs are ranked by total score and the top K are returned.

### RAG Pipeline (Phase 2 — DocuBot Integration)

When a user asks a question, the system:
1. Converts every song into a plain-text description
2. Scores each description by counting how many query words appear in it (keyword overlap)
3. Retrieves the top 3 matching song descriptions as "evidence"
4. Sends that evidence to Gemini 1.5 Flash with a strict prompt: "Answer using ONLY the provided data"
5. Returns the grounded answer alongside confidence warnings

This prevents the LLM from hallucinating songs or genres that are not in the catalog.

### Trending Tool (Phase 2 — Real-Time Feature)

A simulated API call returns the top 3 trending genres with associated moods and hot scores. Any song in the standard scoring output whose genre is currently trending receives a +0.5 score bonus. This re-ranks results to favor what is culturally relevant right now, not just what matches the user's stated preferences.

### Confidence Scorer

Three conditions trigger a warning:
- The user's query contains fewer than 2 meaningful tokens, or consists only of vague words ("music", "vibes", "idk")
- No songs were retrieved for the query (zero keyword overlap)
- The trending API call returned no data (e.g., simulated failure)

Warnings are surfaced to the user at the time of output with a `low`, `medium`, or `high` confidence label.

---

## 4. Data

| Source | Songs | Genres Covered |
|--------|-------|----------------|
| `data/songs.csv` | 10 | pop, lofi, rock, ambient, jazz, synthwave, indie pop |
| `data/additional_songs.csv` | 8 | folk, hip hop, classical, reggae, metal, country, house, r&b |
| **Total** | **18** | **15 genres** |

Moods represented: happy, chill, intense, relaxed, moody, focused, nostalgic, confident, peaceful, uplifting, rebellious, heartfelt, euphoric, romantic.

The data was manually curated and does not reflect real streaming statistics. Whose taste it represents is unclear — there is a noticeable bias toward Western genres and English-language music categories.

---

## 5. Strengths

- **Grounded Q&A:** Because RAG retrieves evidence first, the LLM cannot fabricate songs or statistics not present in the dataset. If nothing is retrieved, it says so explicitly.
- **Transparent scoring:** Every recommendation includes a breakdown of exactly which features contributed to the score and by how much.
- **Graceful degradation:** All three modes produce useful output even when Gemini is unavailable (no API key) or when trending data is missing. Warnings tell the user what is missing.
- **Modular design:** Each component (recommender, rag, trends) is independent and can be tested, replaced, or extended without touching the others.

---

## 6. Limitations and Bias

- **Exact label matching:** "calm" and "chill" are treated as entirely different moods. A user asking for a calm vibe will miss songs labeled "chill" even if they are the best fit.
- **No semantic understanding:** Retrieval scores keyword overlap only. "upbeat workout songs" will not find songs tagged "intense" unless those exact words appear in the description text.
- **Simulated trends:** No real API is connected. The trending pool is static and shuffled randomly, not derived from actual streaming data.
- **Small catalog:** 18 songs is too small for meaningful diversity. The system will frequently surface the same songs across multiple profiles.
- **Single preference per field:** A user cannot express "I like both pop and lofi" — only one genre or mood is supported per recommendation request.
- **Western genre bias:** The catalog does not include K-pop, Afrobeats, Bollywood, or other global genres, which limits the system's usefulness for a diverse user base.

---

## 7. Evaluation

Tested across four user profiles and two adversarial inputs:

| Test | Expected | Observed |
|------|----------|----------|
| Morning Jogger (high energy, hip hop, confident) | Hip hop songs near top | Skyline Bounce scored highest with genre + energy match |
| Night Coder (lofi, chill, low energy) | Lofi/chill songs near top | Midnight Coding, Library Rain, Focus Flow in top 3 |
| Vague RAG query: "music" | Confidence warning triggered | "low" confidence flagged, refusal returned |
| RAG query: "What are chill lofi songs?" | 2-3 lofi songs retrieved | Midnight Coding, Library Rain, Focus Flow retrieved correctly |
| Trending failure simulation | Warning shown in Mode 3 | "Trending data unavailable" warning shown; scoring unchanged |
| The Contradiction (pop, happy, high energy, low danceability) | Conflicting prefs degrade score | No single perfect match; pop songs surface but with lower overall scores |

---

## 8. RAG vs. Naive Generation vs. Retrieval Only

Following the DocuBot framework:

| Mode | Behavior |
|------|----------|
| Naive Generation | LLM answers freely — may confidently describe songs not in the dataset |
| Retrieval Only | Returns raw song text snippets — accurate but hard to interpret without a summary |
| RAG (this system) | Retrieves relevant songs, then generates a concise grounded answer — balances accuracy and readability |

**Where RAG still fails:** If the query uses terminology that does not appear in any song's description (e.g., "melancholic introspection"), retrieval returns nothing and the system correctly refuses. Semantic retrieval (e.g., embeddings) would fix this but adds complexity beyond the current scope.

---

## 9. Future Work

- Replace keyword retrieval with sentence embedding similarity (e.g., using `sentence-transformers`) for semantic matching
- Connect to a real trending API (Spotify Charts, Last.fm, or Billboard)
- Add multi-genre and multi-mood preference support
- Expand the catalog to 100+ songs across global genres
- Build a Streamlit UI for the three modes
- Add user history tracking so recommendations improve over repeated interactions

---

## 10. Personal Reflection

Building this system taught me that real AI products are not a single model — they are pipelines. The scoring engine, the retrieval layer, the LLM, and the confidence scorer each do something the others cannot. Removing any one of them degrades the output in a specific, predictable way.

The most surprising insight came from the confidence scorer. It feels like a minor addition, but it fundamentally changes what the system promises to the user. Without it, the LLM will confidently answer any question. With it, the system admits uncertainty — and that honesty is actually more useful than a fluent but wrong answer.

The exact-match limitation in retrieval also clarified why semantic search matters in production. "Calm" and "chill" carry the same emotional meaning but the system treats them as unrelated, which would frustrate real users. That gap between human meaning and label matching is one of the core unsolved problems in information retrieval.
