import os
import uuid
import asyncio
import logging
import httpx
from datetime import datetime
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.db.base import Base
from app.db.tables import FAQDocument, FAQSyncJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest-faq")

# Directory of FAQ files
FAQ_DIR = "./data/faq"

async def generate_embedding(text: str) -> list:
    """Queries OpenAI embeddings API to represent text chunk as a vector."""
    if not settings.EMBEDDING_API_KEY:
        logger.warning("EMBEDDING_API_KEY no configurado. Saltando vectorización.")
        return []
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
            resp = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if resp.status_code == 200:
                return resp.json()["data"][0]["embedding"]
            else:
                logger.error(f"Error generando embedding: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.error(f"Excepción en embedding: {str(e)}")
    return []

async def ingest():
    logger.info("Starting FAQ Ingestion Job...")
    
    # 1. Setup DB connection
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    # 2. Setup Qdrant connection
    qdrant_active = False
    qclient = None
    if settings.EMBEDDING_API_KEY:
        try:
            qclient = AsyncQdrantClient(url=settings.QDRANT_URL)
            logger.info("Verifying Qdrant collection...")
            # Create collection if it doesn't exist
            collections = await qclient.get_collections()
            exist = any(c.name == settings.QDRANT_COLLECTION for c in collections.collections)
            if not exist:
                logger.info(f"Creating collection '{settings.QDRANT_COLLECTION}' in Qdrant")
                await qclient.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=qmodels.VectorParams(
                        size=1536, # text-embedding-3-small dimension
                        distance=qmodels.Distance.COSINE
                    )
                )
            qdrant_active = True
        except Exception as e:
            logger.warning(f"No fue posible conectar con Qdrant: {str(e)}. La ingesta continuará solo en PostgreSQL.")

    # 3. Read documents
    if not os.path.exists(FAQ_DIR):
        logger.error(f"FAQ directory '{FAQ_DIR}' not found.")
        return
        
    files = [f for f in os.listdir(FAQ_DIR) if f.endswith(".md") or f.endswith(".txt")]
    logger.info(f"Found {len(files)} documents to ingest.")
    
    async with async_session() as session:
        for file_name in files:
            file_path = os.path.join(FAQ_DIR, file_name)
            logger.info(f"Ingesting file: {file_name}")
            
            # Start sync job
            job = FAQSyncJob(status="running", source_file=file_name)
            session.add(job)
            await session.commit()
            await session.refresh(job)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Split content into simple chunks based on markdown headers or paragraph size
                # For simplicity, split by double newline
                chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 30]
                
                # Deactivate old database documents from this source to avoid duplicates
                await session.execute(
                    text("UPDATE faq_documents SET active = false WHERE source = :src"),
                    {"src": file_name}
                )
                await session.commit()
                
                records_processed = 0
                for idx, chunk in enumerate(chunks):
                    # Save document chunk in PostgreSQL
                    doc = FAQDocument(
                        title=f"{file_name} - Chunk {idx}",
                        category=file_name.split(".")[0],
                        source=file_name,
                        content=chunk,
                        active=True
                    )
                    session.add(doc)
                    await session.commit()
                    await session.refresh(doc)
                    
                    # Generate and save vector in Qdrant
                    if qdrant_active and qclient:
                        vector = await generate_embedding(chunk)
                        if vector:
                            await qclient.upsert(
                                collection_name=settings.QDRANT_COLLECTION,
                                points=[
                                    qmodels.PointStruct(
                                        id=str(doc.id), # Map DB UUID to vector ID
                                        vector=vector,
                                        payload={
                                            "title": doc.title,
                                            "content": doc.content,
                                            "source": doc.source,
                                            "category": doc.category
                                        }
                                    )
                                ]
                            )
                    records_processed += 1
                
                # Complete job status
                job.status = "completed"
                job.records_processed = records_processed
                job.finished_at = datetime.utcnow()
                session.add(job)
                await session.commit()
                logger.info(f"File {file_name} synced. Chunks processed: {records_processed}")
                
            except Exception as e:
                logger.exception(f"Error ingesting file {file_name}:")
                job.status = "failed"
                job.error_message = str(e)
                job.finished_at = datetime.utcnow()
                session.add(job)
                await session.commit()
                
    if qclient:
        await qclient.close()
    await engine.dispose()
    logger.info("FAQ Ingestion Job completed.")

if __name__ == "__main__":
    from sqlalchemy import text
    asyncio.run(ingest())
