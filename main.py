import os
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai 
from pinecone import Pinecone, ServerlessSpec
import cohere
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()
model_name = "gemini-3-flash-preview"

app = FastAPI()

# --- 1. SETUP CLIENTS ---
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "rag-app"

# Auto-create Index
existing_indexes = [i.name for i in pc.list_indexes()]
if index_name not in existing_indexes:
    print(f"Creating Pinecone index '{index_name}'...")
    pc.create_index(
        name=index_name,
        dimension=768, 
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)

index = pc.Index(index_name)
co = cohere.Client(os.getenv("CO_API_KEY"))

# --- 2. RESET ENDPOINT (NEW) ---
@app.post("/reset")
async def reset_db():
    try:
        # Wipes everything in the index
        index.delete(delete_all=True)
        print(" -> DB Reset/Cleared.")
        return {"status": "cleared"}
    except Exception as e:
        print(f"Reset Error: {e}")
        return {"status": "error", "detail": str(e)}

# --- 3. INGESTION ---
class IngestRequest(BaseModel):
    text: str

@app.post("/ingest")
async def ingest_text(request: IngestRequest):
    print(f"--- Processing {len(request.text)} chars ---")
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(request.text)
    
    vectors = []
    
    for i, chunk in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        
        # Retry logic for embeddings
        for attempt in range(3):
            try:
                response = client.models.embed_content(
                    model="text-embedding-004",
                    contents=chunk
                )
                if response and response.embeddings:
                    embedding_values = response.embeddings[0].values
                    vectors.append({
                        "id": chunk_id, 
                        "values": embedding_values, 
                        "metadata": {"text": chunk}
                    })
                    break 
            except Exception as e:
                print(f"Error on chunk {i+1}: {e}")
                time.sleep(2)
        
        time.sleep(1) # Rate limit safety

    if vectors:
        index.upsert(vectors=vectors)
    
    return {"status": "indexed", "chunks": len(chunks)}


# --- 4. CHAT (Updated Model) ---
class QueryRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(req: QueryRequest):
    start_time = time.time()
    
    try:
        # A. Embed Query
        q_resp = client.models.embed_content(
            model="text-embedding-004",
            contents=req.question
        )
        q_embed = q_resp.embeddings[0].values
        
        # B. Retrieve relevant documents from Pinecone
        results = index.query(vector=q_embed, top_k=10, include_metadata=True)
        docs = [
            match['metadata']['text']
            for match in results.get('matches', [])
            if match.get('metadata', {}).get('text')
        ]
        
        # C. Rerank documents if any were found
        final_context = ""
        used_docs = []
        
        if docs:
            rerank_results = co.rerank(
                model="rerank-english-v3.0",
                query=req.question,
                documents=docs,
                top_n=3
            )
            
            for idx, result in enumerate(rerank_results.results):
                relevant_text = docs[result.index]
                final_context += f"Source [{idx+1}]: {relevant_text}\n\n"
                used_docs.append({"id": idx+1, "text": relevant_text})
        else:
            final_context = "No specific documents found."
        
        # D. Generate answer with context
        prompt = f"""You are a helpful assistant.
        INSTRUCTIONS:
        1. Check the 'Context' below.
        2. If the Context contains the answer, use it and cite like [1].
        3. If Context is empty or irrelevant, use your own knowledge.
        4. Answer naturally without mentioning missing context.

        Context:
        {final_context}

        Question: {req.question}"""
        
        answer_text = await _generate_answer(prompt)
        
        return {
            "answer": answer_text,
            "citations": used_docs,
            "time_taken": round(time.time() - start_time, 2)
        }

    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_answer(prompt: str) -> str:
    """Generate answer using primary model, fallback to backup if needed."""
    try:
        gen_resp = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return gen_resp.text
    
    except Exception as e:
        if "429" in str(e) or "Quota" in str(e):
            print("⚠️ Primary model rate limited. Switching to backup...")
            gen_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return gen_resp.text
        
        raise

app.mount("/", StaticFiles(directory="static", html=True), name="static")