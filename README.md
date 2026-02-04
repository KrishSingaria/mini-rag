# Mini RAG Assessment (Track B)

[live link](https://mini-rag-67p9.onrender.com)
>Its on Render free instance so it may be spin down with inactivity, which can delay requests by 50 seconds or more, it does not support concurrent requests, and it may hit rate limits on the LLM API, but it should work for basic testing.

A lightweight, hybrid Retrieval-Augmented Generation (RAG) system built with **FastAPI**, **Pinecone**, and **Google Gemini**.

It features a "Hybrid" chat mode that answers from your uploaded documents (with citations) but gracefully falls back to general knowledge for outside queries.

## Architecture

![Architecture Diagram](Architecture.png)

## Tech Stack & Parameters

* **Backend:** Python FastAPI (Async).
* **Embeddings:** Google `text-embedding-004` (768 dimensions).
* **Chunking:** Recursive Character Split (Size: 1000, Overlap: 100).
* **Vector DB:** Pinecone (Serverless, Cosine Similarity).
* **Reranker:** Cohere `rerank-english-v3.0`.
* **LLM:** Google `gemini-3.0-flash` (with fallback logic).
* **Frontend:** Vanilla JS + Marked.js (for Markdown rendering).

## Quick Start

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd mini-rag
```


2. **Install dependencies:**
```bash
pip install -r requirements.txt
```


3. **Set up environment:**
Create a `.env` file:
```ini
GOOGLE_API_KEY=your_key
PINECONE_API_KEY=your_key
CO_API_KEY=your_key
```


4. **Run the App:**
```bash
uvicorn main:app --reload
```


5. **Run Evaluation:**
```bash
python eval.py
```



## Evaluation Results

The system was tested against a fictional "Project Titan" dataset to verify RAG accuracy versus General Knowledge.

| Question Type | Question | Expected | Actual Result | Status |
| --- | --- | --- | --- | --- |
| **Specific Fact** | Budget for Project Titan? | $5.2 Billion | $5.2 Billion [1] | ✅ PASS |
| **Reasoning** | How to brew without gravity? | Centrifugal force | Centrifugal force... [1] | ✅ PASS |
| **Constraint** | Why no boiling water? | Safety hazard | Safety hazard [1] | ✅ PASS |
| **General Knowledge** | CEO of Tesla? | Elon Musk | Elon Musk | ✅ PASS |

**Remarks:**
To ensure reliability on the Free Tier, the system implements a **Model Fallback Strategy**. If `gemini-3.0-flash` hits a rate limit (429), it automatically retries with `gemini-2.0-flash-lite` to ensure the user always gets an answer.

## Remarks

Assessment submission for Predusk Technology Pvt. Ltd. by Krish Singaria B23143 IIT Mandi.
