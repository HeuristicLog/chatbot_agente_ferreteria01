"""
LangChain Automotive AI Service — Native Code Alternative to Flowise
Handles natural language questions, vehicle recommendations, financing calculations,
and conversational memory using LangChain and Python natively.
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any

from app.config import settings

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

Directrices de Respuesta:
1. Responde de forma concisa, educada y persuasiva con emojis automotrices.
2. Si el cliente pregunta por cuotas o presupuestos, brinda ejemplos de cuotas y sugiere simular el crédito en la vitrina.
3. Si el cliente pide hablar con una persona o tiene un reclamo, indícale amablemente que puedes transferirlo con un asesor humano en Chatwoot.
4. Mantén las respuestas breves y directas para WhatsApp (máximo 3 párrafos).
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
        Motor de inferencia semántica en código Python puro.
        Responde con precisión sobre modelos, cotizaciones, garantías y sedes.
        """
        q = question.lower()
        ngrok_url = os.getenv("CATALOG_BASE_URL", "https://usable-thorn-kabob.ngrok-free.dev")
        clean_phone = phone.replace("+", "").replace(" ", "").strip()
        catalog_url = f"{ngrok_url}/catalogo-autos?phone={clean_phone}&biz=15556724304&ngrok-skip-browser-warning=1"

        # D-Max / Pickups
        if any(k in q for k in ["dmax", "d-max", "camioneta", "pickup", "4x4", "hilux", "poer"]):
            return (
                "🛻 *Camionetas 4x4 en AutoEcuador Motors 2026:*\n\n"
                "• *Chevrolet D-Max High Country 3.0L Diésel 4x4:* $34,990 USD\n"
                "  💵 Entrada: $6,998 | Cuota estimada: $585/mes (60m)\n\n"
                "• *Toyota Hilux Doble Cabina 2.4L 4x4:* $38,490 USD\n"
                "  💵 Entrada: $7,698 | Cuota estimada: $645/mes (60m)\n\n"
                "• *Great Wall Poer Luxury 2.0L Turbo 4x4:* $28,990 USD\n"
                "  💵 Entrada: $5,798 | Cuota estimada: $485/mes (60m)\n\n"
                "Todas con tracción 4x4 con reductora, listas para entrega inmediata en todo Ecuador."
            )

        # Híbridos / Pico y Placa
        if any(k in q for k in ["hibrido", "híbrido", "pico y placa", "yaris", "electrico", "eléctrico"]):
            return (
                "⚡ *Toyota Yaris Cross Híbrido 2026 (Cero Pico y Placa)* 🌿\n\n"
                "• 💰 *Precio con IVA (15%):* $27,990 USD\n"
                "• 💵 *Entrada (20%):* $5,598 | Cuota: $465/mes (60m)\n"
                "• 🚀 *Ventaja Ecuador:* **Exento de Pico y Placa en Quito todos los días**.\n"
                "• ⛽ *Rendimiento:* Hasta 85 km por galón (auto-recargable, no necesita enchufe).\n"
                "• 🛡️ *Garantía de batería:* 8 años o 160.000 km."
            )

        # SUVs Familiares
        if any(k in q for k in ["suv", "suvs", "sportage", "tucson", "tracker", "sonet", "tiggo", "familiar"]):
            return (
                "🚙 *SUVs Familiares 2026 en AutoEcuador Motors:*\n\n"
                "• *Chery Tiggo 4 Pro Luxury Turbo:* $18,490 USD (Cuota: $310/mes)\n"
                "• *Kia Sonet LX 1.5L:* $19,990 USD (Cuota: $335/mes)\n"
                "• *Chevrolet Tracker RS 1.2L Turbo:* $22,990 USD (Cuota: $385/mes)\n"
                "• *Kia Sportage LX 2.0L Automático:* $26,490 USD (Cuota: $445/mes)\n"
                "• *Hyundai Tucson NX4 Advance:* $29,990 USD (Cuota: $505/mes)\n\n"
                "Todos con 6 airbags, cámara de reversa y amplio maletero para viajes por Ecuador."
            )

        # Crédito / Financiamiento / Requisitos
        if any(k in q for k in ["credito", "crédito", "financiamiento", "requisitos", "banco", "entrada", "cuota"]):
            return (
                "💳 *Financiamiento Vehicular AutoEcuador Motors:*\n\n"
                "• 📊 *Entradas:* Desde el 20% del valor del auto.\n"
                "• ⏳ *Plazos:* De 12 a 60 meses con cuotas fijas en USD.\n"
                "• 🏦 *Bancos y Cooperativas Aliadas:* Banco Pichincha, Produbanco, Banco Guayaquil, Coac Policía Nacional.\n"
                "• 📋 *Requisitos Básicos:* Cédula de identidad, planilla de servicios básicos y últimos 3 roles de pago o declaraciones de IVA (RUC/RIMPE).\n\n"
                "Aprobamos tu solicitud de crédito en 24 a 48 horas sin garante."
            )

        # Retoma / Auto usado
        if any(k in q for k in ["retoma", "usado", "parte de pago", "tasar", "avaluo", "avalúo"]):
            return (
                "🔄 *Plan Retoma AutoEcuador Motors:*\n\n"
                "¡Recibimos tu auto usado de cualquier marca o año como parte de pago!\n\n"
                "1. Realizamos una inspección mecánica y avalúo transparente al precio de mercado.\n"
                "2. El monto acordado se abona directamente como entrada de tu auto 0 km.\n"
                "3. Nosotros gestionamos todos los trámites legales y de notaría."
            )

        # Test Drive
        if any(k in q for k in ["test drive", "testdrive", "prueba", "manejo"]):
            return (
                "🏎️ *Prueba de Manejo (Test Drive) 100% Gratuita:*\n\n"
                "Puedes probar cualquiera de nuestros modelos:\n"
                "• 🏠 *A domicilio:* Llevamos el auto a tu casa u oficina.\n"
                "• 📍 *En Showroom:* En Quito Centro (Av. 10 de Agosto) o Guayaquil.\n\n"
                "Solo necesitas tu licencia de conducir vigente y cédula para coordinar fecha y hora."
            )

        # Horarios y Ubicaciones
        if any(k in q for k in ["horario", "ubicacion", "ubicación", "donde estan", "dónde están", "direccion", "dirección"]):
            return (
                "📍 *Salas de Exhibición y Showrooms AutoEcuador Motors:*\n\n"
                "• *Quito Centro (Matriz):* Av. 10 de Agosto y Orellana\n"
                "  🕒 Lunes a Sábado: 8:30 a 18:30 | Domingos: 10:00 a 14:00\n\n"
                "• *Guayaquil Norte:* Av. Juan Tanca Marengo km 4.5\n"
                "  🕒 Lunes a Sábado: 9:00 a 19:00\n\n"
                "• *Cuenca:* Av. España y Huayna Cápac\n"
                "  🕒 Lunes a Viernes: 8:30 a 18:00"
            )

        # Respuesta general inteligente
        return (
            "¡Con gusto te asesoro! En *AutoEcuador Motors* 🇪🇨 disponemos de Camionetas 4x4, SUVs familiares "
            "y modelos Híbridos 2026 exentos de Pico y Placa.\n\n"
            "Podemos ayudarte con cotizaciones inmediatas, simulación de crédito con entradas desde el 20%, "
            "plan retoma de tu auto usado o agendar un Test Drive sin costo.\n\n"
            "¿Sobre qué modelo o rango de presupuesto te gustaría recibir información?"
        )
