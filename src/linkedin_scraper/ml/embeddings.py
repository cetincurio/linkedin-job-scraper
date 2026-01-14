"""Generate embeddings for job data using sentence-transformers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.ml.export import JobDataExporter


if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

    from linkedin_scraper.config import Settings

__all__ = ["EmbeddingGenerator"]

logger = get_logger(__name__)

DEFAULT_MODEL = "all-MiniLM-L6-v2"


class EmbeddingGenerator:
    """Generate embeddings for job descriptions using sentence-transformers."""

    def __init__(
        self,
        settings: Settings,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        self._settings = settings
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._exporter = JobDataExporter(settings)

    def _load_model(self) -> SentenceTransformer:
        """Lazy load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as e:
                msg = "sentence-transformers not installed. Run: uv sync --extra ml"
                raise ImportError(msg) from e

            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def generate_embeddings(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = True,
    ) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        model = self._load_model()
        logger.info("Generating embeddings for %d texts", len(texts))
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return embeddings  # type: ignore[return-value]

    def embed_jobs(self, output_path: Path | str | None = None) -> Path:
        """Generate embeddings for all job descriptions and save to file."""
        df = self._exporter.to_polars()
        if df.is_empty():
            msg = "No job data to embed"
            raise ValueError(msg)

        # Use ml_text column which combines title, company, and description
        texts = df["ml_text"].to_list()
        job_ids = df["job_id"].to_list()

        embeddings = self.generate_embeddings(texts)

        if output_path is None:
            output_path = self._settings.data_dir / "datasets" / "embeddings.npz"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save embeddings with job IDs
        np.savez_compressed(
            output_path,
            embeddings=embeddings,
            job_ids=np.array(job_ids, dtype=object),
            model_name=self._model_name,
        )

        logger.info(
            "Saved embeddings for %d jobs to %s (shape: %s)",
            len(job_ids),
            output_path,
            embeddings.shape,
        )
        return output_path

    def load_embeddings(
        self,
        embeddings_path: Path | str | None = None,
    ) -> tuple[np.ndarray, list[str]]:
        """Load embeddings from file."""
        if embeddings_path is None:
            embeddings_path = self._settings.data_dir / "datasets" / "embeddings.npz"

        embeddings_path = Path(embeddings_path)
        if not embeddings_path.exists():
            msg = f"Embeddings file not found: {embeddings_path}"
            raise FileNotFoundError(msg)

        data = np.load(embeddings_path, allow_pickle=True)
        embeddings = data["embeddings"]
        job_ids = data["job_ids"].tolist()

        logger.info("Loaded embeddings: %s", embeddings.shape)
        return embeddings, job_ids

    def find_similar(
        self,
        query: str,
        top_k: int = 5,
        embeddings_path: Path | str | None = None,
    ) -> list[tuple[str, float]]:
        """Find jobs similar to a query string."""
        embeddings, job_ids = self.load_embeddings(embeddings_path)
        model = self._load_model()

        # Encode query
        query_embedding = model.encode([query], convert_to_numpy=True)

        # Compute cosine similarity
        from sentence_transformers import util

        similarities = util.cos_sim(query_embedding, embeddings)[0]
        top_indices = similarities.argsort(descending=True)[:top_k]

        results = []
        for idx in top_indices:
            job_id = job_ids[idx]
            score = float(similarities[idx])
            results.append((job_id, score))

        return results

    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension of the model."""
        model = self._load_model()
        return model.get_sentence_embedding_dimension()  # type: ignore[return-value]
