"""Local sentence-transformers embedding provider."""

from app.services.embedding.exceptions import EmbeddingProviderError

CANONICAL_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SHORT_MODEL_NAME = "all-MiniLM-L6-v2"


class SentenceTransformersProvider:
    def __init__(self, model: str = CANONICAL_MODEL_NAME) -> None:
        self._load_model_name = self._resolve_load_model_name(model)
        self._model = None
        self._dimensions: int | None = None

    @property
    def model_name(self) -> str:
        if self._load_model_name == SHORT_MODEL_NAME:
            return CANONICAL_MODEL_NAME
        return self._load_model_name

    @property
    def dimensions(self) -> int:
        model = self._get_model()
        if self._dimensions is None:
            if hasattr(model, "get_embedding_dimension"):
                self._dimensions = int(model.get_embedding_dimension())
            else:
                self._dimensions = int(model.get_sentence_embedding_dimension())
        return self._dimensions

    def embed_text(self, text: str) -> list[float]:
        vectors = self.embed_texts([text])
        return vectors[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            encoded = self._get_model().encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as error:
            raise EmbeddingProviderError(
                "Sentence-transformers failed while generating embeddings."
            ) from error

        if len(encoded) != len(texts):
            raise EmbeddingProviderError(
                "Sentence-transformers returned a different number of vectors "
                "than input texts."
            )

        return [vector.tolist() for vector in encoded]

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise EmbeddingProviderError(
                    "sentence-transformers is not installed."
                ) from error

            try:
                self._model = SentenceTransformer(self._load_model_name)
            except Exception as error:
                raise EmbeddingProviderError(
                    "Failed to load sentence-transformers model."
                ) from error

        return self._model

    @staticmethod
    def _resolve_load_model_name(model: str) -> str:
        if model == CANONICAL_MODEL_NAME:
            return SHORT_MODEL_NAME
        return model
