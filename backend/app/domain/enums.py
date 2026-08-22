from enum import Enum

class TicketStatus(str, Enum):
    CREATED = "created"
    SENT_TO_WAREHOUSE = "sent_to_warehouse"
    ASSIGNED_TO_WAREHOUSE = "assigned_to_warehouse"
    PICKING = "picking"
    LOADING = "loading"
    LOADED = "loaded"
    DISPATCHED = "dispatched"
    IN_ROUTE = "in_route"
    DELIVERED = "delivered"
    DELIVERY_FAILED = "delivery_failed"
    RETURNING = "returning"
    ARRIVED_BACK = "arrived_back"
    CANCELLED = "cancelled"

class TransitionAction(str, Enum):
    START_TRIP = "start_trip"
    ARRIVE_PLANT = "arrive_plant"
    START_QUEUE = "start_queue"
    ENTER_PLANT = "enter_plant"
    START_LOADING = "start_loading"
    FINISH_LOADING = "finish_loading"
    START_RETURN = "start_return"
    ARRIVE_ORIGIN = "arrive_origin"
    START_UNLOADING = "start_unloading"
    FINISH_UNLOADING = "finish_unloading"
    CANCEL = "cancel"

class IncidentType(str, Enum):
    SLEEP_BREAK = "sleep_break"
    FOOD_BREAK = "food_break"
    PLANT_DELAY = "plant_delay"
    QUEUE_DELAY = "queue_delay"
    MECHANICAL_ISSUE = "mechanical_issue"
    DOCUMENT_ISSUE = "document_issue"
    PLANT_NO_DISPATCH = "plant_no_dispatch"
    ACCIDENT = "accident"
    ROUTE_CHANGE = "route_change"
    WAREHOUSE_CLOSED = "warehouse_closed"
    OTHER = "other"

class HandoffStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RESOLVED = "resolved"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    HANDED_OVER = "handed_over"
