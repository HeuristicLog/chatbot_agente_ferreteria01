"""
Seed script for Auto Dealer Ecuador Catalog (2026).
Populates top-selling vehicles in Ecuador with complete specifications, prices, financing, and safety features.
"""
import asyncio
import logging
from decimal import Decimal
from sqlalchemy.future import select
from app.db.session import async_session
from app.db.tables import Vehicle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_vehicles")

VEHICLES_DATA = [
    {
        "code": "AUT-CHEV-DMAX-2026",
        "brand": "Chevrolet",
        "model": "D-Max High Country 3.0L Diésel 4x4",
        "year": 2026,
        "body_type": "Camioneta (Pickup)",
        "engine": "3.0L Diésel Turbo 190 HP / 450 Nm",
        "fuel_type": "Diésel",
        "transmission": "Automática 6 Vel con modo secuencial",
        "traction": "4x4 con Reductora y bloqueo diferencial posterior",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 1050,
        "price_usd": Decimal("34990.00"),
        "min_down_payment": Decimal("6998.00"),
        "estimated_monthly_fee": Decimal("585.00"),
        "description": "La camioneta #1 y más vendida en todo el Ecuador. Máxima potencia para trabajo pesado en costa, sierra y oriente con el confort de un auto de lujo.",
        "safety_features": ["6 Airbags (frontales, laterales y de cortina)", "Frenos ABS + EBD + ESC", "Asistente de arranque en pendiente (HSA) y descenso (HDC)", "Control de balanceo de remolque"],
        "equipment": ["Pantalla táctil 9'' inalámbrica con Apple CarPlay y Android Auto", "Climatizador automático bizona", "Asientos de cuero con ajuste eléctrico", "Cámara de reversa con guías dinámicas", "Estribos y barra de lujo originales"],
        "colors_available": ["Blanco Cumbre", "Plata Switchblade", "Negro Óbice", "Gris Mercurio", "Rojo Vulcano"],
        "image_url": "https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=900&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 6,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-CHEV-TRACKER-2026",
        "brand": "Chevrolet",
        "model": "Tracker RS 1.2L Turbo Automática",
        "year": 2026,
        "body_type": "SUV",
        "engine": "1.2L Turbo 132 HP / 190 Nm de torque",
        "fuel_type": "Gasolina",
        "transmission": "Automática 6 Velocidades",
        "traction": "4x2 FWD",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 393,
        "price_usd": Decimal("22990.00"),
        "min_down_payment": Decimal("4598.00"),
        "estimated_monthly_fee": Decimal("385.00"),
        "description": "SUV compacto deportivo con motor Turbo de alto rendimiento y bajo consumo (hasta 55 km por galón). Calificación 5 estrellas en seguridad Latin NCAP.",
        "safety_features": ["6 Airbags en todas las versiones", "Alerta de colisión frontal con frenado autónomo de emergencia", "Control de estabilidad y tracción StabiliTrak", "Sensor de punto ciego"],
        "equipment": ["Techo solar panorámico corredizo", "Rines deportivos de 17'' color negro brillante RS", "Cargador inalámbrico para smartphone", "Sistema OnStar con Wi-Fi nativo para 7 dispositivos", "Encendido por botón Keyless"],
        "colors_available": ["Rojo Carmín", "Blanco Niebla", "Negro Metálico", "Gris Ceniza"],
        "image_url": "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=900&auto=format&fit=crop&q=80",
            "https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 8,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-KIA-SPORTAGE-2026",
        "brand": "Kia",
        "model": "Sportage LX 2.0L Automático",
        "year": 2026,
        "body_type": "SUV",
        "engine": "2.0L MPI DOHC 16V 156 HP",
        "fuel_type": "Gasolina",
        "transmission": "Automática Secuencial 6 Velocidades",
        "traction": "4x2",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 543,
        "price_usd": Decimal("26490.00"),
        "min_down_payment": Decimal("5298.00"),
        "estimated_monthly_fee": Decimal("445.00"),
        "description": "El SUV familiar preferido del Ecuador. Diseño vanguardista, amplitud interior inigualable y la mejor garantía del mercado nacional (10 años o 160.000 km).",
        "safety_features": ["6 Airbags", "Frenos de disco a las 4 ruedas con ABS + EBD", "Control electrónico de estabilidad (ESC)", "Asistente de arranque en pendientes (HAC)"],
        "equipment": ["Pantalla táctil panorámica curva de 12.3''", "Cámara de visión posterior con guías de parqueo", "Modos de manejo seleccionables (Eco, Normal, Sport)", "Rines de aleación de aluminio 18''", "Faros LED con luces diurnas DRL"],
        "colors_available": ["Blanco Perla", "Gris Gravedad", "Negro Fusión", "Azul Océano"],
        "image_url": "https://images.unsplash.com/photo-1563720223185-11003d516935?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1563720223185-11003d516935?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 5,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-KIA-SONET-2026",
        "brand": "Kia",
        "model": "Sonet LX 1.5L Manual",
        "year": 2026,
        "body_type": "SUV",
        "engine": "1.5L Smartstream DOHC 115 HP",
        "fuel_type": "Gasolina",
        "transmission": "Manual 6 Velocidades",
        "traction": "4x2 FWD",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 392,
        "price_usd": Decimal("19990.00"),
        "min_down_payment": Decimal("3998.00"),
        "estimated_monthly_fee": Decimal("335.00"),
        "description": "El SUV de entrada más completo y económico de mantener. Gran despeje al piso de 20.5 cm para los baches de las ciudades ecuatorianas y excelente rendimiento de combustible.",
        "safety_features": ["6 Airbags", "Frenos ABS con asistente de frenado BAS", "Control de estabilidad ESC", "Sensores de parqueo posteriores"],
        "equipment": ["Pantalla táctil 8'' con Apple CarPlay y Android Auto inalámbrico", "Difusor de aire acondicionado para la segunda fila", "Barras de techo integradas para equipaje", "Rines de aluminio 16''"],
        "colors_available": ["Rojo Intenso", "Blanco Polar", "Plata Claro", "Gris Acero"],
        "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 10,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-TOY-HILUX-2026",
        "brand": "Toyota",
        "model": "Hilux Doble Cabina 2.4L Diésel 4x4",
        "year": 2026,
        "body_type": "Camioneta (Pickup)",
        "engine": "2.4L Turbo Diésel Intercooler 148 HP / 400 Nm",
        "fuel_type": "Diésel",
        "transmission": "Manual 6 Velocidades",
        "traction": "4x4 desconectable con reductora electrónica",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 1000,
        "price_usd": Decimal("38490.00"),
        "min_down_payment": Decimal("7698.00"),
        "estimated_monthly_fee": Decimal("645.00"),
        "description": "La leyenda indestructible. Valor de reventa insuperable en Ecuador, capacidad de carga de 1 tonelada y tracción total 4x4 para haciendas, minería, camaroneras y construcción.",
        "safety_features": ["7 Airbags (incluye airbag de rodilla para conductor)", "Chasis de alta rigidez GOA", "Control de tracción activo A-TRC", "Control de estabilidad VSC"],
        "equipment": ["Pantalla táctil 8'' con conectividad móvil", "Aire acondicionado de enfriamiento rápido", "Protección anticorrosiva de fábrica", "Ganchos de amarre reforzados en balde"],
        "colors_available": ["Blanco Sólido", "Plata Metálico", "Gris Oscuro", "Negro Mica"],
        "image_url": "https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 4,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-TOY-YARISCROSS-2026",
        "brand": "Toyota",
        "model": "Yaris Cross HEV 1.5L Híbrido Auto-recargable",
        "year": 2026,
        "body_type": "SUV",
        "engine": "1.5L Híbrido 116 HP (Gasolina + Motor Eléctrico)",
        "fuel_type": "Híbrido",
        "transmission": "Automática e-CVT",
        "traction": "4x2 FWD",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 390,
        "price_usd": Decimal("27990.00"),
        "min_down_payment": Decimal("5598.00"),
        "estimated_monthly_fee": Decimal("470.00"),
        "description": "SUV Híbrido auto-recargable sin necesidad de enchufes. Exento de Pico y Placa en Quito, hasta 75 km por galón y mínimo costo de mantenimiento.",
        "safety_features": ["Toyota Safety Sense (Sistema de precolisión, alerta de salida de carril)", "6 Airbags", "Control crucero adaptativo", "Frenos de disco en las 4 ruedas con ABS"],
        "equipment": ["Clúster de instrumentos digital 7''", "Pantalla multimedia de 10'' con conectividad inalámbrica", "Modo de conducción 100% eléctrico EV Mode", "Encendido Smart Key"],
        "colors_available": ["Blanco Perlado", "Plata Metal", "Azul Noche", "Gris Titanio"],
        "image_url": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 7,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-HYU-TUCSON-2026",
        "brand": "Hyundai",
        "model": "Tucson NX4 Advance 2.0L Automático",
        "year": 2026,
        "body_type": "SUV",
        "engine": "2.0L Smartstream MPI 154 HP",
        "fuel_type": "Gasolina",
        "transmission": "Automática 6 Velocidades",
        "traction": "4x2",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 582,
        "price_usd": Decimal("29990.00"),
        "min_down_payment": Decimal("5998.00"),
        "estimated_monthly_fee": Decimal("505.00"),
        "description": "Diseño futurista con luces paramétricas ocultas y un maletero gigante de 582 litros. Ideal para viajes familiares por todo el país.",
        "safety_features": ["6 Airbags", "Control electrónico de estabilidad ESC", "Asistente de arranque en pendiente HAC", "Sensor de presión de neumáticos TPMS individual"],
        "equipment": ["Luces delanteras ocultas LED integradas en parrilla", "Pantalla de infoentretenimiento de 8'' con CarPlay inalámbrico", "Rines de aleación aerodinámicos de 18''", "Salidas de aire multi-aire difuso sin corrientes directas"],
        "colors_available": ["Blanco Atlas", "Negro Phantom", "Gris Amazon", "Rojo Atardecer"],
        "image_url": "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 5,
        "is_featured": False,
        "is_active": True
    },
    {
        "code": "AUT-CHERY-TIGGO4-2026",
        "brand": "Chery",
        "model": "Tiggo 4 Pro Luxury 1.5L Turbo Automático",
        "year": 2026,
        "body_type": "SUV",
        "engine": "1.5L Turbo 147 HP / 210 Nm",
        "fuel_type": "Gasolina",
        "transmission": "Automática CVT 9 velocidades simuladas",
        "traction": "4x2 FWD",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 340,
        "price_usd": Decimal("18490.00"),
        "min_down_payment": Decimal("3698.00"),
        "estimated_monthly_fee": Decimal("310.00"),
        "description": "La mejor relación precio-equipamiento del mercado automotriz en Ecuador. Motor Turbo potente, cámara 360 grados y techo corredizo por menos de $18,500.",
        "safety_features": ["6 Airbags", "Cámara de visión periférica 360° en alta definición", "Asistente de frenado de emergencia BAS", "Control de tracción TCS"],
        "equipment": ["Techo corredizo eléctrico sunroof", "Pantalla ultra panorámica de 10.25''", "Asientos forrados en eco-cuero de alta calidad", "Cargador inalámbrico para celular"],
        "colors_available": ["Rojo Fuego", "Blanco Nieve", "Gris Cuarzo", "Negro Noche"],
        "image_url": "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 12,
        "is_featured": True,
        "is_active": True
    },
    {
        "code": "AUT-GWM-POER-2026",
        "brand": "Great Wall",
        "model": "Poer Luxury Doble Cabina 2.0L Diésel 4x4",
        "year": 2026,
        "body_type": "Camioneta (Pickup)",
        "engine": "2.0L Turbo Diésel Common Rail 161 HP / 400 Nm",
        "fuel_type": "Diésel",
        "transmission": "Manual 6 Velocidades",
        "traction": "4x4 con reductora y selector electrónico BorgWarner",
        "passenger_capacity": 5,
        "trunk_capacity_liters": 1050,
        "price_usd": Decimal("28990.00"),
        "min_down_payment": Decimal("5798.00"),
        "estimated_monthly_fee": Decimal("485.00"),
        "description": "La camioneta china de mayor crecimiento en ventas en Ecuador. Acabados premium, balde amplio con recubrimiento de fábrica y suspensión reforzada para carga pesada.",
        "safety_features": ["6 Airbags", "Frenos de disco en las 4 ruedas con ABS+EBD", "Control electrónico antivuelco RMI", "Alerta de tráfico cruzado posterior"],
        "equipment": ["Asientos de cuero con calefacción", "Cámara 360° con vista 3D", "Botón de encendido Start/Stop sin llave", "Rines de lujo de 18'' bitono"],
        "colors_available": ["Negro Titán", "Blanco Glaciar", "Plata Luna", "Rojo Rubí"],
        "image_url": "https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=900&auto=format&fit=crop&q=80",
        "gallery_urls": [
            "https://images.unsplash.com/photo-1559416523-140ddc3d238c?w=900&auto=format&fit=crop&q=80"
        ],
        "stock_units": 6,
        "is_featured": True,
        "is_active": True
    }
]

async def seed_vehicles():
    logger.info("Iniciando semillero de vehículos Ecuador 2026...")
    async with async_session() as session:
        for v_data in VEHICLES_DATA:
            res = await session.execute(select(Vehicle).where(Vehicle.code == v_data["code"]))
            existing = res.scalar_one_or_none()
            if not existing:
                vehicle = Vehicle(**v_data)
                session.add(vehicle)
                logger.info(f"Vehículo insertado: {v_data['brand']} {v_data['model']} (${v_data['price_usd']})")
            else:
                for k, val in v_data.items():
                    setattr(existing, k, val)
                logger.info(f"Vehículo actualizado: {v_data['brand']} {v_data['model']}")
        await session.commit()
    logger.info("Catálogo de vehículos sembrado exitosamente.")

if __name__ == "__main__":
    asyncio.run(seed_vehicles())
