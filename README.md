# 🦫 Ferretería Castor - Ecosistema de Chatbot Multilínea WhatsApp con Catálogo In-App, Meta Flows y Chatwoot

Ecosistema empresarial completo para la automatización de ventas, atención al cliente y gestión de pedidos mediante un **Chatbot Inteligente** conectado a la **API Oficial de Meta WhatsApp Cloud API**, un **Catálogo Interactivo In-App (sin salir de WhatsApp)**, soporte **Multi-Número (hasta 15 líneas)** y centralización omnicanal con **Chatwoot**.

---

## 📋 Índice
1. [Arquitectura General del Sistema](#-arquitectura-general-del-sistema)
2. [Requerimientos y Prerrequisitos](#-requerimientos-y-prerrequisitos)
3. [Componentes y Microservicios (Puertos)](#-componentes-y-microservicios-puertos)
4. [Configuración de Variables de Entorno (`.env`)](#-configuración-de-variables-de-entorno-env)
5. [Experiencia de Catálogo Interactivo In-App](#-experiencia-de-catálogo-interactivo-in-app)
6. [Configuración Multi-Número en Chatwoot (Hasta 15 Líneas)](#-configuración-multi-número-en-chatwoot-hasta-15-líneas)
7. [Coexistencia: Móvil, Web y WhatsApp Business](#-coexistencia-móvil-web-y-whatsapp-business)
8. [Integración con Odoo ERP / CRM](#-integración-con-odoo-erp--crm)
9. [Gestión de Tokens de Meta (Temporal vs Permanente)](#-gestión-de-tokens-de-meta-temporal-vs-permanente)
10. [Guía de Despliegue Rápido (Docker Compose)](#-guía-de-despliegue-rápido-docker-compose)
11. [Comandos Útiles y Testing](#-comandos-útiles-y-testing)

---

## 🏛️ Arquitectura General del Sistema

```mermaid
flowchart TD
    subgraph WhatsApp["📱 Clientes WhatsApp"]
        User["Cliente Móvil / Web"]
    end

    subgraph MetaCloud["☁️ Meta Cloud API"]
        WABA["WABA ID: 980422014478629<br/>Phone ID: 1163688356822125"]
    end

    subgraph Gateway["🚪 Gateway de WhatsApp (Puerto 8095)"]
        GW["Normalizador de Mensajes & Webhooks"]
    end

    subgraph Backend["⚙️ Backend Core FastAPI (Puerto 8085)"]
        Core["Motor de Flujos / Router"]
        CatAPI["API de Catálogo y Pedidos"]
        Handoff["Servicio de Handoff Humano"]
        AI["Flowise / RAG / Qdrant"]
    end

    subgraph Storefront["🛍️ Catálogo Webview In-App (Puerto 8092 / /catalogo)"]
        Store["Buscador en vivo, Fotos, Categorías, Carrito & Checkout"]
    end

    subgraph DataLayer["🗄️ Base de Datos y Caché"]
        PG[("PostgreSQL 15 (5432)")]
        RD[("Redis 7 (6380:6379)")]
        QD[("Qdrant Vector DB (6333)")]
    end

    subgraph Omnichannel["👨‍💼 Central Omnicanal Chatwoot (Puerto 3010)"]
        CW["Chatwoot Web & Mobile App (Inboxes Multi-Número)"]
    end

    User <-->|Mensajes & Catálogo| WABA
    WABA <-->|Webhooks HTTPS| GW
    GW <-->|REST Interno| Core
    Core <--> CatAPI
    Core <--> Handoff
    Core <--> AI
    CatAPI <--> Store
    Core <--> PG
    Core <--> RD
    AI <--> QD
    Handoff <--> CW
    CatAPI -->|Nota Privada de Pedido| CW
```

---

## 💻 Requerimientos y Prerrequisitos

### 1. Software Requerido en el Servidor / Computadora
* **Docker Engine** (v24.0 o superior) y **Docker Compose** (v2.20 o superior).
* **Git** (v2.30 o superior).
* **Túnel HTTPS público** para desarrollo local (**Ngrok** o **Cloudflare Tunnel**) apuntando al puerto `8095` del gateway.

### 2. Credenciales y Cuentas de Meta WhatsApp Cloud API
* Cuenta en [Meta for Developers](https://developers.facebook.com/) con una **App de tipo Business**.
* **WhatsApp Business Account (WABA)** verificada.
* **Número de Teléfono** registrado en Cloud API (con estado `GREEN` / Aprobado).
* **Access Token** con permisos:
  * `whatsapp_business_messaging`
  * `whatsapp_business_management`
* **Verify Token** configurado en los Webhooks de Meta (ej. `ferreteria_token_seguro_2026`).

---

## 🔌 Componentes y Microservicios (Puertos)

| Servicio | Contenedor Docker | Puerto Local | Descripción |
| :--- | :--- | :--- | :--- |
| **Backend Core** | `ferreteria-backend` | `8085:8080` | API FastAPI principal, catálogo, checkout, lógica de bot y handoff. |
| **WhatsApp Gateway** | `ferreteria-whatsapp-gateway-new` | `8095:8090` | Integración y envío oficial de Meta WhatsApp Cloud API. |
| **Catálogo Flutter Web** | `castor-app` | `8092:80` | Aplicación Web Flutter del catálogo de productos y carrito. |
| **Catálogo Webview In-App** | Integrado en Backend | `8085/catalogo` | Webview ligera optimizada para el navegador interno de WhatsApp. |
| **Simulador WhatsApp** | `whatsapp-simulator` | `8090:80` | Interfaz web para probar el bot localmente sin consumir saldo de Meta. |
| **Chatwoot Web** | `chatwoot-web` | `3010:3000` | Bandeja omnicanal para supervisores y asesores humanos. |
| **Chatwoot Worker** | `chatwoot-worker` | - | Procesamiento asíncrono en segundo plano (Sidekiq). |
| **Mock Logistics API** | `mock-logistics-api` | `8081:8080` | API simuladora de rutas, despachos, órdenes y tickets de entrega. |
| **Panel Administrador** | `frontend-admin` | `3001:80` | Panel web React/Vite de administración del sistema. |
| **Panel Asesor** | `frontend-agent` | `5174:80` | Panel web simplificado para agentes de atención. |
| **Flowise AI** | `flowise-new` | `3000:3000` | Motor visual para flujos de agentes LLM y memoria conversacional. |
| **PostgreSQL 15** | `ferreteria-postgres-new` | `5432:5432` | Base de datos relacional de productos, órdenes, usuarios y chats. |
| **Redis 7** | `ferreteria-redis-new` | `6380:6379` | Caché en memoria, carritos activos y limitador de tasa (*rate limit*). |
| **Qdrant Vector DB** | `ferreteria-qdrant-new` | `6333:6333` | Base de datos vectorial para búsqueda semántica y FAQ RAG. |

---

## ⚙️ Configuración de Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz del proyecto tomando como base esta estructura:

```ini
# ==========================================
# Ferreteria Chatbot - Environment Config
# ==========================================
APP_ENV=development
APP_TIMEZONE=America/Guayaquil
LOG_LEVEL=INFO

# Base de Datos y Caché
DATABASE_URL=postgresql+asyncpg://chatbot:change_me@postgres:5432/ferreteria_chatbot
REDIS_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=ferreteria_faq

# Meta WhatsApp Cloud API Oficial
WHATSAPP_PROVIDER=meta
WHATSAPP_ACCESS_TOKEN=EAATsX7XPiBgBS...
WHATSAPP_PHONE_NUMBER_ID=1163688356822125
WHATSAPP_BUSINESS_ACCOUNT_ID=980422014478629
WHATSAPP_VERIFY_TOKEN=ferreteria_token_seguro_2026
WHATSAPP_FLOW_ID=2881017522260067

# URL pública de catálogo para botones In-App
CATALOG_BASE_URL=https://usable-thorn-kabob.ngrok-free.dev

# Integración Omnicanal con Chatwoot
CHATWOOT_BASE_URL=http://chatwoot-web:3000
CHATWOOT_API_TOKEN=tu_token_de_chatwoot
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# Mapeo Multi-Número (Hasta 15 líneas)
WHATSAPP_INBOX_MAPPING={"1163688356822125": {"inbox_id": 1, "sucursal": "Centro", "access_token": "EAATsX7X..."}}

# Seguridad y Logística
INTERNAL_API_KEY=change_me
LOGISTICS_API_BASE_URL=http://mock-logistics-api:8080
ENABLE_WRITE_ACTIONS=true
SESSION_TTL_MINUTES=60
RATE_LIMIT_MESSAGES_PER_MINUTE=60
```

---

## 🛍️ Experiencia de Catálogo Interactivo In-App

El cliente cuenta con dos formas nativas de comprar sin salir de WhatsApp:

### 1. In-App Webview (CTA Interactivo - Recomendado)
* **Cómo funciona:** Al escribir `"Hola"` o `"Catálogo"`, el bot envía un mensaje interactivo con el botón **`[ 🛍️ Abrir Catálogo ]`**.
* **Comportamiento en WhatsApp:** Abre una ventana emergente nativa (*Custom Tab*) sobre el chat con el botón `[ ✕ ]` de cierre.
* **Funcionalidades:**
  * 📸 Fotos reales y especificaciones de productos.
  * 🔍 Buscador en vivo en tiempo real.
  * 🏷️ Filtros de categorías (*Herramientas, Construcción, Pinturas, Plomería, Electricidad*).
  * 🛒 Carrito animado con cálculo automático de subtotal, IVA (15%) y total.
  * 💳 Checkout emergente (Retiro en Sucursal / Envío a Domicilio y Método de Pago).
* **Confirmación:** Al finalizar la compra, se guarda en PostgreSQL `#CAST-2026-XXXX`, se envía el recibo al chat del cliente y se inserta una nota privada en Chatwoot.

### 2. WhatsApp Flows Nativo de Meta
* Soporte nativo para pantallas de flujo de Meta (`type: "flow"` y `flow_id`), permitiendo formularios interactivos con validación directa en la infraestructura de WhatsApp.

---

## 🏢 Configuración Multi-Número en Chatwoot (Hasta 15 Líneas)

Permite centralizar hasta 15 líneas de WhatsApp en un solo panel de control con asesores organizados por sucursal:

1. **Crear Bandejas en Chatwoot:**
   * Entra a [http://localhost:3010](http://localhost:3010) > **Settings > Inboxes > Add Inbox > API Channel**.
   * Asigna un nombre (ej. `WhatsApp Sucursal Centro`).
   * Configura la URL del webhook: `http://whatsapp-gateway:8090/webhooks/chatwoot`.
   * Asigna los agentes para esa línea y guarda. Chatwoot te dará el `Inbox ID` (ej: `1`, `2`, `3`...).

2. **Mapear en `WHATSAPP_INBOX_MAPPING`:**
   En tu archivo `.env`, añade cada `phone_number_id` con su respectivo `inbox_id`:
   ```json
   WHATSAPP_INBOX_MAPPING={
     "1163688356822125": {"inbox_id": 1, "sucursal": "Centro", "access_token": "TOKEN_LINEA_1"},
     "2233445566778899": {"inbox_id": 2, "sucursal": "Norte", "access_token": "TOKEN_LINEA_2"}
   }
   ```

3. **Enrutamiento Inteligente:**
   * El cliente que escribe a la Sucursal Norte va a la Bandeja 2 de Chatwoot.
   * Las respuestas de los asesores desde esa bandeja salen automáticamente desde el número de WhatsApp correspondiente.
   * Cuando el bot interactúa, mantiene el chat en estado `snoozed` para no saturar al equipo.
   * Cuando el cliente pide `[ 👨‍💼 Hablar con asesor ]`, el estado cambia a `open` y notifica a los asesores.

---

## 📲 Coexistencia: Móvil, Web y WhatsApp Business

Para que los dueños de negocio y asesores puedan ver y responder los chats tanto en PC como en sus celulares:

* **Chatwoot Mobile App (iOS / Android):**
  * Descarga la app oficial de **Chatwoot** en Google Play Store o Apple App Store.
  * Inicia sesión con la URL de tu servidor y tus credenciales de agente.
  * Recibe **notificaciones push en tiempo real**, atiende chats de cualquiera de las 15 líneas, escribe notas internas y despacha pedidos desde el celular.
* **Meta Cloud API Coexistence:**
  * Vinculación oficial de dispositivos para que el número de Cloud API coexista con la app WhatsApp Business móvil mediante código QR.

---

## 🏢 Integración con Odoo ERP / CRM

El backend en FastAPI está preparado para conectarse bidireccionalmente con **Odoo Community o Enterprise (v14 a v18 / Odoo.sh)** vía `xmlrpc.client`:

* **Inventario en Vivo:** Consulta stock y precios desde `product.template` y `stock.quant`.
* **Creación de Pedidos:** Al confirmar en WhatsApp, crea cotizaciones/pedidos de venta en `sale.order`.
* **Contactos:** Registro automático de clientes en `res.partner`.
* **Seguimiento:** Consulta de guías y despacho en tiempo real desde `stock.picking`.

---

## 🔑 Gestión de Tokens de Meta (Temporal vs Permanente)

| Tipo de Token | Duración | Uso Recomendado | Dónde se Genera |
| :--- | :--- | :--- | :--- |
| **Token Temporal** | 24 Horas | Pruebas rápidas de desarrollo | *Meta Developers > WhatsApp > API Setup* |
| **Token Permanente** | **Nunca Expira** | **Producción** | *Meta Business Suite > Configuración del Negocio > Usuarios del Sistema (System Users) > Generar Token Permanente con permisos `whatsapp_business_messaging` y `whatsapp_business_management`*. |

> [!IMPORTANT]
> Para producción, genera siempre un token mediante **Usuario del Sistema** para evitar que el bot se detenga por expiración de sesión.

---

## 🚀 Guía de Despliegue Rápido (Docker Compose)

### 1. Clonar el repositorio
```bash
git clone https://github.com/HeuristicLog/chatbot_agente_ferreteria01.git
cd chatbot_agente_ferreteria01
```

### 2. Configurar entorno
```bash
cp .env.example .env
# Edita el archivo .env con tus credenciales de Meta y Chatwoot
```

### 3. Levantar todos los contenedores
```bash
docker compose up -d --build
```

### 4. Iniciar túnel Ngrok (para webhooks de Meta en local)
```bash
ngrok http 8095 --domain=tu-dominio-ngrok.ngrok-free.dev
```

### 5. Suscribir Webhooks de Meta
```bash
# Ejecutar suscripción en el contenedor backend
docker exec ferreteria-backend python -c "
import urllib.request, os
TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WABA = os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID')
req = urllib.request.Request(f'https://graph.facebook.com/v20.0/{WABA}/subscribed_apps', headers={'Authorization': f'Bearer {TOKEN}'}, data=b'', method='POST')
print(urllib.request.urlopen(req).read().decode())
"
```

---

## 🧪 Comandos Útiles y Testing

### Probar Salud de Todos los Servicios
```bash
docker exec ferreteria-backend python -c "
import urllib.request
for name, url in [('Backend', 'http://localhost:8080/health'), ('Gateway', 'http://whatsapp-gateway:8090/health'), ('Logistics', 'http://mock-logistics-api:8080/health'), ('Castor App', 'http://castor-app:80/'), ('Chatwoot', 'http://chatwoot-web:3000/')]:
    try:
        print(f'✅ {name}: {urllib.request.urlopen(url, timeout=5).status}')
    except Exception as e:
        print(f'❌ {name}: {e}')
"
```

### Enviar Mensaje de Prueba al WhatsApp del Cliente
```bash
docker exec ferreteria-backend python -c "
import asyncio
from app.services import interactive_flow_service as flows
asyncio.run(flows.send_welcome_menu('593984407038', 'change_me'))
"
```

---

## 👥 Equipo y Licencia
* **Desarrollado por:** Equipo HeuristicLog / Ferretería Castor
* **Licencia:** Propietaria / Uso Comercial
