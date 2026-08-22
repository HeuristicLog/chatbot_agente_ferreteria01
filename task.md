# Ferretería Chatbot Project Task List

- `[x]` **Fase 2: Infraestructura**
  - `[x]` Configure Docker Compose (`docker-compose.yml`) in `ChatbotFlowise` workspace
  - `[x]` Migrate or link the existing `flowise-chatbot` configuration
  - `[x]` Setup network and volume connections
  - `[x]` Configure port mappings for local access

- `[x]` **Fase 3: Backend FastAPI**
  - `[x]` Design SQLAlchemy models in `tables.py`
  - `[x]` Create FastAPI application structure and include routers
  - `[x]` Implement Admin API: FAQ CRUD + versioning + Qdrant synchronization
  - `[x]` Implement Seller API & Handoff assignment logic (Advisory locks, status tracking)
  - `[x]` Implement Chat API for tickets & orders safe façade

- `[x]` **Fase 4: Mock Logistics API**
  - `[x]` Create `mock-logistics-api` service
  - `[x]` Implement JWT driver auth & matching endpoints
  - `[x]` Implement database seeding script for mock tickets, sellers, and routes

- `[x]` **Fase 5: Frontend Interfaces**
  - `[x]` Implement administrative dashboard (frontend-admin) in React/TS
  - `[x]` Implement agent conversation portal (frontend-agent) in React/TS
  - `[x]` Implement WhatsApp web simulator (whatsapp-simulator) with client/vendedor views

- `[x]` **Fase 6: Flowise Integration**
  - `[x]` Configure Custom Tools JSON
  - `[x]` Deploy Flowise chatbot chatflow JSON
  - `[x]` Verify tool invocations and prompting safeguards

- `[x]` **Fase 7: WhatsApp Integration**
  - `[x]` Setup WhatsApp webhook gateway in backend
  - `[x]` Handle event statuses, deduplication, and template messages
  - `[x]` Add media validation and downloads

- `[x]` **Fase 8: Verification & Testing**
  - `[x]` Run unit tests (FAQ CRUD, seller allocation, mock logistics auth)
  - `[x]` Run integration tests (End-to-end simulated chat flow)
  - `[x]` Write deployment guide and API documentation
