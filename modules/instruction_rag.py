"""
Instruction RAG Engine using ChromaDB.
Stores uploaded instructions in a persistent vector database
and retrieves relevant guidelines for drafting answers.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from modules.config import VECTOR_DB_DIR

class InstructionRAGEngine:
    def __init__(self, collection_name: str = "assignment_instructions"):
        self.collection_name = collection_name
        self.db_dir = str(VECTOR_DB_DIR)
        self.client = None
        self.collection = None
        self._init_db()

    def _init_db(self):
        """Initializes ChromaDB client."""
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.db_dir)
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
        except Exception as e:
            print(f"Error initializing Instruction RAG ChromaDB: {e}")

    def reset(self):
        """Resets the instructions collection for a new session."""
        if self.client:
            try:
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.get_or_create_collection(name=self.collection_name)
            except Exception as e:
                print(f"Error resetting instruction collection: {e}")

    def chunk_instructions(self, text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        """Splits instruction text into semantic chunks."""
        chunks = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        current_chunk = []
        current_len = 0

        for line in lines:
            current_chunk.append(line)
            current_len += len(line)
            if current_len >= chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = current_chunk[-1:] # slight overlap
                current_len = len(current_chunk[0])

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def add_instructions(self, text: str, source_name: str = "instructions.pdf"):
        """Indexes instructions into vector store."""
        if not self.collection or not text.strip():
            return

        chunks = self.chunk_instructions(text)
        if not chunks:
            return

        ids = [f"inst_{source_name}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": source_name, "chunk": i} for i in range(len(chunks))]

        self.collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )

    def get_instructions_context(self, question_text: str = "", n_results: int = 4) -> str:
        """
        Retrieves the most relevant instruction chunks for a question.
        If few total chunks exist, returns all of them.
        """
        if not self.collection:
            return ""

        try:
            count = self.collection.count()
            if count == 0:
                return ""

            if count <= 4:
                # Return all indexed instruction chunks
                all_docs = self.collection.get()
                return "\n\n".join(all_docs.get("documents", []))

            # Query semantically based on question context (e.g. marks, word count, formatting)
            query_prompt = f"guidelines word count formatting marks {question_text[:100]}"
            results = self.collection.query(query_texts=[query_prompt], n_results=min(n_results, count))
            docs = results.get("documents", [[]])[0]
            return "\n\n".join(docs)
        except Exception as e:
            print(f"Error querying instruction RAG: {e}")
            return ""
