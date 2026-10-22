import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Text, Time, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="seller")  # super_admin, admin, supervisor, seller, viewer
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class FAQCategory(Base):
    __tablename__ = "faq_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class FAQDocument(Base):
    __tablename__ = "faq_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)  # Pregunta
    content = Column(Text, nullable=False)        # Respuesta
    category_id = Column(UUID(as_uuid=True), ForeignKey("faq_categories.id", ondelete="SET NULL"), nullable=True)
    keywords = Column(JSONB, nullable=False, default=list)  # Palabras clave
    active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    qdrant_synced = Column(Boolean, nullable=False, default=False)
    qdrant_vector_id = Column(String(255), nullable=True)
    source = Column(String(100), nullable=False, default="manual")
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)

    # Temporary properties for backwards compatibility
    @property
    def category(self):
        return "general"  # Mocked category property for legacy routers

class FAQVersion(Base):
    __tablename__ = "faq_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    faq_id = Column(UUID(as_uuid=True), ForeignKey("faq_documents.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), nullable=True)
    keywords = Column(JSONB, nullable=False, default=list)
    active = Column(Boolean, nullable=False)
    priority = Column(Integer, nullable=False)
    modified_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    modified_at = Column(DateTime(timezone=True), server_default=func.now())

class FAQSyncJob(Base):
    __tablename__ = "faq_sync_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(50), nullable=False, default="pending")  # pending, running, completed, failed
    source_file = Column(String(255), nullable=True)
    records_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    whatsapp_phone = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="offline")  # available, busy, offline, out_of_hours
    max_chats = Column(Integer, nullable=False, default=5)
    active_chats = Column(Integer, nullable=False, default=0)
    last_assigned_at = Column(DateTime(timezone=True), nullable=True)
    work_start_time = Column(Time, nullable=False)
    work_end_time = Column(Time, nullable=False)
    team_zone = Column(String(100), nullable=True)
    priority = Column(Integer, nullable=False, default=0)

class SellerSpecialty(Base):
    __tablename__ = "seller_specialties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    specialty = Column(String(100), nullable=False)

class Conversation(Base):
    __tablename__ = "chatbot_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    phone_hash = Column(String(255), nullable=False, index=True)  # WhatsApp customer phone
    provider = Column(String(50), nullable=False, default="mock")
    status = Column(String(50), nullable=False, default="bot_active")  # bot_active, waiting_agent, assigned, human_active, resolved, closed, abandoned
    current_seller_id = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)

class ConversationAssignment(Base):
    __tablename__ = "conversation_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, accepted, rejected, completed
    reject_reason = Column(Text, nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

class Message(Base):
    __tablename__ = "chatbot_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False)
    direction = Column(String(20), nullable=False)  # inbound, outbound
    role = Column(String(50), nullable=False)       # user, assistant, seller, system
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False, default="text") # text, media, interactive
    external_message_id = Column(String(255), nullable=True)
    media_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)

class ToolCall(Base):
    __tablename__ = "chatbot_tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    request_payload = Column(JSONB, nullable=False, default=dict)
    response_status = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    error_code = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Handoff(Base):
    __tablename__ = "chatbot_handoffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False)
    phone_hash = Column(String(255), nullable=False, index=True)
    reason = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, active, resolved
    assigned_to = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)

class ConversationNote(Base):
    __tablename__ = "conversation_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_conversations.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WhatsAppMessageEvent(Base):
    __tablename__ = "whatsapp_message_events"

    message_id = Column(String(255), primary_key=True)
    event_type = Column(String(50), nullable=False)  # sent, delivered, read, failed
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    sucursal_stocks = Column(JSONB, nullable=False, default=dict)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(50), nullable=False, unique=True, index=True)
    phone_hash = Column(String(255), nullable=False, index=True)
    customer_phone = Column(String(50), nullable=False)
    customer_name = Column(String(100), nullable=False)
    delivery_type = Column(String(50), nullable=False, default="pickup")  # pickup, delivery
    delivery_address = Column(Text, nullable=True)
    sucursal = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="created")  # created, picking, dispatched, in_route, delivered, cancelled
    payment_method = Column(String(50), nullable=False, default="efectivo")  # efectivo, transferencia, tarjeta
    subtotal = Column(Numeric(10, 2), nullable=False, default=0.0)
    tax = Column(Numeric(10, 2), nullable=False, default=0.0)
    total = Column(Numeric(10, 2), nullable=False, default=0.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=True)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    subtotal = Column(Numeric(10, 2), nullable=False)


# ═══════════════════════════════════════════════════════════════════════════════
# CONCESIONARIO DE AUTOS ECUADOR — MODELOS DE VEHÍCULOS Y SEGUIMIENTO DE LEADS
# ═══════════════════════════════════════════════════════════════════════════════

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, index=True)      # ej: AUT-CHEV-DMAX-2026
    brand = Column(String(100), nullable=False, index=True)                 # Chevrolet, Kia, Toyota, etc.
    model = Column(String(150), nullable=False, index=True)                 # D-Max Premier 3.0L Diésel 4x4
    year = Column(Integer, nullable=False, default=2026)
    body_type = Column(String(100), nullable=False, index=True)             # SUV, Camioneta (Pickup), Sedán, Hatchback
    engine = Column(String(100), nullable=False)                            # 3.0L Diésel Turbo 190 HP
    fuel_type = Column(String(50), nullable=False, default="Gasolina")      # Gasolina, Diésel, Híbrido, Eléctrico
    transmission = Column(String(150), nullable=False)                      # Manual 6 Vel, Automática 6 Vel, CVT
    traction = Column(String(150), nullable=False, default="4x2")           # 4x2 FWD, 4x4 con Reductora, AWD
    passenger_capacity = Column(Integer, nullable=False, default=5)         # 5 o 7 pasajeros
    trunk_capacity_liters = Column(Integer, nullable=True)                  # Capacidad de cajuela / balde
    price_usd = Column(Numeric(10, 2), nullable=False)                      # Precio venta al público con IVA
    min_down_payment = Column(Numeric(10, 2), nullable=False)               # Entrada mínima (20% - 25%)
    estimated_monthly_fee = Column(Numeric(10, 2), nullable=False)          # Cuota estimada a 48/60 meses
    description = Column(Text, nullable=True)
    safety_features = Column(JSONB, nullable=False, default=list)           # [6 Airbags, ABS+EBD, Control de estabilidad ESP]
    equipment = Column(JSONB, nullable=False, default=list)                 # [Pantalla 10", Apple CarPlay, Cámara 360]
    colors_available = Column(JSONB, nullable=False, default=list)          # [Blanco, Plata, Negro, Rojo, Gris]
    image_url = Column(String(500), nullable=False)                         # Foto frontal destacada
    gallery_urls = Column(JSONB, nullable=False, default=list)              # Fotos secundarias e interiores
    stock_units = Column(Integer, nullable=False, default=1)
    is_featured = Column(Boolean, nullable=False, default=False)            # Destacado en vitrina
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VehicleLead(Base):
    __tablename__ = "vehicle_leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_code = Column(String(50), nullable=False, unique=True, index=True) # ej: LEAD-2026-001
    customer_phone = Column(String(50), nullable=False, index=True)
    phone_hash = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(150), nullable=True)
    city = Column(String(100), nullable=True)                              # Quito, Guayaquil, Cuenca, etc.
    interested_vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    interested_model_name = Column(String(150), nullable=True)
    quote_type = Column(String(50), nullable=False, default="credito")      # contado, credito, retoma_usado
    down_payment_offered = Column(Numeric(10, 2), nullable=True)            # Entrada que tiene el cliente
    term_months = Column(Integer, nullable=True, default=48)                # Plazo deseado: 12, 24, 36, 48, 60 meses
    test_drive_requested = Column(Boolean, nullable=False, default=False)
    test_drive_date = Column(DateTime(timezone=True), nullable=True)
    assigned_seller_id = Column(UUID(as_uuid=True), ForeignKey("sellers.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(50), nullable=False, default="nuevo")            # nuevo, cotizado, test_drive_agendado, en_credito, ganado, perdido
    chatwoot_conversation_id = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VehicleCartItem(Base):
    __tablename__ = "vehicle_cart_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_phone = Column(String(50), nullable=False, index=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    down_payment_percent = Column(Integer, nullable=False, default=20)
    down_payment_amount = Column(Numeric(10, 2), nullable=False, default=0.0)
    term_months = Column(Integer, nullable=False, default=48)
    estimated_monthly_fee = Column(Numeric(10, 2), nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="in_cart")          # in_cart, quoted, reserved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VehicleQuote(Base):
    __tablename__ = "vehicle_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_code = Column(String(50), nullable=False, unique=True, index=True) # ej: COT-AUTO-1001
    customer_phone = Column(String(50), nullable=False, index=True)
    customer_name = Column(String(150), nullable=True, default="Cliente WhatsApp")
    city = Column(String(100), nullable=True, default="Quito")
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    vehicle_name = Column(String(200), nullable=False)
    vehicle_price = Column(Numeric(10, 2), nullable=False)
    down_payment = Column(Numeric(10, 2), nullable=False)
    financed_amount = Column(Numeric(10, 2), nullable=False)
    term_months = Column(Integer, nullable=False, default=48)
    monthly_fee = Column(Numeric(10, 2), nullable=False)
    insurance_included = Column(Boolean, nullable=False, default=True)
    trade_in_used_car = Column(Boolean, nullable=False, default=False)
    used_car_details = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pendiente")         # pendiente, contactado, aprobado, entregado
    chatwoot_conversation_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

