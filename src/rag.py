"""
RAG (Retrieval-Augmented Generation) pipeline for the Applied AI Music System.
Uses songs.csv as the knowledge base and Gemini as the generation backend.
"""

import os
import re
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

# Moods/terms too vague to retrieve meaningful results
VAGUE_TERMS = {"ok", "fine", "something", "any", "whatever", "idk", "music", "songs", "vibes", "stuff"}
MIN_QUERY_TOKENS = 2


def _song_to_text(song: Dict) -> str:
    base = (
        f"Song: {song['title']} by {song['artist']}. "
        f"Genre: {song['genre']}. Mood: {song['mood']}. "
        f"Energy: {song['energy']}. Tempo: {song['tempo_bpm']} BPM. "
        f"Valence: {song['valence']}. Danceability: {song['danceability']}. "
        f"Acousticness: {song['acousticness']}."
    )
    # Trend-sourced songs carry chart metadata — include it so retrieval can
    # match queries like "trending songs" or "top chart songs".
    if "chart_rank" in song:
        base += (
            f" Trending. Chart rank: #{song['chart_rank']}."
            f" Popularity: {song['popularity']}."
        )
    return base


def build_rag_index(songs: List[Dict]) -> List[Dict]:
    """Convert songs list into searchable text documents with token sets."""
    docs = []
    for song in songs:
        text = _song_to_text(song)
        tokens = set(re.findall(r'\w+', text.lower()))
        docs.append({"song": song, "text": text, "tokens": tokens})
    return docs


def retrieve(query: str, docs: List[Dict], top_k: int = 3) -> List[Dict]:
    """Return top-k most relevant song docs based on query keyword overlap."""
    query_tokens = set(re.findall(r'\w+', query.lower()))
    scored = [(len(query_tokens & doc["tokens"]), doc) for doc in docs]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for score, doc in scored[:top_k] if score > 0]


def confidence_check(
    query: str,
    retrieved_docs: List[Dict],
    trending_data: Optional[Dict],
) -> Tuple[str, List[str]]:
    """
    Assess confidence in the RAG result and flag any issues.
    Returns (level, warnings) where level is 'high', 'medium', or 'low'.
    """
    warnings = []
    tokens = re.findall(r'\w+', query.lower())

    if len(tokens) < MIN_QUERY_TOKENS or set(tokens).issubset(VAGUE_TERMS):
        warnings.append(
            "Query is too vague — try including a genre, mood, artist, or song name."
        )

    if not retrieved_docs:
        warnings.append("No keyword matches found — using full catalog as context (lower precision).")

    if trending_data is None or not trending_data.get("trending_genres"):
        warnings.append("Trending data unavailable — scoring based on local dataset only.")

    if not warnings:
        return "high", []
    elif len(warnings) == 1:
        return "medium", warnings
    return "low", warnings


def ask_rag(
    query: str,
    docs: List[Dict],
    trending_data: Optional[Dict] = None,
) -> Dict:
    """
    Full RAG pipeline: retrieve relevant songs → check confidence → generate LLM answer.

    Returns:
        answer           — natural language response
        retrieved_songs  — list of song dicts used as context
        confidence_level — 'high', 'medium', or 'low'
        warnings         — list of flagged issues
    """
    keyword_matches = retrieve(query, docs, top_k=3)

    # When no keywords matched, fall back to the full catalog so Gemini can still answer
    # generic questions ("good songs", "which songs are upbeat?") with full context.
    retrieved = keyword_matches if keyword_matches else docs

    # Pass keyword_matches (not the fallback) so confidence_check can flag zero-overlap queries.
    level, warnings = confidence_check(query, keyword_matches, trending_data)
    context = "\n".join(doc["text"] for doc in retrieved)
    answer = _generate_with_gemini(query, context)

    return {
        "answer": answer,
        "retrieved_songs": [doc["song"] for doc in keyword_matches] if keyword_matches else [],
        "confidence_level": level,
        "warnings": warnings,
    }


def _generate_with_gemini(query: str, context: str) -> str:
    """Call Gemini to generate a grounded answer from retrieved context."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return (
            "[LLM disabled — set GEMINI_API_KEY in your .env file to enable generation]\n\n"
            f"Retrieved context:\n{context}"
        )

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = (
            "You are a music dataset assistant. Answer the user's question using ONLY the song "
            "data provided below. If the answer cannot be determined from the data, say exactly: "
            "'I don't know based on the available songs.'\n\n"
            f"Song Data:\n{context}\n\n"
            f"Question: {query}\n\nAnswer:"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as exc:
        return f"[Gemini error: {exc}]\n\nContext used:\n{context}"
