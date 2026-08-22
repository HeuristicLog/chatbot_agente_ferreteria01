import uuid
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from qdrant_client import AsyncQdrantClient

from app.db.session import get_db_session
from app.db.tables import FAQDocument
from app.dependencies import get_redis, get_qdrant
from app.services.faq_service import FAQService
from app.services.flowise_service import FlowiseService

logger = logging.getLogger("chatbot-api.api.admin")
router = APIRouter()

# -----------------
# FAQ Admin REST API Endpoints
# -----------------

@router.get("/api/v1/admin/faqs")
async def list_faqs(db: AsyncSession = Depends(get_db_session)):
    """Retrieves all active FAQ documents."""
    try:
        stmt = select(FAQDocument).where(FAQDocument.active == True).order_by(FAQDocument.created_at.desc())
        result = await db.execute(stmt)
        docs = result.scalars().all()
        return {
            "success": True,
            "data": [
                {
                    "id": str(d.id),
                    "title": d.title,
                    "category": d.category or "general",
                    "source": d.source or "manual",
                    "content": d.content,
                    "created_at": d.created_at.isoformat() if d.created_at else None
                }
                for d in docs
            ]
        }
    except Exception as e:
        logger.error(f"Failed to list FAQs: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al listar las preguntas frecuentes."})

@router.post("/api/v1/admin/faqs")
async def create_faq(
    title: str = Body(...),
    content: str = Body(...),
    category: str = Body("general"),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    """Creates a new FAQ document and indexes it in Qdrant in real-time."""
    faq_service = FAQService(db, qdrant_client)
    try:
        doc = FAQDocument(
            title=title,
            content=content,
            category=category,
            source="manual",
            active=True
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        
        # Sync with Qdrant in real-time
        qdrant_synced = await faq_service.upsert_document_vector(doc)
        
        return {
            "success": True,
            "data": {
                "id": str(doc.id),
                "title": doc.title,
                "category": doc.category,
                "content": doc.content,
                "qdrant_synced": qdrant_synced
            },
            "message": "Pregunta frecuente creada y sincronizada con éxito."
        }
    except Exception as e:
        logger.error(f"Failed to create FAQ: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al crear la pregunta frecuente."})

@router.put("/api/v1/admin/faqs/{faq_id}")
async def update_faq(
    faq_id: uuid.UUID,
    title: str = Body(...),
    content: str = Body(...),
    category: str = Body(...),
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    """Updates an existing FAQ document and re-indexes it in Qdrant in real-time."""
    faq_service = FAQService(db, qdrant_client)
    try:
        stmt = select(FAQDocument).where(FAQDocument.id == faq_id, FAQDocument.active == True)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Pregunta frecuente no encontrada.")
            
        doc.title = title
        doc.content = content
        doc.category = category
        await db.commit()
        await db.refresh(doc)
        
        # Sync with Qdrant in real-time
        qdrant_synced = await faq_service.upsert_document_vector(doc)
        
        return {
            "success": True,
            "data": {
                "id": str(doc.id),
                "title": doc.title,
                "category": doc.category,
                "content": doc.content,
                "qdrant_synced": qdrant_synced
            },
            "message": "Pregunta frecuente actualizada y sincronizada con éxito."
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to update FAQ {faq_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al actualizar la pregunta frecuente."})

@router.delete("/api/v1/admin/faqs/{faq_id}")
async def delete_faq(
    faq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    qdrant_client: AsyncQdrantClient = Depends(get_qdrant)
):
    """Deactivates an FAQ document and removes its points from Qdrant in real-time."""
    faq_service = FAQService(db, qdrant_client)
    try:
        stmt = select(FAQDocument).where(FAQDocument.id == faq_id)
        result = await db.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Pregunta frecuente no encontrada.")
            
        doc.active = False
        await db.commit()
        
        # Remove from Qdrant
        qdrant_removed = await faq_service.delete_document_vector(faq_id)
        
        return {
            "success": True,
            "message": "Pregunta frecuente eliminada de la base de datos y de Qdrant.",
            "qdrant_removed": qdrant_removed
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to delete FAQ {faq_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": "Error al eliminar la pregunta frecuente."})

# -----------------
# Chat Test Endpoint
# -----------------

@router.post("/api/v1/admin/test-chat")
async def test_chat(
    message: str = Body(..., embed=True),
    session_id: Optional[str] = Body(None, embed=True)
):
    """Direct chat interface to query Flowise using an admin testing session ID."""
    flowise_service = FlowiseService()
    try:
        sess = session_id or "admin_test_session"
        reply = await flowise_service.get_prediction(message, session_id=sess)
        return {"success": True, "reply": reply}
    except Exception as e:
        logger.error(f"Chat test error: {str(e)}")
        return JSONResponse(status_code=500, content={"success": False, "message": f"Error de comunicación con Flowise: {str(e)}"})

# -----------------
# Admin Dashboard HTML Template
# -----------------

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    html_content = r"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Castor FAQ Admin Dashboard</title>
    <!-- Google Fonts Outfit & Inter -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #fffaf5;
            --sidebar-bg: #ffffff;
            --card-bg: #ffffff;
            --border-color: #fbbf24;
            --primary-gradient: linear-gradient(135deg, #fbbf24, #d97706);
            --primary-color: #d97706;
            --text-color: #333333;
            --text-muted: #737373;
            --success-color: #10b981;
            --error-color: #ef4444;
            --shadow: 0 4px 12px rgba(217, 119, 6, 0.1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            overflow-x: hidden;
        }

        /* Sidebar styling */
        .sidebar {
            width: 280px;
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 2.5rem 1.5rem;
            position: fixed;
            height: 100vh;
            left: 0;
            top: 0;
            z-index: 10;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 3.5rem;
        }

        .logo-icon {
            font-size: 2.25rem;
        }

        .logo-text {
            font-family: 'Outfit', sans-serif;
            font-size: 1.5rem;
            font-weight: 800;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.85rem 1.25rem;
            border-radius: 0.75rem;
            cursor: pointer;
            font-weight: 500;
            color: var(--text-muted);
            transition: all 0.3s ease;
        }

        .nav-item.active {
            background-color: #fff7ed;
            color: var(--primary-color);
        }

        .nav-item:hover {
            background-color: #fff7ed;
            color: var(--primary-color);
        }

        /* Main Content Container */
        .main-content {
            margin-left: 280px;
            flex-grow: 1;
            padding: 3rem 4rem;
            position: relative;
        }

        header {
            margin-bottom: 3rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header-title {
            font-family: 'Outfit', sans-serif;
            font-size: 2.25rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .header-subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
            margin-top: 0.25rem;
        }

        /* Glassmorphic Cards */
        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 1.25rem;
            padding: 2.5rem;
            box-shadow: var(--shadow);
            margin-bottom: 2rem;
            animation: fadeIn 0.6s ease;
        }

        /* Form styling */
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }

        .input-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        label {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        input, textarea, select {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 0.75rem;
            padding: 0.85rem 1rem;
            color: var(--text-color);
            font-family: 'Inter', sans-serif;
            font-size: 0.95rem;
            transition: all 0.3s ease;
            outline: none;
        }

        input:focus, textarea:focus, select:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 0 2px rgba(217, 119, 6, 0.15);
            background: #ffffff;
        }

        textarea {
            resize: vertical;
            min-height: 120px;
        }

        .btn {
            padding: 0.85rem 1.75rem;
            border-radius: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.95rem;
        }

        .btn-primary {
            background: var(--primary-gradient);
            color: #fff;
            box-shadow: 0 4px 14px 0 rgba(217, 119, 6, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px 0 rgba(217, 119, 6, 0.5);
        }

        .btn-secondary {
            background: #ffffff;
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }

        .btn-secondary:hover {
            background: #fff7ed;
        }

        /* FAQ List styling */
        .faq-list {
            margin-top: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .faq-item {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 0.85rem;
            padding: 1.5rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            transition: all 0.3s ease;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.01);
        }

        .faq-item:hover {
            background: #ffffff;
            border-color: var(--primary-color);
            transform: scale(1.005);
        }

        .faq-meta {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }

        .category-badge {
            background: #fff7ed;
            color: var(--primary-color);
            padding: 0.25rem 0.6rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .faq-title {
            font-size: 1.15rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        .faq-content {
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.5;
            white-space: pre-wrap;
        }

        .action-buttons {
            display: flex;
            gap: 0.5rem;
        }

        .btn-sm {
            padding: 0.5rem 0.75rem;
            font-size: 0.8rem;
            border-radius: 0.5rem;
        }

        .btn-edit {
            background: #fff7ed;
            color: var(--primary-color);
        }

        .btn-delete {
            background: #fef2f2;
            color: var(--error-color);
        }

        /* Slide-out Chat Widget */
        .chat-container {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 380px;
            height: 500px;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 1.25rem;
            box-shadow: var(--shadow);
            z-index: 100;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            transform: translateY(calc(100% - 60px));
        }

        .chat-container.open {
            transform: translateY(0);
        }

        .chat-header {
            background: var(--primary-gradient);
            padding: 1rem 1.25rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            color: white;
        }

        .chat-header-info {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .chat-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
        }

        .chat-name {
            font-weight: 600;
            font-size: 0.95rem;
        }

        .chat-status {
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.9);
        }

        .chat-messages {
            flex-grow: 1;
            padding: 1.25rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            background: #fffaf5;
        }

        .message {
            max-width: 80%;
            padding: 0.75rem 1rem;
            border-radius: 0.85rem;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .message.user {
            background: var(--primary-color);
            color: #fff;
            align-self: flex-end;
            border-bottom-right-radius: 0.15rem;
        }

        .message.bot {
            background: #ffffff;
            color: var(--text-color);
            align-self: flex-start;
            border-bottom-left-radius: 0.15rem;
            border: 1px solid var(--border-color);
        }

        .chat-input-area {
            padding: 0.75rem 1rem;
            background: #ffffff;
            border-top: 1px solid var(--border-color);
            display: flex;
            gap: 0.5rem;
        }

        .chat-input {
            flex-grow: 1;
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 0.5rem 1rem;
            color: var(--text-color);
            font-size: 0.9rem;
            outline: none;
        }

        .chat-send-btn {
            background: var(--primary-gradient);
            border: none;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            cursor: pointer;
        }

        /* Toast notifications */
        .toast {
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: var(--success-color);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0.75rem;
            box-shadow: var(--shadow);
            z-index: 1000;
            display: none;
            animation: slideIn 0.3s ease;
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="logo-area">
            <span class="logo-icon">🦫</span>
            <span class="logo-text">Castor Admin</span>
        </div>
        <ul class="nav-list">
            <li class="nav-item active">Preguntas Frecuentes</li>
        </ul>
    </div>

    <div class="main-content">
        <header>
            <div>
                <h1 class="header-title">Preguntas Frecuentes (FAQs)</h1>
                <p class="header-subtitle">Configura la base de conocimientos y actualiza Qdrant en tiempo real.</p>
            </div>
        </header>

        <div class="glass-card">
            <h2 style="font-family:'Outfit', sans-serif; font-size:1.5rem; margin-bottom:1.5rem;" id="form-title">Agregar FAQ</h2>
            <form id="faq-form" onsubmit="saveFAQ(event)">
                <input type="hidden" id="faq-id">
                <div class="form-grid">
                    <div class="input-group">
                        <label for="title">Pregunta / Título</label>
                        <input type="text" id="title" placeholder="¿Cuál es la política de garantías?" required>
                    </div>
                    <div class="input-group">
                        <label for="category">Categoría</label>
                        <select id="category">
                            <option value="horarios">Horarios y Ubicaciones</option>
                            <option value="pagos">Métodos de Pago</option>
                            <option value="entregas">Políticas de Entrega</option>
                            <option value="productos">Garantías y Productos</option>
                            <option value="empresa">Sobre la Empresa</option>
                            <option value="general">General</option>
                        </select>
                    </div>
                </div>
                <div class="input-group" style="margin-bottom:1.5rem;">
                    <label for="content">Respuesta / Contenido</label>
                    <textarea id="content" placeholder="Escribe aquí la respuesta que Castor debe recordar..." required></textarea>
                </div>
                <div style="display:flex; gap:0.75rem;">
                    <button type="submit" class="btn btn-primary" id="submit-btn">Guardar y Sincronizar</button>
                    <button type="button" class="btn btn-secondary" onclick="resetForm()">Cancelar</button>
                </div>
            </form>
        </div>

        <div class="glass-card">
            <h2 style="font-family:'Outfit', sans-serif; font-size:1.5rem; margin-bottom:1.5rem;">Base de Conocimiento Actual</h2>
            <div id="faq-container" class="faq-list">
                <p style="color:var(--text-muted)">Cargando base de conocimiento...</p>
            </div>
        </div>
    </div>

    <!-- Chat Widget -->
    <div class="chat-container" id="chat-container">
        <div class="chat-header" onclick="toggleChat()">
            <div class="chat-header-info">
                <div class="chat-avatar">🦫</div>
                <div>
                    <div class="chat-name">Castor Chatbot</div>
                    <div class="chat-status">Prueba tus FAQs en vivo</div>
                </div>
            </div>
            <div id="chat-toggle-icon">▲</div>
        </div>
        <div class="chat-messages" id="chat-messages">
            <div class="message bot">¡Hola! Soy Castor, tu asistente ferretero. Escribe cualquier pregunta para probar si me he actualizado correctamente con las FAQs.</div>
        </div>
        <form class="chat-input-area" onsubmit="sendMessage(event)">
            <input type="text" class="chat-input" id="chat-input" placeholder="Hazme una pregunta...">
            <button type="submit" class="chat-send-btn">➤</button>
        </form>
    </div>

    <div class="toast" id="toast">Operación realizada con éxito.</div>

    <script>
        let faqs = [];

        function parseMarkdown(text) {
            if (!text) return "";
            let html = text;
            
            // Escape HTML entities to prevent rendering issues, except if we are injecting our tags
            html = html
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
                
            // Convert Bold: **text** -> <strong>text</strong>
            html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            
            // Convert Italic / Bold-Italic: *text* -> <em>text</em>
            html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            // Convert bullet points and numbered lists
            const lines = html.split('\n');
            const processedLines = lines.map(line => {
                // If it starts with space(s) and * or -
                const bulletMatch = line.match(/^(\s*)([\*\-])\s+(.*)$/);
                if (bulletMatch) {
                    const indent = bulletMatch[1] ? bulletMatch[1].length * 10 : 0;
                    return `<div style="margin-left: ${indent + 15}px; text-indent: -10px; margin-top: 4px;">• ${bulletMatch[3]}</div>`;
                }
                
                // If it's a numbered list item: "1. **text**"
                const numberMatch = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
                if (numberMatch) {
                    const indent = numberMatch[1] ? numberMatch[1].length * 10 : 0;
                    return `<div style="margin-left: ${indent}px; margin-top: 8px; font-weight: 600; color: #f59e0b;">${numberMatch[2]}. ${numberMatch[3]}</div>`;
                }
                return line;
            });
            
            return processedLines.join('\n').replace(/\n/g, '<br>');
        }

        async function loadFAQs() {
            try {
                const response = await fetch('/api/v1/admin/faqs');
                const result = await response.json();
                if (result.success) {
                    faqs = result.data;
                    renderFAQs();
                }
            } catch (err) {
                console.error("Error loading FAQs:", err);
            }
        }

        function renderFAQs() {
            const container = document.getElementById('faq-container');
            if (faqs.length === 0) {
                container.innerHTML = '<p style="color:var(--text-muted)">No hay preguntas frecuentes registradas.</p>';
                return;
            }
            container.innerHTML = faqs.map(faq => `
                <div class="faq-item">
                    <div style="flex-grow:1; padding-right:2rem;">
                        <div class="faq-meta">
                            <span class="category-badge">${faq.category}</span>
                        </div>
                        <h3 class="faq-title">${faq.title}</h3>
                        <div class="faq-content">${parseMarkdown(faq.content)}</div>
                    </div>
                    <div class="action-buttons">
                        <button class="btn btn-secondary btn-sm btn-edit" onclick="editFAQ('${faq.id}')">Editar</button>
                        <button class="btn btn-secondary btn-sm btn-delete" onclick="deleteFAQ('${faq.id}')">Eliminar</button>
                    </div>
                </div>
            `).join('');
        }

        async function saveFAQ(e) {
            e.preventDefault();
            const id = document.getElementById('faq-id').value;
            const title = document.getElementById('title').value;
            const category = document.getElementById('category').value;
            const content = document.getElementById('content').value;

            const url = id ? `/api/v1/admin/faqs/${id}` : '/api/v1/admin/faqs';
            const method = id ? 'PUT' : 'POST';

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, content, category })
                });
                const result = await response.json();
                if (result.success) {
                    showToast(id ? "FAQ actualizada con éxito" : "FAQ creada y sincronizada con Qdrant");
                    resetForm();
                    loadFAQs();
                } else {
                    showToast("Error: " + result.message, true);
                }
            } catch (err) {
                showToast("Error de conexión", true);
            }
        }

        async function deleteFAQ(id) {
            if (!confirm("¿Estás seguro de eliminar esta pregunta frecuente? Se borrará de la base de datos y de Qdrant.")) return;
            try {
                const response = await fetch(`/api/v1/admin/faqs/${id}`, { method: 'DELETE' });
                const result = await response.json();
                if (result.success) {
                    showToast("FAQ eliminada y removida de Qdrant");
                    loadFAQs();
                } else {
                    showToast("Error al eliminar", true);
                }
            } catch (err) {
                showToast("Error de conexión", true);
            }
        }

        function editFAQ(id) {
            const faq = faqs.find(f => f.id === id);
            if (!faq) return;
            document.getElementById('faq-id').value = faq.id;
            document.getElementById('title').value = faq.title;
            document.getElementById('category').value = faq.category;
            document.getElementById('content').value = faq.content;
            document.getElementById('form-title').innerText = "Editar FAQ";
            document.getElementById('submit-btn').innerText = "Actualizar y Sincronizar";
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        function resetForm() {
            document.getElementById('faq-id').value = "";
            document.getElementById('faq-form').reset();
            document.getElementById('form-title').innerText = "Agregar FAQ";
            document.getElementById('submit-btn').innerText = "Guardar y Sincronizar";
        }

        function showToast(msg, isError = false) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.style.background = isError ? 'var(--error-color)' : 'var(--success-color)';
            toast.style.display = 'block';
            setTimeout(() => { toast.style.display = 'none'; }, 3000);
        }

        /* Chat Widget Logic */
        let chatOpen = false;
        const chatSessionId = "admin_test_" + Math.random().toString(36).substring(2, 15);

        function toggleChat() {
            const chat = document.getElementById('chat-container');
            const icon = document.getElementById('chat-toggle-icon');
            chatOpen = !chatOpen;
            if (chatOpen) {
                chat.classList.add('open');
                icon.innerText = "▼";
            } else {
                chat.classList.remove('open');
                icon.innerText = "▲";
            }
        }

        async function sendMessage(e) {
            e.preventDefault();
            const input = document.getElementById('chat-input');
            const text = input.value.trim();
            if (!text) return;

            input.value = "";
            appendMessage(text, 'user');

            // Show typing indicator
            const typingId = appendMessage("Castor está pensando...", 'bot', true);

            try {
                const response = await fetch('/api/v1/admin/test-chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text, session_id: chatSessionId })
                });
                const result = await response.json();
                
                // Remove typing indicator
                document.getElementById(typingId).remove();

                if (result.success) {
                    appendMessage(result.reply, 'bot');
                } else {
                    appendMessage("Error: " + result.message, 'bot');
                }
            } catch (err) {
                document.getElementById(typingId).remove();
                appendMessage("Error de conexión con el backend", 'bot');
            }
        }

        function appendMessage(text, sender, isTemp = false) {
            const container = document.getElementById('chat-messages');
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            
            if (sender === 'bot' && !isTemp) {
                msgDiv.innerHTML = parseMarkdown(text);
            } else {
                msgDiv.innerText = text;
            }
            
            const id = "msg-" + Date.now();
            msgDiv.id = id;
            container.appendChild(msgDiv);
            container.scrollTop = container.scrollHeight;
            return id;
        }

        // Init
        loadFAQs();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)
