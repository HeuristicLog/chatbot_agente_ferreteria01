import asyncio
import logging
from sqlalchemy import select
from app.db.session import async_session, engine
from app.db.base import Base
from app.db.tables import Product

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_catalog")

SAMPLE_PRODUCTS = [
    # Herramientas Eléctricas
    {
        "sku": "HER-TAL-001",
        "name": "Taladro Percutor Inalámbrico DeWalt 20V Max",
        "category": "Herramientas Eléctricas",
        "description": "Taladro percutor de 20V con 2 baterías de litio, cargador rápido y maletín. Mandril de 1/2 pulgada y 2 velocidades mecánicas.",
        "price": 135.00,
        "stock": 24,
        "sucursal_stocks": {"Centro": 10, "Norte": 8, "Sur": 4, "Cumbayá": 2},
        "image_url": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "HER-AMO-002",
        "name": "Amoladora Angular Bosch 4-1/2\" 850W",
        "category": "Herramientas Eléctricas",
        "description": "Esmeriladora angular profesional de 850W con guarda de protección y empuñadura auxiliar antivibración. 11,000 RPM.",
        "price": 78.50,
        "stock": 30,
        "sucursal_stocks": {"Centro": 12, "Norte": 10, "Sur": 5, "Cumbayá": 3},
        "image_url": "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "HER-SIE-003",
        "name": "Sierra Circular Skil 7-1/4\" 1400W",
        "category": "Herramientas Eléctricas",
        "description": "Sierra circular con disco de 24 dientes de carburo de tungsteno. Guía paralela y capacidad de corte en ángulo hasta 45°.",
        "price": 115.00,
        "stock": 15,
        "sucursal_stocks": {"Centro": 6, "Norte": 5, "Sur": 2, "Cumbayá": 2},
        "image_url": "https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "HER-ROT-004",
        "name": "Rotomartillo SDS Plus Makita 800W",
        "category": "Herramientas Eléctricas",
        "description": "Rotomartillo demoledor y perforador con 3 modos de operación (rotación, percusión y cincelado). Incluye maletín de transporte.",
        "price": 189.00,
        "stock": 10,
        "sucursal_stocks": {"Centro": 4, "Norte": 4, "Sur": 1, "Cumbayá": 1},
        "image_url": "https://images.unsplash.com/photo-1508873696983-2df5293cb395?w=600&auto=format&fit=crop&q=80"
    },

    # Herramientas Manuales
    {
        "sku": "MAN-LLV-005",
        "name": "Juego de Llaves Combinadas Stanley 12 Pzas",
        "category": "Herramientas Manuales",
        "description": "Set de llaves milimétricas de 8mm a 19mm fabricadas en acero cromo-vanadio con acabado satinado anticorrosión.",
        "price": 34.50,
        "stock": 40,
        "sucursal_stocks": {"Centro": 15, "Norte": 15, "Sur": 5, "Cumbayá": 5},
        "image_url": "https://images.unsplash.com/photo-1586864387967-d02ef85d93e8?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "MAN-MAR-006",
        "name": "Martillo de Uña Curva 16oz Mango Fibra Truper",
        "category": "Herramientas Manuales",
        "description": "Martillo forjado en una sola pieza con cabeza de acero alto carbono y mango ergonómico de fibra de vidrio anti-impacto.",
        "price": 12.50,
        "stock": 55,
        "sucursal_stocks": {"Centro": 25, "Norte": 15, "Sur": 10, "Cumbayá": 5},
        "image_url": "https://images.unsplash.com/photo-1586864387789-628af9feed72?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "MAN-FLX-007",
        "name": "Flexómetro / Cinta Métrica 8m Lufkin Pro",
        "category": "Herramientas Manuales",
        "description": "Cinta métrica de alta resistencia con cinta recubierta en nylon para máxima durabilidad y freno antideslizante.",
        "price": 9.80,
        "stock": 80,
        "sucursal_stocks": {"Centro": 30, "Norte": 25, "Sur": 15, "Cumbayá": 10},
        "image_url": "https://images.unsplash.com/photo-1588854337236-6889d631faa8?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "MAN-DES-008",
        "name": "Juego de Destornilladores Pro 6 Pzas Tramontina",
        "category": "Herramientas Manuales",
        "description": "3 destornilladores planos y 3 de estrella con puntas magnetizadas y mangos anatómicos de alta adherencia.",
        "price": 14.20,
        "stock": 50,
        "sucursal_stocks": {"Centro": 20, "Norte": 15, "Sur": 10, "Cumbayá": 5},
        "image_url": "https://images.unsplash.com/photo-1580983218765-f663bec07b37?w=600&auto=format&fit=crop&q=80"
    },

    # Construcción y Materiales
    {
        "sku": "CON-CEM-009",
        "name": "Cemento Selvalegre Tipo Portland 50kg",
        "category": "Construcción",
        "description": "Cemento hidráulico de uso general para hormigones, morteros, enlucidos y elementos estructurales. Alta resistencia.",
        "price": 8.75,
        "stock": 300,
        "sucursal_stocks": {"Centro": 100, "Norte": 100, "Sur": 60, "Cumbayá": 40},
        "image_url": "https://images.unsplash.com/photo-1590069261209-f8e9b8642343?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "CON-VAR-010",
        "name": "Varilla de Hierro Corrugado 12mm x 12m Adelca",
        "category": "Construcción",
        "description": "Acero de refuerzo sismorresistente con resaltes de alta adherencia para estructuras de hormigón armado.",
        "price": 11.20,
        "stock": 150,
        "sucursal_stocks": {"Centro": 50, "Norte": 50, "Sur": 30, "Cumbayá": 20},
        "image_url": "https://images.unsplash.com/photo-1535813547-99c456a41d4a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "CON-PAL-011",
        "name": "Pala Cuadrada con Mango Madera Truper",
        "category": "Construcción",
        "description": "Pala de cabeza de acero templado y cabo de madera de fresno americano con puño en Y metálico.",
        "price": 16.50,
        "stock": 35,
        "sucursal_stocks": {"Centro": 15, "Norte": 10, "Sur": 5, "Cumbayá": 5},
        "image_url": "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "CON-CAR-012",
        "name": "Carretilla de Construcción Tolva 90L Reforzada",
        "category": "Construcción",
        "description": "Tolva de chapa reforzada con rueda neumática y soportes tubulares de alta capacidad hasta 150kg.",
        "price": 62.00,
        "stock": 20,
        "sucursal_stocks": {"Centro": 8, "Norte": 6, "Sur": 4, "Cumbayá": 2},
        "image_url": "https://images.unsplash.com/photo-1590496793929-36417d3117de?w=600&auto=format&fit=crop&q=80"
    },

    # Pinturas y Acabados
    {
        "sku": "PIN-VIN-013",
        "name": "Pintura Látex Vinilac Blanco Caneca 5 Galones",
        "category": "Pinturas",
        "description": "Pintura lavable para interiores y exteriores de alto poder cubriente y acabado mate uniforme antihongos.",
        "price": 48.00,
        "stock": 45,
        "sucursal_stocks": {"Centro": 18, "Norte": 15, "Sur": 8, "Cumbayá": 4},
        "image_url": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "PIN-ESM-014",
        "name": "Esmalte Sintético Anticorrosivo 1 Galón Pinturas Unidas",
        "category": "Pinturas",
        "description": "Esmalte brillante protector contra óxido y humedad para metales, rejas, puertas y madera.",
        "price": 19.50,
        "stock": 30,
        "sucursal_stocks": {"Centro": 12, "Norte": 10, "Sur": 5, "Cumbayá": 3},
        "image_url": "https://images.unsplash.com/photo-1562259949-e8e7689d7828?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "PIN-ROD-015",
        "name": "Rodillo Profesional con Felpa y Bandeja 9\"",
        "category": "Pinturas",
        "description": "Kit aplicador completo con maneral metálico de acero galvanizado, felpa antigoteo y bandeja plástica.",
        "price": 6.80,
        "stock": 60,
        "sucursal_stocks": {"Centro": 25, "Norte": 20, "Sur": 10, "Cumbayá": 5},
        "image_url": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=600&auto=format&fit=crop&q=80"
    },

    # Fontanería y Plomería
    {
        "sku": "PLO-TUB-016",
        "name": "Tubo PVC Presión 1/2\" x 6m Plastigama",
        "category": "Plomería",
        "description": "Tubería para conducción de agua potable a presión con extremo liso y campana para soldar.",
        "price": 4.50,
        "stock": 120,
        "sucursal_stocks": {"Centro": 40, "Norte": 40, "Sur": 25, "Cumbayá": 15},
        "image_url": "https://images.unsplash.com/photo-1542013936693-884638332954?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "PLO-GRI-017",
        "name": "Grifería Monomando para Lavabo FV Cromo",
        "category": "Plomería",
        "description": "Grifería ecológica con cartucho cerámico y aireador espumante para ahorro de agua. Acabado cromo brillante.",
        "price": 54.00,
        "stock": 18,
        "sucursal_stocks": {"Centro": 7, "Norte": 6, "Sur": 3, "Cumbayá": 2},
        "image_url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "PLO-BOM-018",
        "name": "Bomba de Agua Periférica 1/2 HP Pedrollo",
        "category": "Plomería",
        "description": "Electrobomba periférica compacta y silenciosa para elevación y presurización de agua en viviendas.",
        "price": 79.90,
        "stock": 12,
        "sucursal_stocks": {"Centro": 5, "Norte": 4, "Sur": 2, "Cumbayá": 1},
        "image_url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?w=600&auto=format&fit=crop&q=80"
    },

    # Electricidad e Iluminación
    {
        "sku": "ELE-CAB-019",
        "name": "Cable Mellizo 2x14 AWG Rollo 100m Indeco",
        "category": "Electricidad",
        "description": "Conductor de cobre electrolítico de alta pureza con aislamiento en PVC flexible para instalaciones interiores.",
        "price": 42.00,
        "stock": 25,
        "sucursal_stocks": {"Centro": 10, "Norte": 8, "Sur": 4, "Cumbayá": 3},
        "image_url": "https://images.unsplash.com/photo-1558346490-a72e53ae2d4f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "ELE-FOC-020",
        "name": "Foco LED Bulbo 9W Luz Blanca Pack x4 Philips",
        "category": "Electricidad",
        "description": "Ahorro del 85% de energía con vida útil de 15,000 horas. Rosca E27 estándar.",
        "price": 7.50,
        "stock": 90,
        "sucursal_stocks": {"Centro": 35, "Norte": 30, "Sur": 15, "Cumbayá": 10},
        "image_url": "https://images.unsplash.com/photo-1550985543-f47f38aee65e?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "ELE-TOM-021",
        "name": "Tomacorriente Doble con Tierra Bticino Blanco",
        "category": "Electricidad",
        "description": "Mecanismo doble polarizado 15A / 125V con placa plástica resistente a rayos UV.",
        "price": 3.80,
        "stock": 110,
        "sucursal_stocks": {"Centro": 45, "Norte": 35, "Sur": 20, "Cumbayá": 10},
        "image_url": "https://images.unsplash.com/photo-1558346490-a72e53ae2d4f?w=600&auto=format&fit=crop&q=80"
    },
    {
        "sku": "ELE-MUL-022",
        "name": "Multímetro Digital Profesional Truper",
        "category": "Electricidad",
        "description": "Tester digital para medición de voltaje AC/DC, corriente, resistencia, continuidad y diodos con pantalla retroiluminada.",
        "price": 22.50,
        "stock": 22,
        "sucursal_stocks": {"Centro": 8, "Norte": 8, "Sur": 4, "Cumbayá": 2},
        "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80"
    }
]

async def seed_products():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for p_data in SAMPLE_PRODUCTS:
            stmt = select(Product).where(Product.sku == p_data["sku"])
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                prod = Product(
                    sku=p_data["sku"],
                    name=p_data["name"],
                    category=p_data["category"],
                    description=p_data["description"],
                    price=p_data["price"],
                    stock=p_data["stock"],
                    sucursal_stocks=p_data["sucursal_stocks"],
                    image_url=p_data["image_url"],
                    is_active=True
                )
                session.add(prod)
                logger.info(f"Producto creado: {p_data['name']} ({p_data['sku']})")
            else:
                existing.name = p_data["name"]
                existing.category = p_data["category"]
                existing.description = p_data["description"]
                existing.price = p_data["price"]
                existing.stock = p_data["stock"]
                existing.sucursal_stocks = p_data["sucursal_stocks"]
                existing.image_url = p_data["image_url"]
                session.add(existing)
                logger.info(f"Producto actualizado: {p_data['name']}")
        await session.commit()
        logger.info("Catálogo de productos sembrado exitosamente.")

if __name__ == "__main__":
    asyncio.run(seed_products())
