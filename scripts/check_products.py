import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.session import async_session
from app.db.tables import Product
from sqlalchemy import select

async def main():
    try:
        async with async_session() as s:
            res = await s.execute(select(Product.sku, Product.name, Product.category, Product.price, Product.stock).limit(15))
            rows = res.fetchall()
            print(f"Total productos encontrados: {len(rows)}")
            for r in rows:
                print(r)
    except Exception as e:
        print(f"Error consultando DB: {e}")

if __name__ == "__main__":
    asyncio.run(main())
