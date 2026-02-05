import os
import requests
import time
from dotenv import load_dotenv
from pinecone import Pinecone
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import TokenTextSplitter

load_dotenv()

# Initialize Models
# Using a specific model for better semantic retrieval
embed_model = SentenceTransformer("sentence-transformers/multi-qa-MiniLM-L6-cos-v1")
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("mini-rag-index")

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for i, page in enumerate(reader.pages):
        content = page.extract_text()
        if content:
            text += f"\n[Page {i+1}]\n{content}\n"
    return text

def process_text(text):
    # Requirement: 800-1200 tokens with 10-15% overlap
    splitter = TokenTextSplitter(chunk_size=1000, chunk_overlap=150)
    return splitter.split_text(text)

def ingest_chunks(chunks, filename):
    vectors = []
    for i, chunk in enumerate(chunks):
        emb = embed_model.encode(chunk).tolist()
        vectors.append({
            "id": f"{filename}-{i}",
            "values": emb,
            "metadata": {"text": chunk, "source": filename}
        })
    index.upsert(vectors=vectors)

def get_answer_with_rerank(query):
    query_emb = embed_model.encode(query).tolist()
    results = index.query(vector=query_emb, top_k=10, include_metadata=True)
    
    if not results["matches"]:
        return "STATUS: NOT FOUND - No relevant data found.", 0

    candidate_chunks = [m["metadata"]["text"] for m in results["matches"]]

    # Jina Reranker (Requirement 3)
    try:
        rerank_url = "https://api.jina.ai/v1/rerank"
        headers = {"Authorization": f"Bearer {os.getenv('JINA_API_KEY')}"}
        data = {
            "model": "jina-reranker-v2-base-multilingual",
            "query": query,
            "documents": candidate_chunks,
            "top_n": 3
        }
        rerank_res = requests.post(rerank_url, headers=headers, json=data, timeout=10).json()
        best_chunks = [candidate_chunks[r["index"]] for r in rerank_res["results"]]
    except:
        best_chunks = candidate_chunks[:3]

    # Explicitly labeling chunks for the LLM to cite
    context_str = ""
    for i, chunk in enumerate(best_chunks):
        context_str += f"--- SOURCE CHUNK [{i+1}] ---\n{chunk}\n\n"

    prompt = f"""You are a helpful AI Assistant. Answer the question using ONLY the context provided.
    
RULES:
1. If the answer is present, start with 'STATUS: VERIFIED'.
2. You MUST use inline citations like [1], [2], or [3] immediately after the sentence they support.
3. If the answer is not in the context, say 'STATUS: NOT FOUND'.

CONTEXT:
{context_str}

QUESTION: {query}"""

    # Groq LLM Generation
    headers = {"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0 # Deterministic for better citation accuracy
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload).json()
        answer = response["choices"][0]["message"]["content"]
        tokens = response.get("usage", {}).get("total_tokens", 0)
        return answer, tokens
    except:
        return "STATUS: ERROR - Connection to LLM failed.", 0

def clear_index():
    index.delete(delete_all=True)