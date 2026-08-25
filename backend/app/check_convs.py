import asyncio
from app.db.session import async_session
from app.db.tables import Conversation
from sqlalchemy import select

async def main():
    async with async_session() as session:
        stmt = select(Conversation).order_by(Conversation.last_activity_at.desc()).limit(10)
        res = await session.execute(stmt)
        convs = res.scalars().all()
        print(f"Encontradas {len(convs)} conversaciones:")
        for c in convs:
            print(f"ID: {c.id}, Phone Hash: {c.phone_hash}, Status: {c.status}, Last Activity: {c.last_activity_at}")

if __name__ == '__main__':
    asyncio.run(main())
