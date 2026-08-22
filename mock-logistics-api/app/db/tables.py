import uuid
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class MockDriver(Base):
    __tablename__ = "mock_drivers"

    email = Column(String(255), primary_key=True)
    password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    token = Column(String(500), nullable=True)

class MockTicket(Base):
    __tablename__ = "mock_tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False, default="created")
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    items = Column(JSONB, nullable=False, default=list)
    customer_phone = Column(String(50), nullable=True)
    customer_identity = Column(String(50), nullable=True)
    order_number = Column(String(100), nullable=True)

class MockTicketEvent(Base):
    __tablename__ = "mock_ticket_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey("mock_tickets.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

class MockLogisticOperation(Base):
    __tablename__ = "mock_logistic_operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(50), nullable=False, default="in_progress")
    route = Column(String(255), nullable=False)
    driver_name = Column(String(255), nullable=True)
    vehicle = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class MockStop(Base):
    __tablename__ = "mock_stops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(Integer, ForeignKey("mock_logistic_operations.id", ondelete="CASCADE"), nullable=False)
    stop_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="pending")  # pending, active, finished
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

class MockIncident(Base):
    __tablename__ = "mock_incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(Integer, ForeignKey("mock_logistic_operations.id", ondelete="CASCADE"), nullable=False)
    incident_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())
