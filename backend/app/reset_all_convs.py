import asyncio
import redis.asyncio as redis
from app.db.session import async_session
from app.db.tables import Conversation
from sqlalchemy import select

async def main():
    # 1. Update all DB Conversations to 'bot_active'
    async with async_session() as session:
        stmt = select(Conversation)
        res = await session.execute(stmt)
        convs = res.scalars().all()
        for c in convs:
            print(f"Reseteando conversación {c.id} (hash: {c.phone_hash}) de {c.status} a 'bot_active'")
            c.status = "bot_active"
            session.add(c)
        await session.commit()
        print("Todas las conversaciones en la DB reseteadas a 'bot_active'.")

    # 2. Clear Redis
    r = redis.from_url("redis://redis:6379/0")
    keys = await r.keys("flow_state:*")
    if keys:
        await r.delete(*keys)
        print(f"Borrados {len(keys)} flow states de Redis.")
    await r.close()

if __name__ == '__main__':
    asyncio.run(main())
