"""Vector store for job similarity search using ChromaDB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from linkedin_scraper.logging_config import get_logger
from linkedin_scraper.ml.embeddings import DEFAULT_MODEL, EmbeddingGenerator
from linkedin_scraper.ml.export import JobDataExporter


if TYPE_CHECKING:
    import chromadb

    from linkedin_scraper.config import Settings

__all__ = ["JobVectorStore"]

logger = get_logger(__name__)

COLLECTION_NAME = "linkedin_jobs"


class JobVectorStore:
    """Vector store for semantic job search using ChromaDB."""

    def __init__(
        self,
        settings: Settings,
        persist_path: Path | str | None = None,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        self._settings = settings
        self._model_name = model_name
        self._exporter = JobDataExporter(settings)
        self._embedding_gen = EmbeddingGenerator(settings, model_name)

        if persist_path is None:
            persist_path = settings.data_dir / "vectorstore"
        self._persist_path = Path(persist_path)

        self._client: chromadb.ClientAPI | None = None
        self._collection: chromadb.Collection | None = None

    def _get_client(self) -> chromadb.ClientAPI:
        """Get or create ChromaDB client."""
        if self._client is None:
            try:
                import chromadb
            except ImportError as e:
                msg = "chromadb not installed. Run: uv sync --extra ml"
                raise ImportError(msg) from e

            self._persist_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self._persist_path))
            logger.info("ChromaDB client initialized at %s", self._persist_path)
        return self._client

    def _get_collection(self) -> chromadb.Collection:
        """Get or create the jobs collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def index_jobs(self, batch_size: int = 100) -> int:
        """Index all job data into the vector store."""
        df = self._exporter.to_polars()
        if df.is_empty():
            logger.warning("No job data to index")
            return 0

        collection = self._get_collection()

        # Get existing IDs to avoid duplicates
        existing_ids = set(collection.get()["ids"])

        # Prepare data
        job_ids = df["job_id"].to_list()
        texts = df["ml_text"].to_list()

        # Filter out already indexed jobs
        new_indices = [i for i, jid in enumerate(job_ids) if jid not in existing_ids]
        if not new_indices:
            logger.info("All jobs already indexed")
            return 0

        new_job_ids = [job_ids[i] for i in new_indices]
        new_texts = [texts[i] for i in new_indices]

        # Prepare metadata
        metadata_cols = ["title", "company_name", "location", "skills"]
        metadatas = []
        for i in new_indices:
            meta = {}
            for col in metadata_cols:
                val = df[col][i]
                if val:
                    meta[col] = str(val)[:500]  # Limit metadata size
            metadatas.append(meta)

        # Index in batches
        indexed = 0
        for start in range(0, len(new_job_ids), batch_size):
            end = min(start + batch_size, len(new_job_ids))
            batch_ids = new_job_ids[start:end]
            batch_texts = new_texts[start:end]
            batch_meta = metadatas[start:end]

            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_meta,
            )
            indexed += len(batch_ids)
            logger.info("Indexed %d/%d jobs", indexed, len(new_job_ids))

        return indexed

    def search(
        self,
        query: str,
        n_results: int = 10,
        filter_dict: dict | None = None,
    ) -> list[dict]:
        """Search for similar jobs."""
        collection = self._get_collection()

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where=filter_dict,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        jobs = []
        if results["ids"] and results["ids"][0]:
            for i, job_id in enumerate(results["ids"][0]):
                job = {
                    "job_id": job_id,
                    "score": 1 - (results["distances"][0][i] if results["distances"] else 0),
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                }
                jobs.append(job)

        return jobs

    def get_similar_jobs(self, job_id: str, n_results: int = 5) -> list[dict]:
        """Find jobs similar to a given job."""
        collection = self._get_collection()

        # Get the job document
        result = collection.get(ids=[job_id], include=["documents"])
        if not result["documents"]:
            msg = f"Job not found: {job_id}"
            raise ValueError(msg)

        job_text = result["documents"][0]
        return self.search(job_text, n_results=n_results + 1)[1:]  # Exclude self

    def delete_all(self) -> None:
        """Delete all indexed data."""
        client = self._get_client()
        try:
            client.delete_collection(COLLECTION_NAME)
            self._collection = None
            logger.info("Deleted collection: %s", COLLECTION_NAME)
        except ValueError:
            logger.info("Collection does not exist")

    def get_stats(self) -> dict:
        """Get vector store statistics."""
        collection = self._get_collection()
        return {
            "collection_name": COLLECTION_NAME,
            "total_documents": collection.count(),
            "persist_path": str(self._persist_path),
        }

    def export_for_training(self, output_path: Path | str | None = None) -> Path:
        """Export indexed data for fine-tuning or training."""
        collection = self._get_collection()
        all_data = collection.get(include=["documents", "metadatas"])

        if output_path is None:
            output_path = self._settings.data_dir / "datasets" / "training_data.jsonl"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            for i, job_id in enumerate(all_data["ids"]):
                record = {
                    "id": job_id,
                    "text": all_data["documents"][i] if all_data["documents"] else "",
                    "metadata": all_data["metadatas"][i] if all_data["metadatas"] else {},
                }
                f.write(json.dumps(record) + "\n")

        logger.info("Exported %d records to %s", len(all_data["ids"]), output_path)
        return output_path
