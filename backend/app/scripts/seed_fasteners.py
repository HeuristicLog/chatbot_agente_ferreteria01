import asyncio
from decimal import Decimal
from app.db.session import async_session
from app.db.tables import Product
from sqlalchemy import select

IMG_MAP = {
    'HER-ROT-004': {
        'main': 'https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1572981779307-38b8cabb2407?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'HER-TAL-001': {
        'main': 'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1572981779307-38b8cabb2407?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'HER-AMO-002': {
        'main': 'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'HER-SIE-003': {
        'main': 'https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'MAN-LLV-005': {
        'main': 'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1586864387789-628af9feed72?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'MAN-MAR-006': {
        'main': 'https://images.unsplash.com/photo-1586864387789-628af9feed72?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'CON-CEM-009': {
        'main': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'CON-VAR-010': {
        'main': 'https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&auto=format&fit=crop&q=80'
        ]
    },
    'PIN-VIN-013': {
        'main': 'https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=800&auto=format&fit=crop&q=80',
        'gallery': [
            'https://images.unsplash.com/photo-1562259949-e8e7689d7828?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=800&auto=format&fit=crop&q=80'
        ]
    }
}

FASTENERS = [
    {
        'sku': 'FIJ-TOR-001',
        'name': 'Tornillo Drywall 6x1" Punta Fina (Caja 100u)',
        'category': 'Construcción',
        'description': 'Tornillo fosfatado negro especial para planchas de yeso, gypsum y perfiles metálicos livianos.',
        'price': Decimal('3.50'),
        'stock': 250,
        'sucursal_stocks': {'Centro': 150, 'Norte': 100},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-002',
        'name': 'Tornillo Autoperforante Hexagonal 10x3/4" (Caja 100u)',
        'category': 'Construcción',
        'description': 'Tornillo autoperforante con arandela de neopreno para techos de zinc, policarbonato y estructuras metálicas.',
        'price': Decimal('5.20'),
        'stock': 180,
        'sucursal_stocks': {'Centro': 100, 'Norte': 80},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-003',
        'name': 'Tornillo para Madera Cabeza Plana 8x2" (Caja 100u)',
        'category': 'Construcción',
        'description': 'Tornillo zincado brillante con ranura Phillips para carpintería, muebles y madera tratada.',
        'price': Decimal('4.10'),
        'stock': 120,
        'sucursal_stocks': {'Centro': 70, 'Norte': 50},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-004',
        'name': 'Perno Hexagonal Grado 5 con Tuerca 1/4x2" (Pack 10u)',
        'category': 'Construcción',
        'description': 'Perno de acero de alta resistencia Grado 5 con rosca estándar UNC y tuerca de seguridad.',
        'price': Decimal('2.80'),
        'stock': 95,
        'sucursal_stocks': {'Centro': 60, 'Norte': 35},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-005',
        'name': 'Tornillo Tirafondo Zincado 5/16x3" (Pack 10u)',
        'category': 'Construcción',
        'description': 'Tirafondo cabeza hexagonal para fijación pesada en vigas de madera y tacos plásticos de concreto.',
        'price': Decimal('3.60'),
        'stock': 85,
        'sucursal_stocks': {'Centro': 50, 'Norte': 35},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-006',
        'name': 'Tornillo Gypsum Punta Broca 6x1-1/4" (Caja 100u)',
        'category': 'Construcción',
        'description': 'Punta broca autoperforante especial para fijación sobre perfiles estructurales de acero pesado.',
        'price': Decimal('4.20'),
        'stock': 140,
        'sucursal_stocks': {'Centro': 90, 'Norte': 50},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-007',
        'name': 'Perno Estructural A325 1/2x2-1/2" (Pack 5u)',
        'category': 'Construcción',
        'description': 'Perno estructural ASTM A325 de alta resistencia para puentes, naves industriales y vigas IPE.',
        'price': Decimal('6.50'),
        'stock': 60,
        'sucursal_stocks': {'Centro': 40, 'Norte': 20},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-008',
        'name': 'Remache Pop de Aluminio 5/32x1/2" (Caja 100u)',
        'category': 'Construcción',
        'description': 'Remaches de unión rápida cuerpo de aluminio y mandril de acero para cerrajería y canaletas.',
        'price': Decimal('3.10'),
        'stock': 110,
        'sucursal_stocks': {'Centro': 70, 'Norte': 40},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-009',
        'name': 'Tuerca Hexagonal Galvanizada 3/8" (Pack 25u)',
        'category': 'Construcción',
        'description': 'Tuerca galvanizada en caliente anticorrosiva para montaje electromecánico y plomería.',
        'price': Decimal('2.20'),
        'stock': 200,
        'sucursal_stocks': {'Centro': 120, 'Norte': 80},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    },
    {
        'sku': 'FIJ-TOR-010',
        'name': 'Arandela de Presión y Plana 1/2" (Pack 25u)',
        'category': 'Construcción',
        'description': 'Juego de arandelas Grover de presión y planas para absorción de vibraciones en pernos.',
        'price': Decimal('1.80'),
        'stock': 190,
        'sucursal_stocks': {'Centro': 110, 'Norte': 80},
        'image_url': 'https://images.unsplash.com/photo-1585776245991-cf89dd7fc73a?w=800&auto=format&fit=crop&q=80',
        'gallery_images': [
            'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80'
        ]
    }
]

async def seed():
    async with async_session() as s:
        # Update existing
        res = await s.execute(select(Product))
        for p in res.scalars().all():
            if p.sku in IMG_MAP:
                p.image_url = IMG_MAP[p.sku]['main']
                p.gallery_images = IMG_MAP[p.sku]['gallery']
            elif not p.gallery_images:
                p.gallery_images = [
                    p.image_url or 'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=800&auto=format&fit=crop&q=80',
                    'https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=800&auto=format&fit=crop&q=80'
                ]
        
        # Add fasteners
        for f in FASTENERS:
            chk = await s.execute(select(Product).where(Product.sku == f['sku']))
            existing = chk.scalar_one_or_none()
            if not existing:
                np = Product(**f)
                s.add(np)
                print(f"Added fastener: {f['name']}")
            else:
                existing.gallery_images = f['gallery_images']
                existing.image_url = f['image_url']
                existing.description = f['description']
                existing.price = f['price']
                existing.stock = f['stock']
                existing.sucursal_stocks = f['sucursal_stocks']
        
        await s.commit()
        print('Seed and update successfully completed!')

if __name__ == '__main__':
    asyncio.run(seed())
