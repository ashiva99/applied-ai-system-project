// Applied AI Music System — Architecture Diagram (Mermaid flowchart)
// Paste the string below into https://mermaid.live to render it.

const diagram = `
flowchart TD
    A([User Input\\nQuery / Mood / Preferences]) --> B{Mode Selector\\nsrc/main.py}

    B -->|Mode 1| C[Standard Recommendation\\nsrc/recommender.py]
    B -->|Mode 2| D[RAG Q&A\\nsrc/rag.py]
    B -->|Mode 3| E[Trending Overview\\nsrc/trends.py]

    subgraph DATA [Data Layer]
        CSV1[(songs.csv\\n10 songs)]
        CSV2[(additional_songs.csv\\n8 songs)]
        CSV3[(trends.csv\\n100 Apple Music tracks)]
    end

    subgraph FETCH [Internet Fetch — Mode 3 only]
        APPLE[Apple Music RSS\\nrss.applemarketingtools.com\\nNo API key required]
        APPLE -->|urllib, 100 tracks| NORM[_normalize_track\\nGenre map + feature defaults\\nPopularity from chart rank]
        NORM -->|save_trends_csv| CSV3
    end

    subgraph MODE1 [Mode 1 — Standard Recommendation]
        CSV1 & CSV2 -->|load_songs| SCORE[score_song\\ngenre + mood + energy\\nvalence + danceability]
        CSV3 -->|load_trends_csv + fetch_trending| BOOST[apply_trending_boost\\n+0.5 bonus per trending genre]
        BOOST --> SCORE
        SCORE --> RANK[Ranked Top-5\\nwith score breakdown]
    end

    subgraph MODE2 [Mode 2 — RAG Q&A]
        CSV1 & CSV2 & CSV3 -->|build_rag_index\\n118 docs total| IDX[Text Index\\nKeyword token sets]
        IDX -->|retrieve: keyword overlap| RET{Any matches?}
        RET -->|Yes — top 3| CTX[Retrieved Song Context]
        RET -->|No match — fallback| CTX
        CTX --> LLM[Gemini 2.0 Flash\\ngoogle-genai SDK\\nGrounded answer only]
    end

    subgraph MODE3 [Mode 3 — Trending Overview]
        CSV3 -->|get_top_genres| GENRES[Top 5 Genres\\nweighted by popularity]
        CSV3 -->|recommend_from_trends| TOP5[Top 5 Tracks\\nby chart rank]
        CSV3 -->|fetch_trending| TDATA[Trending Data Dict]
        TDATA --> BOOST
    end

    subgraph GUARD [Confidence Scorer — all modes]
        LLM --> CHK{confidence_check}
        RANK --> CHK
        CHK -->|Vague query / no data / no matches| WARN[Warning + confidence label\\nlow / medium / high]
        CHK -->|Sufficient context| OUT[Final Output]
        WARN --> OUT
    end

    C --> MODE1
    D --> MODE2
    E --> MODE3
    E -.->|optional fetch| FETCH

    style A fill:#4f86c6,color:#fff,stroke:#2c5f8a
    style B fill:#6b6bcc,color:#fff,stroke:#4444aa
    style APPLE fill:#555,color:#fff,stroke:#333
    style LLM fill:#e8a838,color:#fff,stroke:#b07a1a
    style WARN fill:#d9534f,color:#fff,stroke:#a02020
    style OUT fill:#2ecc71,color:#fff,stroke:#1a9950
    style CSV3 fill:#ffd580,color:#000,stroke:#c8a000
    style NORM fill:#ffd580,color:#000,stroke:#c8a000
`;

export default diagram;
