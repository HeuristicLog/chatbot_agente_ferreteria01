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
3. Invita siempre al cliente a abrir el catálogo interactivo dentro de WhatsApp: https://usable-thorn-kabob.ngrok-free.dev/catalogo
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
        ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
        clean_phone = phone.replace("+", "").replace(" ", "").strip()
        if not clean_phone:
            clean_phone = "593988921136"
        catalog_url = f"{ngrok_url}/catalogo?phone={clean_phone}&sucursal=Centro&ngrok-skip-browser-warning=1"

        # Saludos / Menú principal / Opciones
        if any(k == q or q.startswith(k) for k in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "menú", "inicio", "start", "opciones", "ayuda"]):
            return (
                "🦫 *¡Bienvenido a Ferretería Castor 2026!* 🇪🇨\n"
                "Soy *Castor*, tu asistente virtual inteligente. Te ayudo a cotizar herramientas, materiales de construcción y hacer tus pedidos con despacho inmediato.\n\n"
                "✨ *Selecciona una opción rápida o escribe lo que necesitas:*\n\n"
                "1️⃣ 🛍️ *Abrir Catálogo y Carrito en Vivo* (Fotos, buscador y compra)\n"
                "2️⃣ 📦 *Consultar Estado de Pedido* (CAST-2026-XXXX)\n"
                "3️⃣ ⚡ *Herramientas Eléctricas* (Makita, DeWalt, Bosch)\n"
                "4️⃣ 🔨 *Herramientas Manuales* (Stanley, Truper, Tramontina)\n"
                "5️⃣ 🏗️ *Materiales de Construcción* (Varillas Adelca, Cemento)\n"
                "6️⃣ 🎨 *Pinturas y Plomería* (Pinturas Unidas, Tubos PVC Plastigama)\n"
                "7️⃣ 🕒 *Horarios, Sucursales y Envíos*\n"
                "8️⃣ 👨‍💼 *Hablar con un Asesor Humano*\n\n"
                f"🛒 *Explora la tienda completa sin salir de WhatsApp:* \n{catalog_url}\n\n"
                "_Responde con un número (1 al 8) o escríbeme directamente tu consulta._"
            )

        # 1. Catálogo y Carrito Webview
        if q in ["1", "opcion 1", "opción 1"] or any(k in q for k in ["catalogo", "catálogo", "carrito", "tienda", "comprar", "productos", "inventario", "precios"]):
            return (
                "🛍️ *Catálogo Interactivo con Carrito — Ferretería Castor*\n\n"
                "Abre nuestra tienda virtual directamente en WhatsApp sin salir de la app:\n\n"
                "• 📸 Explora más de 20 productos con fotos y especificaciones técnicas.\n"
                "• 🔎 Filtra por categorías: Eléctricas, Manuales, Construcción, Pintura, Plomería.\n"
                "• 🛒 Agrega productos a tu carrito y elige retiro en sucursal o envío a domicilio.\n"
                "• 💳 Paga en efectivo contra entrega, transferencia o tarjeta.\n\n"
                f"👉 *Toca este enlace para abrir el catálogo:* \n{catalog_url}\n\n"
                "_¡Pruébalo ahora y realiza tu pedido en segundos!_"
            )

        # 2. Estado de Pedido
        if q in ["2", "opcion 2", "opción 2"] or any(k in q for k in ["pedido", "pedidos", "orden", "ordenes", "estado", "rastreo", "mi compra"]):
            return (
                "📦 *Consulta y Rastreo de Pedidos — Ferretería Castor*\n\n"
                "Para verificar el estado de tu compra, escribe tu código de orden:\n"
                "👉 Ejemplo: *CAST-2026-1042* (o simplemente *1042*).\n\n"
                "Te indicaremos en tiempo real si tu pedido está en preparación en bodega, despachado o en camino con el transportista."
            )

        # 3. Herramientas Eléctricas
        if q in ["3", "opcion 3", "opción 3"] or any(k in q for k in ["herramientas electricas", "herramientas eléctricas", "taladro", "rotomartillo", "amoladora", "esmeril", "sierra", "makita", "dewalt", "bosch"]):
            return (
                "⚡ *Herramientas Eléctricas Profesionales en Stock:*\n\n"
                "🔹 *Rotomartillo Makita HR2470 780W SDS-Plus*\n"
                "   • Precio: *$145.00 USD* | Stock: Disponible\n"
                "   • Potencia para hormigón, metal y madera.\n\n"
                "🔹 *Amoladora Angular DeWalt 4-1/2\" DWE4020 800W*\n"
                "   • Precio: *$89.50 USD* | Stock: Disponible\n"
                "   • Compacta y ergonómica para corte y desbaste.\n\n"
                "🔹 *Sierra Circular Bosch GKS 150 7-1/4\" 1500W*\n"
                "   • Precio: *$135.00 USD* | Stock: Disponible\n"
                "   • Ideal para cortes rectos de alta precisión en madera.\n\n"
                f"🛒 *Ver todas las herramientas eléctricas en el catálogo:* \n{catalog_url}&cat=electricas\n\n"
                "🔘 *¿Qué deseas hacer?*\n"
                "👉 Responde *1* para abrir el carrito de compras.\n"
                "👉 Responde *ASESOR* para cotizaciones técnicas al por mayor."
            )

        # 4. Herramientas Manuales
        if q in ["4", "opcion 4", "opción 4"] or any(k in q for k in ["herramientas manuales", "manuales", "llaves", "martillo", "flexometro", "flexómetro", "destornillador", "destornilladores", "stanley", "truper", "tramontina"]):
            return (
                "🔨 *Herramientas Manuales de Alta Resistencia:*\n\n"
                "🔸 *Juego de Llaves Combinadas Stanley (14 piezas)*: *$38.50 USD*\n"
                "   • Acero cromo vanadio forjado, estuche organizador.\n\n"
                "🔸 *Martillo de Uña Curva Truper 16 oz Mango Fibra*: *$12.00 USD*\n"
                "   • Antivibración, máxima durabilidad.\n\n"
                "🔸 *Flexómetro Profesional Lufkin 8 Metros*: *$14.50 USD*\n"
                "   • Cinta de alta visibilidad con recubrimiento de nailon.\n\n"
                "🔸 *Juego de Destornilladores Tramontina 6 Piezas*: *$11.50 USD*\n"
                "   • Puntas imantadas planas y Phillips.\n\n"
                f"🛒 *Revisa el catálogo completo de herramientas:* \n{catalog_url}&cat=manuales\n\n"
                "👉 Responde *1* para abrir el catálogo o *ASESOR* para hablar con nuestro equipo."
            )

        # 5. Construcción
        if q in ["5", "opcion 5", "opción 5"] or any(k in q for k in ["construccion", "construcción", "cemento", "varilla", "varillas", "adelca", "holcim", "selvalegre", "arena", "ripio", "pala", "carretilla"]):
            return (
                "🏗️ *Materiales de Construcción y Obra Gruesa:*\n\n"
                "🧱 *Varilla Corrugada Adelca 12mm x 12m*\n"
                "   • Precio: *$9.85 USD* / unidad | Norma INEN sismorresistente.\n\n"
                "🧱 *Saco de Cemento Selvalegre / Holcim 50kg*\n"
                "   • Precio: *$8.40 USD* / saco | Alta resistencia inicial y final.\n\n"
                "🧱 *Carretilla Truper Capacidad 6 Pies Cúbicos*\n"
                "   • Precio: *$68.00 USD* | Tolva metálica de alta capacidad.\n\n"
                "🧱 *Pala Cuadrada Truper Mango de Fibra*\n"
                "   • Precio: *$15.20 USD* | Ideal para excavación y mezcla.\n\n"
                "🚚 *Envíos en Quito:* Flete gratis en compras superiores a $150.\n\n"
                f"🛒 *Cotiza tus materiales en el catálogo:* \n{catalog_url}&cat=construccion\n\n"
                "👉 Responde *ASESOR* para cotizaciones de obra por volumen."
            )

        # 6. Pinturas y Plomería
        if q in ["6", "opcion 6", "opción 6"] or any(k in q for k in ["pintura", "pinturas", "esmalte", "latex", "látex", "plomeria", "plomería", "tubo", "tubos", "pvc", "plastigama", "griferia", "grifería", "briggs"]):
            return (
                "🎨 *Pinturas, Acabados y Plomería en Stock:*\n\n"
                "🖌️ *Látex Vinilac Pinturas Unidas (Caneca 5 galones)*\n"
                "   • Precio: *$58.00 USD* | Máximo cubrimiento lavable para interiores y fachadas.\n\n"
                "🖌️ *Esmalte Sintético Anticorrosivo (Galón)*\n"
                "   • Precio: *$22.50 USD* | Protección contra óxido en metales y madera.\n\n"
                "🚰 *Tubo PVC Plastigama Desagüe 110mm x 3m*\n"
                "   • Precio: *$14.20 USD* | Alta resistencia para aguas servidas y pluviales.\n\n"
                "🚰 *Grifería Monomando Lavamanos Briggs Cromada*\n"
                "   • Precio: *$42.00 USD* | Cartucho cerámico de alta durabilidad.\n\n"
                f"🛒 *Explora la sección en el catálogo:* \n{catalog_url}\n\n"
                "👉 Responde *1* para abrir el catálogo o *ASESOR* para asistencia personalizada."
            )

        # 7. Horarios, Sucursales y Envíos
        if q in ["7", "opcion 7", "opción 7"] or any(k in q for k in ["horario", "horarios", "sucursales", "sucursal", "ubicacion", "ubicación", "donde estan", "dónde están", "direccion", "dirección", "envio", "envíos", "flete"]):
            return (
                "📍 *Sucursales y Horarios de Ferretería Castor:*\n\n"
                "🏛️ *Sucursal Centro (Matriz):*\n"
                "   • Av. 10 de Agosto N45-23 y Mariana de Jesús\n"
                "   • 🕒 Lunes a Viernes: 07:30 a 18:00 | Sábados: 08:00 a 14:00\n\n"
                "🏛️ *Sucursal Norte:*\n"
                "   • Av. Eloy Alfaro N56-10 y Los Álamos\n"
                "   • 🕒 Lunes a Viernes: 08:00 a 18:00 | Sábados: 08:00 a 13:30\n\n"
                "🏛️ *Sucursal Sur:*\n"
                "   • Av. Rodrigo de Chávez y Pedro de Alfaro (Villaflora)\n"
                "   • 🕒 Lunes a Viernes: 08:00 a 18:00 | Sábados: 08:00 a 14:00\n\n"
                "🏛️ *Sucursal Cumbayá:*\n"
                "   • Av. Interoceánica km 11.5 frente a Scala Shopping\n"
                "   • 🕒 Lunes a Sábado: 08:30 a 18:00\n\n"
                "🚚 *Política de Despacho:* Envío GRATIS en Quito en compras mayores a $150. Retiro en tienda inmediato y gratuito.\n\n"
                f"🛒 *Abre la tienda online aquí:* \n{catalog_url}"
            )

        # 8. Asesor Humano
        if q in ["8", "opcion 8", "opción 8"] or any(k in q for k in ["asesor", "humano", "persona", "agente", "vendedor", "hablar con alguien", "soporte", "transferir"]):
            return (
                "👨‍💼 *Conectando con un Asesor de Ferretería Castor...*\n\n"
                "He transferido tu conversación a nuestro equipo técnico en *Chatwoot* para que un asesor humano tome el control del chat y te brinde atención personalizada.\n\n"
                "🕒 *Tiempo estimado de respuesta:* Menos de 60 segundos.\n"
                "📍 *Sede asignada:* Matriz Quito Centro.\n\n"
                "🔘 *Mientras te atienden, puedes:*\n"
                f"👉 Abrir el catálogo interactivo: {catalog_url}\n"
                "👉 Dejarnos tu lista de materiales o requerimientos específicos en este chat.\n\n"
                "_Un asesor te responderá directamente aquí en breve._"
            )

        # Cotizaciones / Presupuestos generales
        if any(k in q for k in ["cotizar", "cotizacion", "cotización", "presupuesto", "lista de materiales"]):
            return (
                "📋 *Cotizaciones de Materiales y Herramientas — Ferretería Castor*\n\n"
                "Con gusto elaboramos tu presupuesto para obra o remodelación:\n\n"
                "1️⃣ *Desde el catálogo:* Agrega tus productos al carrito y finaliza el pedido como cotización.\n"
                "2️⃣ *Por este chat:* Escríbenos la lista detallada de materiales con cantidades y un asesor te responderá con precios formales y descuentos por volumen.\n\n"
                f"👉 *Abrir el catálogo digital:* {catalog_url}\n"
                "👉 *Responde ASESOR* para transferir con un ejecutivo de ventas corporativas."
            )

        # Respuesta general inteligente con menú rápido
        return (
            "¡Con gusto te ayudo! En *Ferretería Castor* 🦫 tenemos en stock herramientas eléctricas, manuales, "
            "materiales de construcción, plomería, pinturas y electricidad con entrega rápida en Quito.\n\n"
            "✨ *Opciones rápidas de atención:*\n"
            "1️⃣ 🛍️ Abrir Catálogo y Carrito en Vivo\n"
            "2️⃣ 📦 Consultar Estado de Pedido (CAST-)\n"
            "3️⃣ ⚡ Herramientas Eléctricas (Makita, DeWalt)\n"
            "4️⃣ 🔨 Herramientas Manuales (Stanley, Truper)\n"
            "5️⃣ 🏗️ Materiales de Construcción (Adelca, Cemento)\n"
            "6️⃣ 🎨 Pinturas y Plomería (Pinturas Unidas, PVC)\n"
            "7️⃣ 🕒 Horarios, Sucursales y Envíos\n"
            "8️⃣ 👨‍💼 Hablar con un Asesor Humano\n\n"
            f"🛒 *Explora y compra en la tienda interactiva:* \n{catalog_url}\n\n"
            "_Escribe un número del 1 al 8 o indícame qué material necesitas._"
        )
