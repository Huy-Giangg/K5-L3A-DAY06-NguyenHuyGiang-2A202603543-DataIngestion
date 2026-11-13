"""Local embedding implementation using Sentence Transformers."""
from sentence_transformers import SentenceTransformer


class LocalEmbedder:
    """Real local embedding provider adapter using sentence-transformers/all-MiniLM-L6-v2."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one normalized embedding vector per input text."""
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embeddings.tolist()

    def embed_query(self, question: str) -> list[float]:
        """Return normalized query vector compatible with document vectors."""
        embedding = self.model.encode(
            question,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        return embedding.tolist()
