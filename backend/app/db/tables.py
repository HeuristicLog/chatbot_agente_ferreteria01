import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Text, Time
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
