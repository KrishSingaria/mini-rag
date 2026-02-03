import os
import time
import uuid
from fastapi import FastAPI, Body, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import google.generativeai as genai
from pinecone import Pinecone
import cohere
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

# Load environment variables from .env file (for local dev)
load_dotenv()

app = FastAPI()

# 1. Setup Clients
# Check if keys are present to avoid runtime errors
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY is missing")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("rag-app")
co = cohere.Client(os.getenv("CO_API_KEY"))

# 2. Ingestion Logic
class IngestRequest(BaseModel):
    text: str

# ... inside main.py ...

@app.post("/ingest")
async def ingest_text(request: IngestRequest):
    # A. Chunking
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(request.text)
    
    # B. Embedding & Upserting
    vectors = []
    
    print(f"Starting ingestion of {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        # Generate a unique ID
        chunk_id = str(uuid.uuid4())
        
        # --- RATE LIMIT HANDLING ---
        retry_count = 0
        max_retries = 3
        while retry_count < max_retries:
            try:
                embedding = genai.embed_content(
                    model="models/embedding-001",
                    content=chunk,
                    task_type="retrieval_document"
                )['embedding']
                
                vectors.append({
                    "id": chunk_id, 
                    "values": embedding, 
                    "metadata": {"text": chunk, "source": "user-upload"}
                })
                
                # Success! Break the retry loop
                break 
            except Exception as e:
                if "429" in str(e):
                    print(f"Hit rate limit on chunk {i}. Sleeping for 10s...")
                    time.sleep(10) # Wait longer if we hit the limit
                    retry_count += 1
                else:
                    print(f"Error embedding chunk {i}: {e}")
                    break
        
        # --- CRITICAL: SLEEP BETWEEN REQUESTS ---
        # Sleep 2 seconds between every chunk to be nice to the API
        time.sleep(2) 
    
    # C. Upsert to Pinecone
    if vectors:
        # Upsert in batches of 50 to avoid Pinecone size limits
        batch_size = 50
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            index.upsert(vectors=batch)
            
    return {"status": "indexed", "chunks": len(chunks)}

# 3. Retrieval Logic
class QueryRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat(req: QueryRequest):
    start_time = time.time()
    
    try:
        # A. Embed Query
        q_embed = genai.embed_content(
            model="models/embedding-001",
            content=req.question,
            task_type="retrieval_query"
        )['embedding']
        
        # B. Initial Retrieval (Top 10)
        results = index.query(vector=q_embed, top_k=10, include_metadata=True)
        
        # Guard clause: If no matches found in DB
        if not results['matches']:
            return {
                "answer": "I don't have any information on that topic in my database.",
                "citations": [],
                "time_taken": round(time.time() - start_time, 2)
            }

        docs = [match['metadata']['text'] for match in results['matches']]
        
        # C. Rerank (Top 3)
        rerank_results = co.rerank(
            model="rerank-english-v3.0",
            query=req.question,
            documents=docs,
            top_n=3
        )
        
        # Prepare Context
        final_context = ""
        used_docs = []
        for idx, result in enumerate(rerank_results.results):
            final_context += f"Source [{idx+1}]: {result.document['text']}\n\n"
            used_docs.append({"id": idx+1, "text": result.document['text']})

        # D. LLM Answer
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are a helpful assistant. Answer the user's question using ONLY the context below. 
        Cite the sources you used as [1], [2], etc.
        If the answer is not in the context, state that you do not know.
        
        Context:
        {final_context}
        
        Question: {req.question}
        """
        
        response = model.generate_content(prompt)
        
        return {
            "answer": response.text,
            "citations": used_docs,
            "time_taken": round(time.time() - start_time, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve Frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")