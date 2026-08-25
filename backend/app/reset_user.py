import asyncio
import hashlib
import redis.asyncio as redis
from app.db.session import async_session
from app.db.tables import Conversation
from sqlalchemy import select

async def main():
    phone = "593987621657"
    phone_hash = hashlib.sha256(phone.encode()).hexdigest()
    
    # 1. Update DB Conversation status to 'bot_active'
    async with async_session() as session:
        stmt = select(Conversation).where(Conversation.phone_hash == phone_hash).order_by(Conversation.last_activity_at.desc())
        res = await session.execute(stmt)
        convs = res.scalars().all()
        if convs:
            for c in convs:
                print(f"Reseteando conversación {c.id} de {c.status} a 'bot_active'")
                c.status = "bot_active"
                session.add(c)
            await session.commit()
            print("Conversaciones actualizadas en la DB.")
        else:
            print("No se encontró conversación en la DB.")

    # 2. Clear Redis flow state
    r = redis.from_url("redis://redis:6379/0")
    await r.delete(f"flow_state:{phone}")
    await r.close()
    print("Redis flow state borrado.")

if __name__ == '__main__':
    asyncio.run(main())
