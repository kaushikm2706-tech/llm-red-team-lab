import os
import chromadb
from chromadb.utils import embedding_functions

# Folder where Chroma will save its database files
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "company_docs"


def chunk_text(text, chunk_size=300, overlap=50):
    """Splits a long piece of text into smaller overlapping chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def build_vector_store():
    """Reads all .txt documents, chunks them, and stores them in Chroma."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete old collection if it exists, so we always rebuild fresh
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    embedding_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.create_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)

    folder = "documents"
    chunk_id = 0

    for filename in os.listdir(folder):
        if filename.endswith(".txt"):
            filepath = os.path.join(folder, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            chunks = chunk_text(content)
            for chunk in chunks:
                collection.add(
                    documents=[chunk],
                    metadatas=[{"source": filename}],
                    ids=[f"chunk_{chunk_id}"]
                )
                chunk_id += 1

    print(f"Vector store built with {chunk_id} chunks.")
    return collection


def get_relevant_chunks(query, n_results=3):
    """Given a question, returns the most relevant document chunks.
    Automatically builds the vector store first if it doesn't exist yet -
    this makes the app self-healing on a fresh deployment where
    chroma_db/ hasn't been created yet (e.g. Streamlit Cloud)."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = embedding_functions.DefaultEmbeddingFunction()

    try:
        collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embedding_fn)
    except Exception:
        print("Vector store not found - building it now...")
        collection = build_vector_store()

    results = collection.query(query_texts=[query], n_results=n_results)
    chunks = results["documents"][0]
    sources = [meta["source"] for meta in results["metadatas"][0]]

    combined = ""
    for chunk, source in zip(chunks, sources):
        combined += f"\n--- From {source} ---\n{chunk}\n"
    return combined


if __name__ == "__main__":
    build_vector_store()
    # Quick test
    test_result = get_relevant_chunks("What is the admin password?")
    print("\n--- Test retrieval for 'What is the admin password?' ---")
    print(test_result)