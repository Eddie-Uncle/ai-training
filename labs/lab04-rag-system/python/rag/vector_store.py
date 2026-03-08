"""Vector Store implementation using ChromaDB with Voyage AI embeddings."""
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings
from typing import List, Dict, Any, Optional
import os


class VoyageAIEmbeddingFunction(EmbeddingFunction):
    """Voyage AI embedding function for ChromaDB."""

    def __init__(self, api_key: str, model_name: str = "voyage-code-2"):
        import voyageai
        self.voyage = voyageai.Client(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        """Embed documents with document input_type for indexing."""
        result = self.voyage.embed(
            list(input), model=self.model_name, input_type="document"
        )
        return result.embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a query with query input_type for better retrieval accuracy."""
        result = self.voyage.embed(
            [text], model=self.model_name, input_type="query"
        )
        return result.embeddings[0]


class CodebaseVectorStore:
    """Vector store for code embeddings using ChromaDB + Voyage AI."""

    def __init__(
        self,
        collection_name: str = "codebase",
        persist_directory: str = "./chroma_db"
    ):
        self.client = chromadb.PersistentClient(path=persist_directory)

        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY environment variable is required")

        self.embedding_fn = VoyageAIEmbeddingFunction(api_key=api_key)

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Add documents to the vector store."""
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict]:
        """Query the vector store using a semantically correct query embedding."""
        query_embedding = self.embedding_fn.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where
        )

        formatted = []
        for i in range(len(results['documents'][0])):
            formatted.append({
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i],
                'id': results['ids'][0][i]
            })

        return formatted

    def get_stats(self) -> Dict:
        """Get collection statistics."""
        return {
            "count": self.collection.count(),
            "name": self.collection.name
        }

    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
