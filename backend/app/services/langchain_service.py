"""
LangChain Automotive AI Service — Native Code Alternative to Flowise
Handles natural language questions, vehicle recommendations, financing calculations,
and conversational memory using LangChain and Python natively.
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

# System prompt for AutoEcuador Motors sales consultant
SYSTEM_PROMPT = """Eres Alex, el asesor comercial ejecutivo oficial de AutoEcuador Motors (Ecuador, 2026).
Tu misión es asesorar a los clientes con amabilidad, profesionalismo y enfoque comercial en vehículos nuevos y seminuevos.

Información Oficial del Concesionario:
• Sedes y Showrooms:
  - Quito Centro (Matriz): Av. 10 de Agosto y Orellana (Lunes a Sábado 8:30 a 18:30, Domingos 10:00 a 14:00)
  - Guayaquil Norte: Av. Juan Tanca Marengo km 4.5 (Lunes a Sábado 9:00 a 19:00)
  - Cuenca: Av. España y Huayna Cápac (Lunes a Viernes 8:30 a 18:00)
• Modelos Destacados 2026:
  - Chevrolet D-Max High Country 3.0L Diésel 4x4: $34,990 USD (Entrada: $6,998 | Cuota: $585/mes)
  - Toyota Hilux Doble Cabina 2.4L Diésel 4x4: $38,490 USD (Entrada: $7,698 | Cuota: $645/mes)
  - Great Wall Poer Luxury 2.0L Turbo 4x4: $28,990 USD (Entrada: $5,798 | Cuota: $485/mes)
  - Toyota Yaris Cross Híbrido 1.5L: $27,990 USD (Entrada: $5,598 | Cuota: $465/mes | CERO PICO Y PLACA en Quito)
  - Chevrolet Tracker RS 1.2L Turbo: $22,990 USD (Entrada: $4,598 | Cuota: $385/mes)
  - Kia Sportage LX 2.0L Automático: $26,490 USD (Entrada: $5,298 | Cuota: $445/mes)
  - Hyundai Tucson NX4 Advance: $29,990 USD (Entrada: $5,998 | Cuota: $505/mes)
  - Chery Tiggo 4 Pro Luxury Turbo: $18,490 USD (Entrada: $3,698 | Cuota: $310/mes)
  - Kia Sonet LX 1.5L: $19,990 USD (Entrada: $3,998 | Cuota: $335/mes)
• Planes y Servicios:
  - Financiamiento directo y bancario con plazos de 12 a 60 meses y entradas desde el 20%.
  - Plan Retoma: recibimos vehículos usados de cualquier marca o año como parte de pago.
  - Test Drive gratuito a domicilio o en concesionario.
  - Vitrina virtual / Catálogo digital sin salir de WhatsApp.

Directrices de Respuesta (Interactivas y No Texto Plano):
1. NUNCA respondas con párrafos largos o texto plano monótono. Usa viñetas claras, negritas, subtítulos y emojis automotrices.
2. Al final de CADA respuesta, ofrece siempre opciones interactivas de acción rápida numeradas (ej: 1️⃣ Simular cuotas, 2️⃣ Ver vitrina, 3️⃣ Hablar con asesor).
3. Invita al cliente a abrir la vitrina virtual interactiva dentro de WhatsApp: https://usable-thorn-kabob.ngrok-free.dev/catalogo-autos
4. Si el cliente pregunta por cuotas o presupuestos, brinda ejemplos de cuotas reales con entradas del 20% y plazos a 60 meses.
5. Si el cliente pide hablar con una persona, transferir o quejarse, indícale amablemente que un asesor ejecutivo humano lo atenderá de inmediato por este chat.
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
        Procesa la consulta del cliente mediante LangChain o motor semántico nativo.
        """
        clean_q = question.strip()
        if not clean_q:
            return "¡Hola! ¿En qué vehículo o servicio de AutoEcuador Motors podemos asesorarte hoy? 🚗✨"

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

        # 2. Motor Semántico Nativo AutoEcuador Motors (100% Código Python)
        native_reply = await self._native_semantic_engine(clean_q, phone)
        await self._save_chat_history(session_id, clean_q, native_reply)
        return native_reply

    async def _native_semantic_engine(self, question: str, phone: str) -> str:
        """
        Motor de inferencia semántica y conversacional en código Python puro.
        Genera respuestas interactivas, estructuradas y visualmente atractivas
        con opciones de navegación rápida y enlace a la vitrina webview sin salir de WhatsApp.
        """
        q = question.lower().strip()
        ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
        clean_phone = phone.replace("+", "").replace(" ", "").strip()
        if not clean_phone:
            clean_phone = "593988921136"
        catalog_url = f"{ngrok_url}/catalogo-autos?phone={clean_phone}&biz=15556724304&ngrok-skip-browser-warning=1"

        # Saludos / Menú principal / Opciones
        if any(k == q or q.startswith(k) for k in ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "menu", "menú", "inicio", "start", "opciones", "ayuda"]):
            return (
                "🚘 *¡Bienvenido a AutoEcuador Motors 2026!* 🇪🇨\n"
                "Soy *Alex*, tu asesor comercial inteligente. Te ayudo a cotizar y estrenar tu próximo vehículo con financiamiento inmediato.\n\n"
                "✨ *Selecciona una opción rápida o escribe tu consulta:*\n\n"
                "1️⃣ 🛻 *Camionetas 4x4* (D-Max, Hilux, Poer)\n"
                "2️⃣ 🌿 *Híbridos Cero Pico y Placa* (Yaris Cross)\n"
                "3️⃣ 🚙 *SUVs Familiares* (Tracker, Sportage, Tucson, Tiggo)\n"
                "4️⃣ 📱 *Vitrina Virtual Interactiva* (Explora sin salir de WhatsApp)\n"
                "5️⃣ 💳 *Simulador de Crédito* (Entrada desde 20% y 60 meses)\n"
                "6️⃣ 🔄 *Plan Retoma* (Tu auto usado como entrada)\n"
                "7️⃣ 👨‍💼 *Hablar con un asesor comercial humano*\n\n"
                f"🌐 *Abre el catálogo interactivo aquí:* \n{catalog_url}\n\n"
                "_Responde con el número (1 al 7) o pregúntame directamente lo que necesites._"
            )

        # Manejo de números interactivos (1 al 7) y consultas temáticas
        if q in ["1", "opcion 1", "opción 1"] or any(k in q for k in ["camionetas", "camioneta", "pickups", "pickup", "4x4", "dmax", "d-max", "hilux", "poer"]):
            return (
                "🛻 *Camionetas 4x4 — AutoEcuador Motors 2026*\n"
                "Tracción 4x4 con reductora, alta durabilidad y entrega inmediata en todo Ecuador:\n\n"
                "🔹 *Chevrolet D-Max High Country 3.0L Diésel 4x4*\n"
                "   • Precio: *$34,990 USD*\n"
                "   • Entrada (20%): *$6,998 USD* | Cuota: *$585/mes* (60m)\n\n"
                "🔹 *Toyota Hilux Doble Cabina 2.4L 4x4*\n"
                "   • Precio: *$38,490 USD*\n"
                "   • Entrada (20%): *$7,698 USD* | Cuota: *$645/mes* (60m)\n\n"
                "🔹 *Great Wall Poer Luxury 2.0L Turbo 4x4*\n"
                "   • Precio: *$28,990 USD*\n"
                "   • Entrada (20%): *$5,798 USD* | Cuota: *$485/mes* (60m)\n\n"
                f"📱 *Ver fotos y fichas 4x4 en la Vitrina Virtual:* \n{catalog_url}&cat=pickups\n\n"
                "🔘 *¿Qué deseas hacer ahora?*\n"
                "👉 Responde *D-MAX*, *HILUX* o *POER* para ver la ficha detallada.\n"
                "👉 Responde *CREDITO* para simular tu financiamiento.\n"
                "👉 Responde *ASESOR* para hablar con nuestro equipo comercial."
            )

        if q in ["2", "opcion 2", "opción 2"] or any(k in q for k in ["hibrido", "hibridos", "híbrido", "híbridos", "pico y placa", "yaris", "electrico", "eléctrico"]):
            return (
                "🌿 *Toyota Yaris Cross Híbrido 2026 — ¡Cero Pico y Placa!* ⚡\n"
                "El SUV híbrido auto-recargable más eficiente de Ecuador, sin necesidad de cables ni enchufes:\n\n"
                "💰 *Precio con IVA (15%):* $27,990 USD\n"
                "💵 *Entrada sugerida (20%):* $5,598 USD\n"
                "📅 *Cuota fija estimada:* $465/mes (Plazo 60 meses)\n\n"
                "🌟 *Ventajas Exclusivas en Ecuador:*\n"
                "• 🚀 *Exento de Pico y Placa en Quito* todos los días del año.\n"
                "• ⛽ *Rendimiento sobresaliente:* Hasta 85 km por galón.\n"
                "• 🛡️ *Garantía de batería híbrida:* 8 años o 160.000 km respaldada por Toyota.\n\n"
                f"📱 *Simula tu crédito y mira la galería 360° en la Vitrina:* \n{catalog_url}&cat=hibridos\n\n"
                "🔘 *Siguientes pasos:*\n"
                "👉 Responde *TEST DRIVE* para agendar tu prueba de manejo gratuita.\n"
                "👉 Responde *REQUISITOS* para conocer la documentación bancaria.\n"
                "👉 Responde *ASESOR* para coordinar con un vendedor."
            )

        if q in ["3", "opcion 3", "opción 3"] or any(k in q for k in ["suv", "suvs", "familiar", "familiares", "tracker", "sportage", "tucson", "tiggo", "sonet"]):
            return (
                "🚙 *SUVs Familiares 2026 — Espacio, Confort y Seguridad*\n"
                "Equipadas con 6 airbags, cámara de reversa, pantalla táctil y amplio maletero:\n\n"
                "🔸 *Chery Tiggo 4 Pro Luxury Turbo:* *$18,490 USD* | Cuota: *$310/mes*\n"
                "🔸 *Kia Sonet LX 1.5L:* *$19,990 USD* | Cuota: *$335/mes*\n"
                "🔸 *Chevrolet Tracker RS 1.2L Turbo:* *$22,990 USD* | Cuota: *$385/mes*\n"
                "🔸 *Kia Sportage LX 2.0L Automático:* *$26,490 USD* | Cuota: *$445/mes*\n"
                "🔸 *Hyundai Tucson NX4 Advance:* *$29,990 USD* | Cuota: *$505/mes*\n\n"
                f"📱 *Compara todas las SUVs en la Vitrina Virtual:* \n{catalog_url}&cat=suvs\n\n"
                "🔘 *¿Cuál te llama la atención?*\n"
                "👉 Escribe el modelo (ej: *TRACKER* o *SPORTAGE*) para detalles.\n"
                "👉 Responde *ASESOR* para atención personalizada."
            )

        if q in ["4", "opcion 4", "opción 4"] or any(k in q for k in ["vitrina", "catalogo", "catálogo", "pagina", "página", "web", "webview"]):
            return (
                "📱 *Vitrina Virtual Interactiva — AutoEcuador Motors 2026*\n\n"
                "Abre nuestra vitrina directamente dentro de WhatsApp sin salir de la app. Allí podrás:\n"
                "1️⃣ Ver fotos en alta definición de todos los modelos 2026.\n"
                "2️⃣ Mover la barra de entrada y plazo en el simulador de cuotas en vivo.\n"
                "3️⃣ Enviar tu solicitud formal de cotización con un solo toque.\n\n"
                f"👉 *Toca este enlace para abrir la vitrina ahora:* \n{catalog_url}\n\n"
                "_¡Pruébalo ahora y calcula la cuota exacta para tu presupuesto!_"
            )

        if q in ["5", "opcion 5", "opción 5"] or any(k in q for k in ["credito", "crédito", "financiamiento", "requisitos", "banco", "entrada", "cuota", "interes", "interés"]):
            return (
                "💳 *Financiamiento y Crédito Automotriz AutoEcuador*\n"
                "Planes flexibles con entidades aliadas (Banco Pichincha, Produbanco, Banco Guayaquil, Coac Policía Nacional):\n\n"
                "📊 *Condiciones Financieras:*\n"
                "• *Entrada mínima:* Desde el 20% del valor comercial.\n"
                "• *Plazos de pago:* 12, 24, 36, 48 o 60 meses con cuota fija.\n"
                "• *Tasa preferencial:* Aprobación en 24 a 48 horas sin garante.\n\n"
                "📋 *Requisitos de Crédito:*\n"
                "1. Cédula de identidad y papeleta de votación.\n"
                "2. Planilla de servicios básicos (luz o agua).\n"
                "3. Últimos 3 roles de pago (dependientes) o 3 declaraciones de IVA (independientes/RUC).\n\n"
                f"📱 *Calcula tu cuota fija en tiempo real en la Vitrina:* \n{catalog_url}\n\n"
                "🔘 *Opciones:*\n"
                "👉 Responde *ASESOR* para pre-aprobar tu crédito hoy mismo.\n"
                "👉 Responde *RETOMA* si tienes un auto usado para dar como entrada."
            )

        if q in ["6", "opcion 6", "opción 6"] or any(k in q for k in ["retoma", "usado", "parte de pago", "tasar", "avaluo", "avalúo"]):
            return (
                "🔄 *Plan Retoma AutoEcuador Motors — ¡Tu Auto Usado Vale Más!*\n"
                "Aceptamos tu vehículo usado de cualquier marca o año como parte de pago de tu 0 km:\n\n"
                "1️⃣ *Inspección y Avalúo:* Revisión técnica en nuestras sedes o a domicilio.\n"
                "2️⃣ *Precio Justo de Mercado:* Valoramos tu auto con transparencia inmediata.\n"
                "3️⃣ *Abono Directo:* El valor acordado se aplica como entrada de tu auto nuevo.\n"
                "4️⃣ *Cero Trámites:* Gestionamos traspasos notariales y matriculación por ti.\n\n"
                f"📱 *Elige tu próximo auto en la Vitrina Virtual:* \n{catalog_url}\n\n"
                "👉 *¿Qué auto tienes actualmente?* Responde con la marca, modelo y año (ej: *Chevrolet Sail 2018*) y coordinamos tu avalúo con un asesor."
            )

        if q in ["7", "opcion 7", "opción 7"] or any(k in q for k in ["asesor", "humano", "persona", "agente", "vendedor", "hablar con alguien"]):
            return (
                "👨‍💼 *Conectando con un Asesor Comercial Ejecutivo...*\n\n"
                "He notificado a nuestro equipo en *Chatwoot Cloud* para que un asesor humano tome el control de este chat y te brinde atención personalizada.\n\n"
                "🕒 *Tiempo estimado de respuesta:* Menos de 60 segundos.\n"
                "📍 *Sucursal principal:* AutoEcuador Motors Quito Centro (Av. 10 de Agosto y Orellana).\n\n"
                "🔘 *Mientras esperas, puedes interactuar:*\n"
                f"👉 Tocar aquí para explorar la vitrina virtual: {catalog_url}\n"
                "👉 Escribir tus preguntas específicas sobre modelo o financiamiento.\n\n"
                "_Un asesor te escribirá directamente aquí en breve._"
            )

        if any(k in q for k in ["test drive", "testdrive", "prueba", "manejo"]):
            return (
                "🏎️ *Agenda tu Test Drive Oficial 100% Gratuito*\n"
                "Siente la potencia y confort del vehículo antes de comprar:\n\n"
                "• 🏠 *A Domicilio:* Llevamos el auto a tu casa u oficina (Quito y Valles).\n"
                "• 📍 *En Showroom:* Quito Centro (Av. 10 de Agosto) o Guayaquil Norte.\n\n"
                "📋 *Solo necesitas:* Licencia de conducir vigente y cédula.\n\n"
                "👉 *¿Qué modelo deseas probar y en qué ciudad estás?* Escríbenos y coordinamos tu cita de inmediato."
            )

        if any(k in q for k in ["horario", "ubicacion", "ubicación", "donde estan", "dónde están", "direccion", "dirección"]):
            return (
                "📍 *Salas de Exhibición y Showrooms AutoEcuador Motors:*\n\n"
                "🏛️ *Quito Centro (Matriz):*\n"
                "   • Av. 10 de Agosto y Orellana\n"
                "   • 🕒 Lun-Sáb: 8:30 a 18:30 | Dom: 10:00 a 14:00\n\n"
                "🏛️ *Guayaquil Norte:*\n"
                "   • Av. Juan Tanca Marengo km 4.5\n"
                "   • 🕒 Lun-Sáb: 9:00 a 19:00\n\n"
                "🏛️ *Cuenca:*\n"
                "   • Av. España y Huayna Cápac\n"
                "   • 🕒 Lun-Vie: 8:30 a 18:00\n\n"
                f"📱 *Explora los autos disponibles en cada showroom:* \n{catalog_url}"
            )

        # Respuesta general inteligente con menú rápido
        return (
            "¡Con gusto te asesoro! En *AutoEcuador Motors* 🇪🇨 contamos con Camionetas 4x4, SUVs familiares "
            "y modelos Híbridos 2026 exentos de Pico y Placa.\n\n"
            "✨ *Opciones rápidas para explorar:*\n"
            "1️⃣ Camionetas 4x4 (D-Max, Hilux, Poer)\n"
            "2️⃣ Híbridos Cero Pico y Placa (Yaris Cross)\n"
            "3️⃣ SUVs Familiares (Tracker, Sportage, Tucson)\n"
            "4️⃣ Abrir Vitrina Virtual Interactiva\n"
            "5️⃣ Simular Crédito (20% entrada)\n"
            "6️⃣ Plan Retoma de Usados\n"
            "7️⃣ Hablar con un asesor humano\n\n"
            f"📱 *Abre la vitrina sin salir de WhatsApp:* \n{catalog_url}\n\n"
            "_Escribe un número del 1 al 7 o indícame qué modelo te interesa._"
        )
