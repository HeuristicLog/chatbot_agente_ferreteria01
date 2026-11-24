"""
LangChain Hardware Store AI Service — Native Code Alternative to Flowise
Handles natural language questions, hardware product recommendations, stock & pricing,
and conversational memory using LangChain and Python natively for Ferretería Castor.
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any

try:
    from app.config import settings
except ImportError:
    settings = None

logger = logging.getLogger("chatbot-api.services.langchain")

# System prompt for Ferretería Castor virtual assistant
SYSTEM_PROMPT = """Eres Castor 🦫, el asistente virtual y asesor técnico experto oficial de Ferretería Castor (Ecuador, 2026).
Tu misión es asesorar a maestros de obra, contratistas, profesionales y clientes del hogar con amabilidad, rapidez y precisión técnica en materiales de construcción, herramientas, pinturas, plomería y electricidad.

Información Oficial de Ferretería Castor:
• Sucursales en Quito:
  - Sucursal Centro (Matriz): Av. 10 de Agosto N45-23 y Mariana de Jesús. (Lunes a Viernes 07:30 a 18:00, Sábados 08:00 a 14:00)
  - Sucursal Norte: Av. Eloy Alfaro N56-10 y Los Álamos. (Lunes a Viernes 08:00 a 18:00, Sábados 08:00 a 13:30)
  - Sucursal Sur: Av. Rodrigo de Chávez y Pedro de Alfaro (Villaflora). (Lunes a Viernes 08:00 a 18:00, Sábados 08:00 a 14:00)
  - Sucursal Cumbayá: Av. Interoceánica km 11.5 frente a Scala Shopping. (Lunes a Sábado 08:30 a 18:00)
• Horarios Generales: Lunes a Viernes 07:30 a 18:00 | Sábados 08:00 a 14:00 | Domingos cerrado.
• Categorías y Productos Destacados en Stock:
  - Herramientas Eléctricas: Rotomartillo Makita HR2470 ($145.00), Amoladora DeWalt 4-1/2" ($89.50), Sierra Circular Bosch 7-1/4" ($135.00), Taladro Percutor Stanley 1/2" ($65.00).
  - Herramientas Manuales: Juego de Llaves Stanley 14 piezas ($38.50), Martillo Truper 16 oz ($12.00), Flexómetro Lufkin 8m ($14.50), Destornilladores Tramontina ($11.50).
  - Materiales de Construcción: Varilla Adelca 12mm x 12m ($9.85), Cemento Selvalegre / Holcim 50kg ($8.40), Pala Truper Cuadrada ($15.20), Carretilla Truper ($68.00).
  - Pinturas y Acabados: Látex Vinilac Caneca Pinturas Unidas ($58.00), Esmalte Sintético Galón ($22.50), Rodillo Pro 9" ($6.50), Sellador Acrílico ($18.00).
  - Plomería: Tubo PVC Desagüe Plastigama 110mm x 3m ($14.20), Tubo Presión 1/2" x 6m ($6.80), Grifería Lavamanos Briggs ($42.00), Llave de Paso Esferica ($4.50).
  - Electricidad: Rollo Cable THHN #12 Indeco 100m ($48.00), Rollo THHN #14 Indeco ($34.00), Breaker Schneider 1x20A ($7.50), Tomacorriente Doble Veto ($4.20).
• Envíos y Logística:
  - Envío GRATIS en Quito urbano en pedidos superiores a $150.
  - Tarifa estándar de flete: $5 para compras menores a $150.
  - Tiempos de entrega: 24 a 48 horas hábiles en obra o domicilio.
  - Retiro gratuito en cualquiera de las 4 sucursales (Pick up inmediato).
• Métodos de Pago: Efectivo contra entrega, Transferencia Banco Pichincha / Produbanco, Tarjetas de crédito/débito, PayPhone y DeUna.
• Catálogo y Carrito In-App: Explora productos con fotos y realiza tu pedido sin salir de WhatsApp.

Directrices de Respuesta (Interactivas y No Texto Plano):
1. NUNCA respondas con párrafos largos o texto plano monótono. Usa viñetas limpias, negritas, subtítulos y emojis de ferretería (🛠️, 🏗️, ⚡, 🎨, 🚰).
2. Al final de CADA respuesta, ofrece siempre opciones interactivas de acción rápida numeradas (ej: 1️⃣ Abrir catálogo, 2️⃣ Consultar pedido, 3️⃣ Hablar con asesor).
3. Invita siempre al cliente a abrir el catálogo interactivo dentro de WhatsApp: https://bot.autoeconomotors.com/catalogo
4. Si el cliente pregunta por un pedido, pídele su número (ej. CAST-2026-1042).
5. Si el cliente pide hablar con una persona o transferir, ofrécele conectarlo de inmediato con un asesor humano en Chatwoot.
"""

class LangChainService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._llm = None
        self._init_llm()

    def _init_llm(self):
        """Inicializa el modelo de lenguaje de LangChain según los proveedores configurados."""
        try:
            if self.openai_api_key:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(
                    model=self.model_name,
                    api_key=self.openai_api_key,
                    temperature=0.3,
                    max_tokens=600
                )
                logger.info(f"LangChain initialized with OpenAI ({self.model_name})")
            elif self.groq_api_key:
                from langchain_community.chat_models import ChatGroq
                self._llm = ChatGroq(
                    model_name="llama-3.3-70b-versatile",
                    groq_api_key=self.groq_api_key,
                    temperature=0.3,
                    max_tokens=600
                )
                logger.info("LangChain initialized with Groq Llama-3.3")
            else:
                logger.info("No LLM API key detected. Using built-in native semantic inference engine.")
        except Exception as e:
            logger.warning(f"Error initializing LangChain LLM: {e}. Using native semantic engine.")
            self._llm = None

    async def _get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """Recupera el historial de conversación desde Redis para mantener contexto."""
        try:
            import redis.asyncio as aioredis
            r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            client = aioredis.from_url(r_url)
            raw = await client.lrange(f"chat_history:{session_id}", -6, -1)
            await client.aclose()
            history = []
            for item in raw:
                try:
                    history.append(json.loads(item))
                except Exception:
                    pass
            return history
        except Exception as e:
            logger.debug(f"Error fetching history from Redis: {e}")
            return []

    async def _save_chat_history(self, session_id: str, user_msg: str, ai_msg: str):
        """Guarda los mensajes en Redis con expiración de 2 horas."""
        try:
            import redis.asyncio as aioredis
            r_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
            client = aioredis.from_url(r_url)
            pipe = client.pipeline()
            pipe.rpush(f"chat_history:{session_id}", json.dumps({"role": "user", "content": user_msg}))
            pipe.rpush(f"chat_history:{session_id}", json.dumps({"role": "assistant", "content": ai_msg}))
            pipe.expire(f"chat_history:{session_id}", 7200)
            await pipe.execute()
            await client.aclose()
        except Exception as e:
            logger.debug(f"Error saving history to Redis: {e}")

    async def get_prediction(self, question: str, session_id: str, phone: str = "") -> str:
        """
        Punto de entrada compatible con Flowise.
        Procesa la consulta del cliente mediante LangChain o motor semántico nativo para Ferretería Castor.
        """
        clean_q = question.strip()
        if not clean_q:
            return "¡Hola! ¿En qué herramienta o material de construcción de Ferretería Castor te podemos asesorar hoy? 🦫🛠️"

        # 1. Si LangChain LLM está configurado con OpenAI/Groq
        if self._llm:
            try:
                from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
                messages = [SystemMessage(content=SYSTEM_PROMPT)]
                
                # Cargar historial conversacional
                history = await self._get_chat_history(session_id)
                for h in history:
                    if h.get("role") == "user":
                        messages.append(HumanMessage(content=h.get("content", "")))
                    else:
                        messages.append(AIMessage(content=h.get("content", "")))
                
                messages.append(HumanMessage(content=clean_q))
                
                # Ejecutar predicción
                res = await self._llm.ainvoke(messages)
                response_text = res.content.strip() if hasattr(res, "content") else str(res).strip()
                
                # Guardar memoria
                await self._save_chat_history(session_id, clean_q, response_text)
                return response_text
            except Exception as e:
                logger.error(f"LangChain LLM error: {e}. Falling back to native semantic engine.")

        # 2. Motor Semántico Nativo Ferretería Castor (100% Código Python)
        native_reply = await self._native_semantic_engine(clean_q, phone)
        await self._save_chat_history(session_id, clean_q, native_reply)
        return native_reply

    async def _native_semantic_engine(self, question: str, phone: str) -> str:
        """
        Motor de inferencia semántica y conversacional en código Python puro para Ferretería Castor.
        Genera respuestas interactivas, estructuradas y visualmente atractivas
        con opciones de navegación rápida y enlace al catálogo webview sin salir de WhatsApp.
        """
        q = question.lower().strip()
        ngrok_url = os.getenv("CATALOG_BASE_URL", "https://bot.autoeconomotors.com")
        clean_phone = phone.replace("+", "").replace(" ", "").strip()
        if not clean_phone:
            clean_phone = "593988921136"
        catalog_url = f"{ngrok_url}/catalogo?phone={clean_phone}&sucursal=Centro"

        # Saludos / Menú principal / Opciones
        if any(k == q or q.startswith(k) for k in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "menú", "inicio", "start", "opciones", "ayuda"]):
            return (
                "¡Hola! 👋 Soy *Castor* 🦫, tu asistente virtual de *Ferretería Castor*.\n\n"
                "Estoy aquí para ayudarte a encontrar herramientas, materiales de construcción, pinturas y gestionar tu carrito de compras 100% dentro de WhatsApp."
            )

        # 1. Catálogo
        if q in ["1", "opcion 1", "opción 1"] or any(k in q for k in ["catalogo", "catálogo", "tienda", "comprar", "precios"]):
            return (
                "🛍️ *Catálogo Interactivo Ferretería Castor* 🦫\n\n"
                "Puedes explorar nuestros departamentos, ver fotos en alta resolución, stock en vivo y agregar productos directamente a tu carrito tocando las opciones abajo:"
            )

        # 2. Estado de Pedido
        if q in ["pedido", "pedidos", "orden", "rastreo", "mi compra"]:
            return (
                "📦 *Rastreo de Pedidos Castor*\n\n"
                "Por favor escribe tu código de pedido (ej: *CAST-2026-1042* o *1042*) para consultar su estado en tiempo real:"
            )

        # 3. Herramientas Eléctricas
        if any(k in q for k in ["electricas", "eléctricas", "taladro", "rotomartillo", "amoladora", "makita", "dewalt", "bosch"]):
            return (
                "⚡ *Herramientas Eléctricas Profesionales*\n\n"
                "Contamos con rotomartillos, taladros inalámbricos 20V, amoladoras y sierras circulares con garantía de fábrica Makita, DeWalt y Bosch."
            )

        # 4. Herramientas Manuales
        if any(k in q for k in ["manuales", "llaves", "martillo", "flexometro", "stanley", "truper"]):
            return (
                "🔧 *Herramientas Manuales de Uso Rudo*\n\n"
                "Juegos de llaves combinadas Stanley, martillos Truper con mango de fibra y flexómetros profesionales con entrega inmediata."
            )

        # 5. Construcción y Tornillería
        if any(k in q for k in ["construccion", "construcción", "cemento", "varilla", "varillas", "adelca", "holcim", "tornillo", "tornillos", "perno", "pernos"]):
            return (
                "🧱 *Materiales de Construcción y Tornillería*\n\n"
                "Cemento Selvalegre/Holcim 50kg, varillas Adelca 12mm y gran variedad de tornillos Drywall, autoperforantes y pernos estructurales."
            )

        # 6. Pinturas y Plomería
        if any(k in q for k in ["pintura", "pinturas", "latex", "plomeria", "tubo", "pvc", "plastigama", "griferia"]):
            return (
                "🎨 *Pinturas y Plomería Profesional*\n\n"
                "Pinturas Látex Vinilac, esmaltes anticorrosivos, tubería PVC Plastigama y grifería FV de primera calidad."
            )

        # 7. Horarios, Sucursales y Envíos
        if any(k in q for k in ["horario", "horarios", "sucursales", "sucursal", "ubicacion", "direccion", "envio"]):
            return (
                "🕒 *Horarios y Sucursales Ferretería Castor:*\n\n"
                "• *Matriz Centro:* Lunes a Viernes 7:30 a 18:00 | Sábados 8:00 a 14:00\n"
                "• *Sucursal Norte y Sur:* Lunes a Viernes 8:00 a 18:00 | Sábados 8:00 a 14:00\n"
                "• *Sucursal Cumbayá:* Lunes a Sábado 8:30 a 18:00\n\n"
                "🚚 *Envíos a domicilio:* Entregas en el mismo día para Quito y valles."
            )

        # 8. Asesor Humano
        if any(k in q for k in ["asesor", "humano", "persona", "agente", "vendedor"]):
            return (
                "👨‍💼 *Atención Personalizada con Asesor*\n\n"
                "Un asesor comercial tomará tu conversación en breve para brindarte cotizaciones personalizadas o compras por volumen."
            )

        # Default conciso
        return (
            "¡Con gusto te ayudo! 🦫\n"
            "En *Ferretería Castor* disponemos de catálogo interactivo, búsqueda de productos, stock en tiempo real y compras directas por WhatsApp."
        )
