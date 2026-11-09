import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("chatbot-api.qa-auditor")

class ConversationQAAuditor:
    """
    Motor de Auditoría de Calidad Conversacional en 9 Dimensiones
    Evalúa conversaciones de asesores humanos y del bot en WhatsApp y Chatwoot.
    """

    RUBRIC_WEIGHTS = {
        "saludo_y_presentacion": 10,       # Saludo ameno + Nombre del asesor
        "relevo_y_sucursal": 10,           # Presentación al tomar chat + Sucursal
        "calidad_cotizacion": 15,          # Precios claros, desglose IVA, evitar fuga de venta
        "respuestas_rapidas": 10,          # Uso de atajos rápidos y agilidad
        "abordaje_y_actitud": 15,          # Proactividad comercial, alternativas similares
        "claridad_y_ortografia": 10,       # Buena redacción y ortografía
        "disponibilidad_y_sustitutos": 10, # Verificación rápida de stock + recomendación de otra marca
        "presentacion_producto": 10,       # Envío de fotos adecuadas y características técnicas
        "cierre_y_logistica": 10           # Entrega/retiro, tiempos, formas de pago y despedida
    }

    @classmethod
    def evaluate_conversation(cls, messages: List[Dict[str, Any]], advisor_name: Optional[str] = None, sucursal: Optional[str] = None) -> Dict[str, Any]:
        """
        Evalúa el hilo de mensajes de una conversación y genera un scoring detallado.
        messages: Lista de diccionarios con keys: 'content', 'message_type' (0: user, 1: agent/bot), 'created_at'
        """
        advisor_messages = []
        user_messages = []
        full_text_advisor = ""
        full_text_user = ""

        for m in messages:
            content = str(m.get("content") or "").strip()
            # message_type 1 = Outgoing (Asesor / Bot), 0 = Incoming (Cliente)
            m_type = m.get("message_type")
            if m_type == 1 or m.get("sender_type") == "User":
                advisor_messages.append({"text": content, "time": m.get("created_at")})
                full_text_advisor += " " + content
            else:
                user_messages.append({"text": content, "time": m.get("created_at")})
                full_text_user += " " + content

        adv_clean = full_text_advisor.lower()
        user_clean = full_text_user.lower()

        scores = {}
        feedback = {}

        # ── 1. Saludo, Sentimiento y Presentación de Nombre (10 pts) ──
        saludo_score = 0
        has_saludo = any(k in adv_clean for k in ["hola", "buen", "buenos días", "buenas tardes", "buenas noches", "un gusto", "bienvenido"])
        has_nombre = False
        detected_name = advisor_name or ""
        
        # Buscar patrones como "mi nombre es ...", "le atiende ...", "soy ..."
        name_match = re.search(r"(?:mi nombre es|le saluda|soy|le atiende|te saluda|atendido por)\s+([a-zA-ZáéíóúÁÉÍÓÚñÑ]+)", adv_clean)
        if name_match:
            has_nombre = True
            detected_name = name_match.group(1).capitalize()
        elif advisor_name and advisor_name.lower() in adv_clean:
            has_nombre = True

        if has_saludo and has_nombre:
            saludo_score = 10
            feedback["saludo_y_presentacion"] = f"Excelente saludo ameno y formal presentación de nombre ({detected_name or 'Asesor'})."
        elif has_saludo:
            saludo_score = 6
            feedback["saludo_y_presentacion"] = "Saludó cordialmente pero no mencionó explícitamente su nombre de asesor."
        else:
            saludo_score = 2
            feedback["saludo_y_presentacion"] = "Respuesta fría sin protocolo de saludo ni presentación inicial."
        scores["saludo_y_presentacion"] = saludo_score

        # ── 2. Relevo, Cambio de Asesor y Sucursal (10 pts) ──
        relevo_score = 10
        has_transfer = any(k in adv_clean or k in user_clean for k in ["transfer", "comunicar con", "otra persona", "sucursal", "relevo", "compañer"])
        has_sucursal = any(s in adv_clean for s in ["centro", "norte", "sur", "cumbayá", "cumbaya", "matriz", "bodega"])

        if has_transfer:
            if has_sucursal and has_nombre:
                relevo_score = 10
                feedback["relevo_y_sucursal"] = "Correcto relevo: se presentó con nombre y especificó sucursal de atención."
            elif has_sucursal or has_nombre:
                relevo_score = 7
                feedback["relevo_y_sucursal"] = "Relevo aceptable, pero omitió indicar sucursal o nombre completo."
            else:
                relevo_score = 4
                feedback["relevo_y_sucursal"] = "Al transferir la conversación no se identificó ni aclaró la sucursal asignada."
        else:
            feedback["relevo_y_sucursal"] = "Atención directa sin necesidad de transferencia a otro asesor."
        scores["relevo_y_sucursal"] = relevo_score

        # ── 3. Calidad de Cotización & Prevención de Fuga de Venta (15 pts) ──
        coti_score = 0
        has_price = bool(re.search(r"(\$\s*\d+|\d+\s*dólares|\d+,\d{2}|\d+\.\d{2}|usd)", adv_clean))
        has_tax = any(k in adv_clean for k in ["iva", "15%", "impuesto", "subtotal", "total"])
        has_proforma = any(k in adv_clean for k in ["proforma", "cotización", "cotizacion", "so-2026", "op-", "orden"])

        if has_price and has_tax:
            coti_score = 15
            feedback["calidad_cotizacion"] = "Cotización impecable con precio claro y desglose reglamentario del IVA (15%)."
        elif has_price:
            coti_score = 11
            feedback["calidad_cotizacion"] = "Entregó precio claro, se recomienda especificar siempre si incluye IVA para evitar malentendidos."
        elif has_proforma:
            coti_score = 8
            feedback["calidad_cotizacion"] = "Hizo referencia a la proforma/orden sin detallar el valor en el texto."
        else:
            coti_score = 5
            feedback["calidad_cotizacion"] = "No se estructuró una cotización formal durante la interacción."
        scores["calidad_cotizacion"] = coti_score

        # ── 4. Agilidad y Respuestas Rápidas (10 pts) ──
        rapidas_score = 10
        has_canned = any(k in adv_clean for k in ["horario", "lunes a viernes", "07:30 a 18:00", "catálogo", "catalogo", "transferencia", "pago"])
        if has_canned:
            rapidas_score = 10
            feedback["respuestas_rapidas"] = "Uso eficiente de respuestas rápidas y datos estandarizados."
        else:
            rapidas_score = 7
            feedback["respuestas_rapidas"] = "Mensajes manuales, se sugiere usar atajos de respuestas rápidas para mayor agilidad."
        scores["respuestas_rapidas"] = rapidas_score

        # ── 5. Abordaje Comercial & Actitud Consultiva (15 pts) ──
        abordaje_score = 0
        has_options = any(k in adv_clean for k in ["también disponemos", "otra opción", "similar", "alternativa", "te puedo recomendar", "le recomiendo", "para qué trabajo", "qué modelo"])
        has_politeness = any(k in adv_clean for k in ["con gusto", "un placer", "a la orden", "estamos para servirle", "con mucho gusto"])

        if has_options and has_politeness:
            abordaje_score = 15
            feedback["abordaje_y_actitud"] = "Excelente venta consultiva: indagó necesidades, ofreció alternativas y mostró gran calidez."
        elif has_options or has_politeness:
            abordaje_score = 11
            feedback["abordaje_y_actitud"] = "Buena actitud; se puede mejorar ofreciendo productos complementarios o sustitutos."
        else:
            abordaje_score = 6
            feedback["abordaje_y_actitud"] = "Atención reactiva; solo respondió lo puntual sin asesorar activamente al cliente."
        scores["abordaje_y_actitud"] = abordaje_score

        # ── 6. Claridad y Ortografía (10 pts) ──
        ortografia_score = 10
        # Detección de fallas comunes informales
        informal_errors = ["k ", "q ", "xq", "pq", "ola ", "aki", "ke "]
        error_count = sum(1 for e in informal_errors if e in adv_clean)
        
        if error_count == 0:
            ortografia_score = 10
            feedback["claridad_y_ortografia"] = "Redacción pulcra, profesional y sin abreviaturas informales de chat."
        elif error_count <= 2:
            ortografia_score = 7
            feedback["claridad_y_ortografia"] = "Comprensible, pero contiene abreviaturas informales ('q', 'xq'). Cuidar imagen corporativa."
        else:
            ortografia_score = 4
            feedback["claridad_y_ortografia"] = "Se detectaron múltiples errores ortográficos o abreviaturas inadecuadas."
        scores["claridad_y_ortografia"] = ortografia_score

        # ── 7. Verificación de Stock y Recomendación de Sustitutos (10 pts) ──
        stock_score = 0
        has_stock_check = any(k in adv_clean for k in ["disponemos", "tenemos en bodega", "stock", "agotado", "no disponemos", "disponible"])
        has_brand_substitute = any(k in adv_clean for k in ["makita", "dewalt", "bosch", "adelca", "holcim", "selvalegre", "plastigama", "truper"])

        if has_stock_check and has_brand_substitute:
            stock_score = 10
            feedback["disponibilidad_y_sustitutos"] = "Excelente: verificó disponibilidad y ofreció marcas reconocidas del catálogo."
        elif has_stock_check:
            stock_score = 8
            feedback["disponibilidad_y_sustitutos"] = "Verificó stock; si un ítem no existe, recuerde ofrecer una marca alternativa."
        else:
            stock_score = 5
            feedback["disponibilidad_y_sustitutos"] = "No se evidenció confirmación explícita de existencias en bodega."
        scores["disponibilidad_y_sustitutos"] = stock_score

        # ── 8. Presentación de Producto & Fichas / Fotos (10 pts) ──
        presentacion_score = 0
        has_photo_link = any(k in adv_clean for k in ["foto", "imagen", "fotografía", "catálogo", "catalogo", "características", "ficha técnica", "potencia", "780w", "12mm"])
        if has_photo_link:
            presentacion_score = 10
            feedback["presentacion_producto"] = "Correcto envío de imágenes, especificaciones técnicas o enlace a la vitrina webview."
        else:
            presentacion_score = 6
            feedback["presentacion_producto"] = "Solo mencionó el producto con texto simple sin fotos ni ficha técnica de apoyo."
        scores["presentacion_producto"] = presentacion_score

        # ── 9. Protocolo de Cierre, Logística y Formas de Pago (10 pts) ──
        cierre_score = 0
        has_delivery = any(k in adv_clean for k in ["entrega", "envío", "envio", "retiro", "local", "bodega", "tiempo de entrega"])
        has_payment_methods = any(k in adv_clean for k in ["transferencia", "tarjeta", "crédito", "credito", "efectivo", "cheque", "pago"])
        has_farewell = any(k in adv_clean for k in ["gracias por preferirnos", "un buen día", "excelente tarde", "a la orden", "hasta luego", "quedamos atentos"])

        cierre_matches = sum([has_delivery, has_payment_methods, has_farewell])
        if cierre_matches >= 2:
            cierre_score = 10
            feedback["cierre_y_logistica"] = "Cierre comercial impecable: acordó logística, formas de pago y despedida formal."
        elif cierre_matches == 1:
            cierre_score = 7
            feedback["cierre_y_logistica"] = "Cierre parcial: definió entrega o pago, pero faltó completar los datos logísticos y despedida."
        else:
            cierre_score = 3
            feedback["cierre_y_logistica"] = "Conversación abierta o inconclusa sin acordar entrega ni formas de pago."
        scores["cierre_y_logistica"] = cierre_score

        # ── Cálculo del Puntaje Total Ponderado (0 a 100) ──
        total_score = sum(scores.values())

        if total_score >= 88:
            qa_level = "Sobresaliente (A+)"
            qa_tag = "qa-sobresaliente"
            color_badge = "emerald"
        elif total_score >= 75:
            qa_level = "Aprobado (A)"
            qa_tag = "qa-aprobado"
            color_badge = "blue"
        elif total_score >= 60:
            qa_level = "Requiere Mejora (B)"
            qa_tag = "qa-mejora"
            color_badge = "amber"
        else:
            qa_level = "Crítico / Auditoría Requerida (C)"
            qa_tag = "qa-critico"
            color_badge = "rose"

        return {
            "total_score": total_score,
            "max_score": 100,
            "qa_level": qa_level,
            "qa_tag": qa_tag,
            "color_badge": color_badge,
            "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "advisor_name": detected_name or "Asesor Comercial",
            "scores": scores,
            "feedback": feedback
        }

    @classmethod
    def format_chatwoot_internal_note(cls, audit_result: Dict[str, Any]) -> str:
        """Genera el texto de la nota interna privada para Chatwoot."""
        score = audit_result["total_score"]
        level = audit_result["qa_level"]
        adv = audit_result["advisor_name"]
        sc = audit_result["scores"]
        fb = audit_result["feedback"]

        note = (
            f"📋 *AUDITORÍA DE CALIDAD CONVERSACIONAL (QA - 9 DIMENSIONES)*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Asesor Evaluado:* {adv}\n"
            f"🏆 *Calificación Total:* {score}/100 — *{level}*\n"
            f"📅 *Fecha de Evaluación:* {audit_result['evaluated_at']}\n\n"
            f"📊 *DESGLOSE POR DIMENSIÓN:*\n"
            f"1️⃣ *Saludo & Sentimiento:* {sc['saludo_y_presentacion']}/10\n"
            f"   └ {fb['saludo_y_presentacion']}\n\n"
            f"2️⃣ *Relevo & Sucursal:* {sc['relevo_y_sucursal']}/10\n"
            f"   └ {fb['relevo_y_sucursal']}\n\n"
            f"3️⃣ *Calidad de Cotización:* {sc['calidad_cotizacion']}/15\n"
            f"   └ {fb['calidad_cotizacion']}\n\n"
            f"4️⃣ *Respuestas Rápidas:* {sc['respuestas_rapidas']}/10\n"
            f"   └ {fb['respuestas_rapidas']}\n\n"
            f"5️⃣ *Abordaje & Actitud:* {sc['abordaje_y_actitud']}/15\n"
            f"   └ {fb['abordaje_y_actitud']}\n\n"
            f"6️⃣ *Claridad & Ortografía:* {sc['claridad_y_ortografia']}/10\n"
            f"   └ {fb['claridad_y_ortografia']}\n\n"
            f"7️⃣ *Stock & Alternativas:* {sc['disponibilidad_y_sustitutos']}/10\n"
            f"   └ {fb['disponibilidad_y_sustitutos']}\n\n"
            f"8️⃣ *Fotos & Ficha Técnica:* {sc['presentacion_producto']}/10\n"
            f"   └ {fb['presentacion_producto']}\n\n"
            f"9️⃣ *Cierre, Logística & Pago:* {sc['cierre_y_logistica']}/10\n"
            f"   └ {fb['cierre_y_logistica']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 *Acción del Supervisor:* "
            + ("Felicitar al asesor por excelente estándar de servicio." if score >= 80 else "Revisar protocolos de cotización, stock y alternativas de venta.")
        )
        return note
