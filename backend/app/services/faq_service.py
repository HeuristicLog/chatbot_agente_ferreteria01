import logging
import httpx
from typing import List, Optional
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.repositories.faq_repository import FAQRepository
from app.domain.models import FAQSearchResult

logger = logging.getLogger("chatbot-api.services.faq")

class FAQService:
    def __init__(self, db: AsyncSession, qdrant_client: Optional[AsyncQdrantClient] = None):
        self.repo = FAQRepository(db)
        self.db = db
        self.qdrant = qdrant_client

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Calls OpenAI's API directly to generate text embeddings."""
        if not settings.EMBEDDING_API_KEY:
            logger.debug("EMBEDDING_API_KEY is not set. Skipping vector generation.")
            return None
            
        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "input": text,
                "model": settings.EMBEDDING_MODEL
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code == 200:
                    return response.json()["data"][0]["embedding"]
                logger.error(f"OpenAI Embeddings error: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Exception generating embedding: {str(e)}")
        return None

    async def search_faq(self, query: str, limit: int = 5) -> List[FAQSearchResult]:
        """Performs a semantic search on Qdrant, falling back to a database keyword match if offline."""
        logger.info(f"Searching FAQ for query: '{query}'")
        
        # 1. Attempt Semantic Search if Qdrant and key are ready
        if self.qdrant and settings.EMBEDDING_API_KEY:
            vector = await self._get_embedding(query)
            if vector:
                try:
                    logger.info("Executing vector search in Qdrant.")
                    search_result = await self.qdrant.search(
                        collection_name=settings.QDRANT_COLLECTION,
                        query_vector=vector,
                        limit=limit
                    )
                    
                    results = []
                    for hit in search_result:
                        payload = hit.payload or {}
                        results.append(
                            FAQSearchResult(
                                text=payload.get("content", ""),
                                source=payload.get("source", "unknown"),
                                category=payload.get("category", "general"),
                                score=hit.score
                            )
                        )
                    if results:
                        return results
                except Exception as e:
                    logger.warning(f"Qdrant vector search failed, falling back to DB: {str(e)}")

        # 2. Fallback: Keyword search in PostgreSQL
        logger.info("Executing database keyword-matching fallback.")
        words = [w.strip() for w in query.split() if len(w.strip()) > 2]
        
        # Build matching conditions
        from app.db.tables import FAQDocument
        stmt = select(FAQDocument).where(FAQDocument.active == True)
        
        result = await self.db.execute(stmt)
        docs = result.scalars().all()
        
        scored_docs = []
        for doc in docs:
            score = 0.0
            content_lower = doc.content.lower()
            title_lower = doc.title.lower()
            
            # Simple keyword scoring
            for word in words:
                word_lower = word.lower()
                if word_lower in title_lower:
                    score += 2.0
                if word_lower in content_lower:
                    score += 1.0
                    
            if score > 0:
                scored_docs.append((doc, score))
                
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Map to FAQSearchResult
        results = []
        for doc, score in scored_docs[:limit]:
            results.append(
                FAQSearchResult(
                    text=doc.content,
                    source=doc.source or "manual",
                    category=doc.category or "general",
                    score=min(1.0, score / 5.0)  # Normalize score
                )
            )
        return results

    async def upsert_document_vector(self, doc) -> bool:
        """Generates embedding for a document and upserts it in Qdrant in real-time."""
        if not self.qdrant or not settings.EMBEDDING_API_KEY:
            logger.warning("Qdrant or EMBEDDING_API_KEY not configured. Skipping vector sync.")
            return False
            
        vector = await self._get_embedding(doc.content)
        if not vector:
            logger.warning(f"Failed to generate embedding for document: {doc.id}")
            return False
            
        try:
            logger.info(f"Upserting document point {doc.id} to Qdrant collection {settings.QDRANT_COLLECTION}")
            await self.qdrant.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                points=[
                    qmodels.PointStruct(
                        id=str(doc.id),
                        vector=vector,
                        payload={
                            "content": doc.content,
                            "title": doc.title,
                            "source": doc.source or "manual",
                            "category": doc.category or "general"
                        }
                    )
                ]
            )
            return True
        except Exception as e:
            logger.error(f"Error upserting vector to Qdrant: {str(e)}")
            return False

    async def delete_document_vector(self, doc_id) -> bool:
        """Deletes a document vector from Qdrant in real-time."""
        if not self.qdrant:
            logger.warning("Qdrant client not configured. Skipping vector deletion.")
            return False
            
        try:
            logger.info(f"Deleting document point {doc_id} from Qdrant collection {settings.QDRANT_COLLECTION}")
            await self.qdrant.delete(
                collection_name=settings.QDRANT_COLLECTION,
                points_selector=qmodels.PointIdsList(
                    points=[str(doc_id)]
                )
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting vector from Qdrant: {str(e)}")
            return False
