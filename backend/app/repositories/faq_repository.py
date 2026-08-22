import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.db.tables import FAQDocument, FAQSyncJob

class FAQRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document(self, title: str, content: str, source: str, category: str = "general") -> FAQDocument:
        """Saves a document chunk to the faq database."""
        doc = FAQDocument(
            title=title,
            content=content,
            source=source,
            category=category,
            active=True
        )
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def deactivate_all_source_documents(self, source_name: str) -> None:
        """Deactivates documents from a source (for full refresh/overwrite cycles)."""
        stmt = (
            update(FAQDocument)
            .where(FAQDocument.source == source_name)
            .values(active=False, updated_at=datetime.utcnow())
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_active_documents(self) -> List[FAQDocument]:
        """Retrieves all active FAQ documents."""
        stmt = select(FAQDocument).where(FAQDocument.active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_sync_job(self, source_file: str) -> FAQSyncJob:
        """Logs the start of a knowledge base ingest sync job."""
        job = FAQSyncJob(
            status="running",
            source_file=source_file,
            records_processed=0
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def update_sync_job(self, job_id: uuid.UUID, status: str, processed_count: int, error_message: Optional[str] = None) -> None:
        """Updates status and completion stats of a synchronization job."""
        stmt = (
            update(FAQSyncJob)
            .where(FAQSyncJob.id == job_id)
            .values(
                status=status,
                records_processed=processed_count,
                error_message=error_message,
                finished_at=datetime.utcnow()
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
