# Arquitectura Estructurada y Análisis de Beneficios: Chatwoot Cloud vs. Community
## Caso de Estudio Técnico: Torre de Control para 25 Números — Mega Ferretería Bonilla

---

## 1. El Objetivo del Sistema

La empresa requiere una **Torre de Control de 25 Entradas (Números de WhatsApp)** donde:
1. **El Backend Propio** es el motor inteligente: atiende con el bot **Castor**, abre el **Catálogo Webview**, gestiona el **Carrito de Compras** y calcula precios/stock.
2. **Chatwoot** es la pantalla de auditoría y analítica: permite a **Gerencia** supervisar el flujo de conversaciones y consultar métricas de rendimiento de las 25 entradas.
3. No hay necesidad de licencias masivas de vendedores si el objetivo es supervisión gerencial centralizada.

---

## 2. Diagramas de Arquitectura: Modelo Cloud vs. Modelo Servidor Propio

### Arquitectura 1: Modelo Nube (Chatwoot Cloud SaaS - Startups o Business)
```mermaid
flowchart LR
    subgraph Clientes["25 Líneas de WhatsApp"]
        W1["WhatsApp 1 (+593...)"]
        W2["WhatsApp 2 (+593...)"]
        W25["WhatsApp 25 (+593...)"]
    end

    subgraph BackendLocal["Tu Servidor / Backend"]
        BOT["🤖 Bot Castor\n🛍️ Catálogo\n🛒 Carrito"]
    end

    subgraph CloudChatwoot["Servidores de Chatwoot (EE.UU. / Europa)"]
        API_TOKEN["🔐 Token de API (De Pago)"]
        INBOXES["📥 25 Bandejas en app.chatwoot.com"]
        METRICS_CLOUD["📊 Métricas Nube (Retención 1 - 2 años)"]
    end

    subgraph Gerente["Gerencia"]
        DASH_CLOUD["💻 Acceso a app.chatwoot.com"]
    end

    W1 & W2 & W25 <-->|Webhooks| BOT
    BOT <-->|Llamadas HTTP a la Nube\n(Requiere plan $19 o $39)| API_TOKEN
    API_TOKEN --> INBOXES
    INBOXES --> METRICS_CLOUD
    METRICS_CLOUD --> DASH_CLOUD
```

---

### Arquitectura 2: Modelo Servidor Propio (Chatwoot Community Docker) — *Recomendado*
```mermaid
flowchart LR
    subgraph Clientes2["25 Líneas de WhatsApp"]
        WA1["WhatsApp 1 (+593...)"]
        WA2["WhatsApp 2 (+593...)"]
        WA25["WhatsApp 25 (+593...)"]
    end

    subgraph ServidorEmpresa["Tu Servidor Privado (Todo en Red Local Docker)"]
        BOT2["🤖 Bot Castor\n🛍️ Catálogo y Carrito\n(FastAPI / Redis)"]
        EVO["📱 Pasarela Multi-Línea QR\n(Evolution API)"]
        CW_LOCAL["📥 Chatwoot Community\n- 25 Bandejas\n- Token de API $0 Libre\n- Retención Infinita en PostgreSQL"]
        METRICS_LOCAL["📊 Tablero de Métricas\n(Tiempos de respuesta y resolución)"]
    end

    subgraph Gerente2["Gerencia"]
        DASH_LOCAL["💻 Acceso Seguro HTTPS\n(chat.megaferreteriabonilla.com)"]
    end

    WA1 & WA2 & WA25 <--> EVO
    EVO <--> BOT2
    BOT2 <-->|Conexión directa interna (0 ms)| CW_LOCAL
    CW_LOCAL --> METRICS_LOCAL
    METRICS_LOCAL --> DASH_LOCAL
```

---

## 3. Desglose Estructurado de Beneficios por Versión

### Opción 1: Plan Hacker ($0 / mes en la Nube)

| Aspecto | Evaluación Técnica |
| :--- | :--- |
| **Costo Mensual** | **$0 USD** |
| **Arquitectura** | Incompatible con el proyecto. |
| **Beneficios que ofrece** | • Ningún costo de software.<br>• Útil exclusivamente para probar un widget de chat en una página web. |
| **Limitaciones críticas para la empresa** | • **Cero canales de WhatsApp:** No permite conectar ningún número de WhatsApp.<br>• **Máximo 2 agentes y 500 chats/mes:** Se bloquea al superar 500 mensajes.<br>• **Token de API bloqueado:** Tu backend no puede sincronizar datos con Chatwoot.<br>• **Retención de solo 30 días:** Borra el historial cada mes. |
| **Veredicto para la Ferretería** | ❌ **Completamente descartado.** No permite WhatsApp ni conexión por API. |

---

### Opción 2: Plan Startups ($19 / agente / mes en la Nube)

| Aspecto | Evaluación Técnica |
| :--- | :--- |
| **Costo Mensual** | **$19 USD / mes** *(1 usuario Gerencia)* o **$475 USD / mes** *(25 usuarios)* |
| **Arquitectura** | Híbrida: Tu backend procesa la lógica y envía eventos a los servidores externos de Chatwoot. |
| **Beneficios que aporta a la empresa** | • **Desbloquea los Tokens de API:** Permite que tu backend inyecte conversaciones a las 25 entradas.<br>• **25 Entradas de WhatsApp:** Puedes crear las 25 bandejas para tus números.<br>• **Conversaciones ilimitadas:** Sin límite de 500 chats.<br>• **Cero mantenimiento:** Chatwoot se encarga de que la web de `app.chatwoot.com` esté siempre en línea.<br>• **Help Center:** Te da una página de preguntas frecuentes alojada en su nube. |
| **Limitaciones frente a la ferretería** | • **Sin división por Equipos (Teams):** No puedes agrupar las 25 entradas en categorías como "Sucursales Sierra", "Sucursales Costa" o "Mayoristas".<br>• **Sin reglas de automatización:** No puedes programar macros automáticas dentro de Chatwoot.<br>• **Retención de datos limitada a 1 año:** Al año se purga el historial de conversaciones antiguas. |
| **Veredicto para la Ferretería** | ⚠️ **Viable únicamente si no quieres administrar ningún servidor** y solo registras a 1 usuario Gerente ($19/mes). |

---

### Opción 3: Plan Business ($39 / agente / mes en la Nube)

| Aspecto | Evaluación Técnica |
| :--- | :--- |
| **Costo Mensual** | **$39 USD / mes** *(1 usuario Gerencia)* o **$975 USD / mes** *(25 usuarios)* |
| **Arquitectura** | Híbrida gestionada con funciones corporativas completas en la nube de Chatwoot. |
| **Beneficios que aporta a la empresa** | • **División por Equipos (Teams):** Permite organizar las 25 entradas por sucursales y departamentos con total claridad.<br>• **Reglas de Automatización avanzadas:** Permite crear flujos internos (ej. si una conversación lleva 10 minutos sin responder, enviar alerta por email al Gerente).<br>• **Canales de Voz:** Soporte para telefonía IP web.<br>• **Retención de datos por 2 años:** El historial se preserva el doble de tiempo que en Startups.<br>• **Captain AI (500 créditos):** Asistente de redacción para agentes. |
| **Limitaciones frente a la ferretería** | • **Pagas por funciones redundantes:** El bot con IA, catálogo, cotizador y flete ya están construidos en tu Backend; pagar $39/mes por la IA de Chatwoot es pagar dos veces por lo mismo.<br>• **Costo acumulado:** Pagar $468 USD al año (1 usuario) o $11,700 USD al año (25 usuarios). |
| **Veredicto para la Ferretería** | ⚠️ **Excelente software, pero redundante y sobrecosteado** para lo que la ferretería ya tiene resuelto en su backend. |

---

### Opción 4: Chatwoot Community (Self-Hosted en Servidor VPS Propio)

| Aspecto | Evaluación Técnica |
| :--- | :--- |
| **Costo Mensual** | **$0 USD en software** *(Solo el costo del servidor VPS: ~$25 a $35 USD/mes total)* |
| **Arquitectura** | **100% On-Premise / Soberanía Total:** Todo el sistema (Chatbot, Catálogo, Pasarela QR, Chatwoot, Base de Datos) vive en la misma máquina privada. |
| **Beneficios que aporta a la empresa** | 1. **Cero Límites de Usuarios y Entradas:** Puedes crear las 25 entradas hoy, y si mañana quieres darle acceso a 30 vendedores, el costo sigue siendo **$0**.<br>2. **Latencia Cero (Velocidad Inmediata):** Tu backend y Chatwoot están en la misma red interna de Docker (`ferreteria-net`). Las conversaciones entran al instante sin viajar a servidores de EE.UU.<br>3. **Tokens de API 100% Desbloqueados y Gratuitos:** Sin planes de pago para conectar webhooks, el catálogo webview o herramientas externas.<br>4. **Retención de Datos Eterna:** Todo el historial de clientes, teléfonos, cotizaciones y ventas queda para siempre en tu base PostgreSQL. Nunca se borra.<br>5. **Seguridad y Privacidad Comercial:** La información confidencial de clientes, precios de ferretería y transacciones no está en la nube pública de nadie. |
| **Requerimiento** | Requiere mantener un servidor en la nube (un VPS de 4 vCPUs y 8 GB de RAM por ~$25/mes) con copias de seguridad automáticas. |
| **Veredicto para la Ferretería** | 🏆 **LA MEJOR ARQUITECTURA TÉCNICA Y FINANCIERA.** Da el 100% del control a Gerencia sin pagar licencias mensuales por software. |

---

## 4. Matriz Comparativa de Beneficios

```
+------------------------------------+------------+--------------+--------------+-----------------------+
| Funcionalidad / Beneficio          | Hacker $0  | Startups $19 | Business $39 | Community Self-Hosted |
+------------------------------------+------------+--------------+--------------+-----------------------+
| 25 Números (Entradas WhatsApp)     | ❌ No       | ✔️ Sí         | ✔️ Sí         | ✔️ Sí (Ilimitadas)    |
| Costo con 1 Usuario Gerente        | $0         | $19 / mes    | $39 / mes    | $0 en licencias       |
| Costo con 25 Asesores              | ❌ Bloqueado| $475 / mes   | $975 / mes   | $0 en licencias       |
| Acceso a Tokens de API             | ❌ Bloqueado| ✔️ Con pago   | ✔️ Con pago   | ✔️ 100% Libre         |
| Integración con Bot y Catálogo     | ❌ Imposible| ✔️ Sí         | ✔️ Sí         | ✔️ Nativa en red local|
| Retención de Historial de Clientes | 30 días    | 1 año        | 2 años       | ♾️ Permanente          |
| Módulo de Informes y Métricas      | Básico     | Completo     | Avanzado     | Completo              |
| Conexión por Código QR (Evolution) | ❌ No       | ⚠️ Difícil    | ⚠️ Difícil    | ✔️ Totalmente integrada|
+------------------------------------+------------+--------------+--------------+-----------------------+
```

---

## 5. Dictamen y Conclusión Ejecutiva

1. **Si la prioridad es NO instalar ni administrar servidores:**  
   El **Plan Startups ($19/mes para 1 solo usuario Gerencia)** te permite tener las 25 entradas en la nube y ver las métricas pagando solo **$19 al mes**.
2. **Si la prioridad es RENTABILIDAD, VELOCIDAD Y PROPIEDAD DE LOS DATOS:**  
   La versión **Community en servidor propio** es imbatible:
   - Ya la tienes funcionando en Docker.
   - Tiene el conector QR listo y el conector de API listo.
   - Tu backend ya está integrado.
   - Te ahorra miles de dólares al año y no te restringe nada.
