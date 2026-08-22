import asyncio
import logging
import sys
import os
import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

# Add current path to python path to run from workspace root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import tables and base
from app.db.base import Base
from app.db.tables import User, FAQCategory, FAQDocument, Seller, SellerSpecialty, SystemSetting
from app.config import settings
from app.security.jwt_auth import hash_password

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed-database")

async def seed():
    logger.info("Connecting to database to run seeding...")
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = async_sessionmaker(bind=engine, expire_on_commit=False)
    
    async with engine.begin() as conn:
        logger.info("Re-creating or verifying tables...")
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        
    async with async_session() as session:
        # Check if already seeded by verifying if users exist
        result = await session.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        if count > 0:
            logger.info("Database already seeded. Skipping.")
            return

        logger.info("Seeding system configuration and users...")
        
        # 1. Create Admins and Supervisors
        admin_user = User(
            username="admin",
            email="admin@ferreteria.com",
            password_hash=hash_password("admin_pass"),
            role="admin",
            is_active=True
        )
        super_admin = User(
            username="superadmin",
            email="superadmin@ferreteria.com",
            password_hash=hash_password("superadmin_pass"),
            role="super_admin",
            is_active=True
        )
        supervisor = User(
            username="supervisor",
            email="supervisor@ferreteria.com",
            password_hash=hash_password("supervisor_pass"),
            role="supervisor",
            is_active=True
        )
        session.add_all([admin_user, super_admin, supervisor])
        await session.commit()
        await session.refresh(admin_user)
        
        # 2. Create 12 Sellers (Vendedores)
        logger.info("Seeding 12 sellers...")
        sellers_data = [
            ("Juan Pérez", "593900000001", "juan@ferreteria.com", "ventas", "Norte"),
            ("María Gómez", "593900000002", "maria@ferreteria.com", "ventas", "Centro"),
            ("Carlos Ruiz", "593900000003", "carlos@ferreteria.com", "devoluciones", "Sur"),
            ("Ana Torres", "593900000004", "ana@ferreteria.com", "reclamos", "Norte"),
            ("Luis Castro", "593900000005", "luis@ferreteria.com", "ventas", "Cumbayá"),
            ("Sofía Ramos", "593900000006", "sofia@ferreteria.com", "ventas", "Sur"),
            ("Diego Díaz", "593900000007", "diego@ferreteria.com", "general", "Centro"),
            ("Elena Vega", "593900000008", "elena@ferreteria.com", "ventas", "Norte"),
            ("Pedro Morales", "593900000009", "pedro@ferreteria.com", "general", "Cumbayá"),
            ("Lucía Silva", "593900000010", "lucia@ferreteria.com", "devoluciones", "Centro"),
            ("Andrés Ortiz", "593900000011", "andres@ferreteria.com", "ventas", "Norte"),
            ("Patricia Luna", "593900000012", "patricia@ferreteria.com", "reclamos", "Cumbayá")
        ]
        
        sellers = []
        for idx, (name, phone, email, specialty, zone) in enumerate(sellers_data):
            # Create user account for seller
            s_user = User(
                username=f"seller{idx+1}",
                email=email,
                password_hash=hash_password(f"seller{idx+1}_pass"),
                role="seller",
                is_active=True
            )
            session.add(s_user)
            await session.commit()
            
            # Create seller profile
            seller = Seller(
                name=name,
                whatsapp_phone=phone,
                email=email,
                is_active=True,
                status="available" if idx < 8 else "offline", # some active, some offline
                max_chats=5 if idx % 2 == 0 else 8,
                active_chats=0,
                last_assigned_at=None,
                work_start_time=datetime.time(8, 0),
                work_end_time=datetime.time(18, 0),
                team_zone=zone,
                priority=10 if idx < 4 else 5
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)
            
            # Add specialty
            spec = SellerSpecialty(seller_id=seller.id, specialty=specialty)
            session.add(spec)
            await session.commit()
            sellers.append(seller)
            
        # 3. Create FAQ Categories
        logger.info("Seeding FAQ categories...")
        cat_names = [
            ("general", "Información general y corporativa"),
            ("horarios", "Horarios de sucursales y días festivos"),
            ("pagos", "Formas y métodos de pago aceptados"),
            ("entregas", "Tiempos, costos y políticas de entrega a domicilio"),
            ("productos", "Garantías, marcas y stock"),
            ("empresa", "Sobre nosotros y contactos principales")
        ]
        categories = {}
        for name, desc in cat_names:
            cat = FAQCategory(name=name, description=desc, active=True)
            session.add(cat)
            await session.commit()
            await session.refresh(cat)
            categories[name] = cat
            
        # 4. Create default FAQ documents
        logger.info("Seeding FAQ documents...")
        default_faqs = [
            (
                "¿Cuál es el horario de atención?",
                "En Ferretería Castor atendemos de Lunes a Viernes de 07:30 AM a 06:00 PM y Sábados de 08:00 AM a 02:00 PM. Los domingos permanecemos cerrado.",
                "horarios",
                ["horario", "atención", "hora", "abierto", "sábado", "domingo"]
            ),
            (
                "¿Cuáles son sus sucursales y cómo los contacto?",
                "Contamos con tres sucursales:\n1. Matriz Centro: Av. 10 de Agosto, Quito (Tel: +593 2 255-5555)\n2. Sucursal Norte: Av. Galo Plaza Lasso y Capitán Ramón Borja\n3. Sucursal Cumbayá: Av. Interoceánica km 12.\nTeléfono de atención al cliente centralizado: +593 9 8888 8888.",
                "general",
                ["sucursal", "ubicación", "dónde", "dirección", "teléfono", "contacto", "Quito", "Cumbayá"]
            ),
            (
                "¿Cuáles son las políticas y costos de entrega?",
                "Las entregas a domicilio son GRATIS en compras superiores a $150 dentro del perímetro urbano de Quito. Para compras menores, aplica un recargo fijo de $5. Las entregas estándar se realizan en un lapso de 24 a 48 horas laborables.",
                "entregas",
                ["entrega", "domicilio", "costo", "gratis", "tiempo", "envío", "tarda"]
            ),
            (
                "¿Qué métodos de pago aceptan?",
                "Aceptamos efectivo, transferencias bancarias directas, tarjetas de débito y crédito (Visa, Mastercard, Diners, American Express) con diferidos de hasta 3 y 6 meses sin intereses en compras superiores a $200.",
                "pagos",
                ["pago", "tarjeta", "efectivo", "crédito", "débito", "transferencia", "diferir", "meses"]
            ),
            (
                "¿Cuál es la política de garantías y devoluciones?",
                "Todos nuestros productos eléctricos y maquinaria cuentan con al menos 1 año de garantía contra defectos de fabricación. Las devoluciones se aceptan dentro de los primeros 5 días hábiles posteriores a la compra, presentando la factura original y el producto en su empaque sellado sin señales de uso.",
                "productos",
                ["garantía", "devolución", "devolver", "dañado", "cambio", "factura", "días"]
            )
        ]
        
        for title, content, cat_name, keywords in default_faqs:
            faq = FAQDocument(
                title=title,
                content=content,
                category_id=categories[cat_name].id,
                keywords=keywords,
                active=True,
                priority=10,
                created_by=admin_user.id,
                updated_by=admin_user.id,
                qdrant_synced=False,
                qdrant_vector_id=None,
                source="manual"
            )
            session.add(faq)
            await session.commit()
            
        # 5. Create System Settings
        logger.info("Seeding system settings...")
        settings_data = [
            ("allow_automatic_handoff", "true", "Habilita que el bot derive automáticamente en caso de no saber la respuesta."),
            ("require_identity_verification", "true", "Exige cédula o teléfono antes de dar información sensible sobre tickets."),
            ("welcome_message", "¡Hola! Bienvenido a Ferretería Castor. Estoy aquí para responder tus preguntas frecuentes o consultar el estado de tu pedido. ¿En qué puedo ayudarte?", "Mensaje de bienvenida del chatbot.")
        ]
        for key, val, desc in settings_data:
            setting = SystemSetting(key=key, value=val, description=desc)
            session.add(setting)
            await session.commit()

        logger.info("Database seeding completed successfully.")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
