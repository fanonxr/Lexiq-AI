"""
Minimal Qdrant client for terminate-account: delete points and delete collection.

Used by TerminateAccountService to remove RAG vectors when a user (or orphan firm)
is deleted. If QDRANT_URL is not set or empty, operations are no-ops.
"""

from __future__ import annotations

import logging
from typing import List

from api_core.config import get_settings

logger = logging.getLogger(__name__)


def delete_points(collection_name: str, point_ids: List[str]) -> None:
    """
    Delete points from a Qdrant collection by ID.

    No-op if Qdrant is not configured. Logs and swallows errors so terminate
    can proceed (DB/user deletion is primary; Qdrant cleanup is best-effort).

    Args:
        collection_name: Qdrant collection name (e.g. firm_<uuid>).
        point_ids: List of point IDs (UUID strings) to delete.
    """
    settings = get_settings()
    if not (settings.qdrant.is_configured and point_ids):
        return
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointIdsList

        client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=settings.qdrant.timeout,
        )
        client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=point_ids),
            wait=True,
        )
        logger.info(
            f"Deleted {len(point_ids)} points from Qdrant collection {collection_name}"
        )
    except Exception as e:
        logger.warning(
            f"Qdrant delete_points failed (collection={collection_name}, "
            f"count={len(point_ids)}): {e}. Continuing with terminate."
        )


def list_collections() -> List[str]:
    """
    List all Qdrant collection names.

    No-op if Qdrant is not configured; returns [].
    """
    settings = get_settings()
    if not settings.qdrant.is_configured:
        return []
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=settings.qdrant.timeout,
        )
        collections = client.get_collections().collections
        return [c.name for c in collections]
    except Exception as e:
        logger.warning(f"Qdrant list_collections failed: {e}. Continuing.")
        return []


def delete_collection(collection_name: str) -> None:
    """
    Delete a Qdrant collection.

    No-op if Qdrant is not configured. Logs and swallows errors so terminate
    can proceed.

    Args:
        collection_name: Qdrant collection name (e.g. firm_<uuid>).
    """
    settings = get_settings()
    if not (settings.qdrant.is_configured and collection_name):
        return
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            timeout=settings.qdrant.timeout,
        )
        client.delete_collection(collection_name=collection_name)
        logger.info(f"Deleted Qdrant collection: {collection_name}")
    except Exception as e:
        logger.warning(
            f"Qdrant delete_collection failed (collection={collection_name}): {e}. "
            "Continuing with terminate."
        )
