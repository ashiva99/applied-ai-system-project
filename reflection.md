Github Link: https://github.com/ashiva99/applied-ai-system-project 
Loom video: https://www.loom.com/share/e408c79ffa7a4e1eb4e446c8ff9f3835


What are the blind spots in your system? Does your music recommender favor certain genres over others because of the dataset?

Yes. The catalog only has 18 songs and most of them are pop, lofi, or rock. Genres like K-pop, Afrobeats, or Bollywood are completely missing. Also, mood labels have to match exactly. "Calm" and "chill" are treated as different things, so users who describe the same vibe with different words get worse results. The Apple Music trending data is also US-only, not global.


How could someone use this AI in a way it was not intended for, and what steps would you take to stop that?

Someone could ask statistical questions like "which artist has the most chart presence" and get a confident answer based on only 18 songs. The confidence warnings are there but easy to ignore. A stronger guardrail would block questions that need comparisons across the full catalog. Also, the trending fetch has no rate limit, so someone could run it in a loop to scrape chart data, which would violate Apple's terms. A simple one-fetch-per-hour check would prevent that.


What was the most unexpected thing you noticed while testing the system's accuracy or guardrails?

Queries like "good songs" returned nothing because the word "good" does not appear anywhere in the song descriptions. The system just refused to answer, even though the question made total sense. Adding a full-catalog fallback fixed it. That taught me that retrieval quality depends more on how the knowledge base is written than on how smart the model is.


You must describe your experience working with AI to build the project. Identify one instance where the AI gave a helpful suggestion, and one where its suggestion was flawed or incorrect.

Helpful: when the retriever returned zero matches, the AI suggested passing the full catalog to Gemini anyway and flagging it as lower-confidence. That kept the system useful without pretending it found a strong match.

Flawed: the AI told me to use the google.generativeai package with gemini-1.5-flash. When I ran it, I got a 404 error because that package was already deprecated and the model was no longer on the v1beta API. I had to switch to the google-genai SDK and gemini-2.0-flash to get it working.




This project showed me that I care more about building something that works in the real world than something that looks good on paper. I did not start with a perfect plan. I started with a small catalog, hit real bugs, and fixed them one by one. When the retriever failed on a simple question like "good songs," I did not ignore it. I tracked down the cause and added a fallback. That feels like the right instinct for an AI engineer: stay curious when something breaks, and do not ship a confident wrong answer.