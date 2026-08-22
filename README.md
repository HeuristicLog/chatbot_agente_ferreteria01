# Ferretería Castor - Ecosistema de Chatbot Multilínea de WhatsApp con Chatwoot

Este proyecto es un ecosistema completo para automatizar la atención al cliente mediante un chatbot inteligente conectado a la API oficial de WhatsApp Business y centralizado con **Chatwoot** como plataforma omnicanal para los asesores humanos.

El flujo principal garantiza que **el primer contacto del cliente siempre sea atendido por el chatbot**. Cuando el cliente solicita un asesor humano, la conversación se transfiere de forma transparente a la bandeja de entrada de Chatwoot correspondiente a la sucursal del cliente, cambiando el estado del chat a abierto para alertar a los agentes.

---

## 🚀 Arquitectura y Funcionamiento

El ecosistema está compuesto por los siguientes servicios principales (orquestados en Docker):
*   **`backend` (FastAPI)**: El núcleo lógico que maneja la máquina de estados de los flujos del bot, almacena el historial local, realiza la integración con Flowise (para respuestas con IA) y coordina la lógica de transferencia humana.
*   **`whatsapp-gateway` (FastAPI)**: Capa de abstracción para la API oficial de Meta. Recibe los webhooks entrantes de Meta, formatea los payloads de mensajes (textos, botones interactivos y listas) y realiza las peticiones salientes de forma segura.
*   **`chatwoot`**: Plataforma omnicanal centralizada. Permite a los supervisores controlar múltiples líneas de WhatsApp oficiales desde una única pantalla, y a los asesores responder directamente desde allí.
*   **`redis`**: Utilizado para limitar la tasa de mensajes (rate limiting), asegurar la idempotencia de los webhooks mediante identificadores únicos de mensajes, y almacenar el estado de las sesiones de interacción.
*   **`postgres`**: Base de datos relacional para guardar el historial de conversaciones, usuarios de sistema, asesores asignados a sucursales y registros de auditoría de handoff.

---

## 🔑 Configuración del Token de WhatsApp y Duración

Meta (Facebook Developers) ofrece dos tipos de tokens para realizar peticiones a la API de WhatsApp Business Cloud:

### 1. Token de Acceso Temporal (Pruebas)
*   **Duración**: Vence exactamente **24 horas** después de su generación.
*   **Uso**: Ideal para desarrollo y pruebas rápidas en local.
*   **Recarga**: Se debe ingresar manualmente a la consola de [Meta for Developers](https://developers.facebook.com/), seleccionar tu aplicación, ir a **WhatsApp > Configuración de la API** y presionar el botón "Generar token temporal". Este nuevo token debe ser copiado y reemplazado en la variable `WHATSAPP_ACCESS_TOKEN` de tu archivo `.env`.

### 2. Token de Acceso Permanente (Producción)
*   **Duración**: **No expira nunca** (a menos que se revoque manualmente).
*   **Uso**: Obligatorio para entornos de producción.
*   **Proceso de Generación Paso a Paso**:
    1.  Entra al **Administrador Comercial de Meta** (Business Manager) en `https://business.facebook.com/`.
    2.  Ve a **Configuración del negocio > Usuarios del sistema**.
    3.  Crea un nuevo usuario del sistema (con rol de **Administrador**).
    4.  Una vez creado, haz clic en **Asignar activos** (Assign Assets), selecciona la categoría **Cuentas de WhatsApp** (WhatsApp Business Account), elige tu cuenta oficial y activa el permiso completo de **Administrar cuenta** (Manage Account). Guarda los cambios.
    5.  Regresa a la lista de usuarios del sistema, selecciona el usuario administrador creado y haz clic en el botón **Generar nuevo token** (Generate New Token).
    6.  Selecciona tu cuenta de WhatsApp en la lista desplegable y marca los siguientes permisos:
        *   `whatsapp_business_messaging` (Permite enviar y recibir mensajes)
        *   `whatsapp_business_management` (Permite administrar plantillas y configuraciones)
    7.  Haz clic en **Generar token**. Copia este token largo de manera segura. **Este token es permanente y nunca se vencerá.**
    8.  Pega este token en tu archivo `.env` en la variable `WHATSAPP_ACCESS_TOKEN` (y dentro del mapping multilínea si corresponde).

---

## 📱 Configuración Multilínea y Bandejas de Chatwoot (`WHATSAPP_INBOX_MAPPING`)

El chatbot tiene soporte nativo para **múltiples líneas de WhatsApp Business oficiales al mismo tiempo**, cada una mapeada a su propio inbox de Chatwoot y a su respectiva sucursal física.

En el archivo `.env`, puedes configurar este comportamiento mediante la variable de entorno `WHATSAPP_INBOX_MAPPING`:

```ini
WHATSAPP_INBOX_MAPPING={"1163688356822125": {"inbox_id": 1, "sucursal": "Centro", "access_token": "EAATsX7X..."}}
```

### Explicación del Formato JSON:
Cada clave representa un `phone_number_id` oficial de Meta. El valor es un objeto que contiene:
*   `inbox_id`: El ID de la bandeja de entrada correspondiente en Chatwoot (donde se crearán los chats).
*   `sucursal`: El nombre de la sucursal física (ej. `"Centro"`, `"Norte"`, `"Sur"`), que servirá para la asignación y derivación interna de asesores.
*   `access_token`: El token de Meta específico para esa línea de WhatsApp (puede ser diferente para cada número comercial).

### Flujo de Trabajo en Detalle:
1.  **Primer Mensaje del Cliente**: El cliente escribe a uno de tus números de WhatsApp oficiales.
2.  **Sincronización en Chatwoot (Fondo Silencioso)**: El backend detecta el número oficial al que escribió el cliente, busca su mapeo en `WHATSAPP_INBOX_MAPPING`, crea el contacto y la conversación en la bandeja correcta (`inbox_id`) de Chatwoot, y publica el mensaje entrante.
3.  **Estado Pospuesto (`snoozed`)**: Mientras el cliente interactúe con el chatbot, el backend configura el estado de la conversación en Chatwoot como `snoozed` (Pospuesta) o `bot` de forma automática. De esta forma, el chat **no interrumpe ni notifica a los asesores humanos**, pero los supervisores pueden monitorear el chat en vivo si lo desean.
4.  **Respuestas del Bot**: Cada respuesta, botón interactivo o menú desplegable que el bot le envía al cliente es enviada automáticamente a Chatwoot en tiempo real como mensaje de salida (`outgoing`).
5.  **Solicitud de Asesor (Handoff)**: Cuando el cliente presiona "Hablar con asesor":
    *   El backend local busca asesores activos asignados a esa sucursal específica.
    *   El backend envía una llamada de API a Chatwoot para cambiar el estado de la conversación a **`open` (Abierta)**.
    *   Se publica una **nota interna (privada, de color amarillo)** con el resumen y motivo del handoff. Esto alerta de inmediato al asesor humano.
6.  **Intervención Humana**: El asesor responde al cliente directamente desde la consola web o móvil de Chatwoot. El webhook intercepta la respuesta de salida, realiza una búsqueda reversa en el mapping para encontrar el `phone_number_id` y `access_token` correspondientes, y retransmite el mensaje vía Meta. El cliente lo recibe en su celular desde el número de la sucursal.
7.  **Resolución**: Cuando el asesor marca la conversación como **Resuelta** (`resolved`) en Chatwoot, el backend recibe el evento, limpia la sesión en Redis, reactiva el chatbot Castor localmente y le envía un mensaje de confirmación al cliente por WhatsApp.

---

## 🛠️ Despliegue con Docker Compose

### 1. Requisitos
*   Docker y Docker Compose instalados.
*   Un túnel público activo (ej. ngrok) apuntando al puerto `8085` (backend) y `8095` (gateway) para que Meta pueda enviar los Webhooks a tu servidor local.

### 2. Configurar variables de entorno
Crea el archivo `.env` en la raíz (puedes copiar el `.env.example`) y configura los tokens de Meta, URLs de Chatwoot e inboxes:

```ini
APP_ENV=development
APP_TIMEZONE=America/Guayaquil

# Tokens por defecto de WhatsApp
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=tu_token_de_verificacion_webhook
WHATSAPP_ACCESS_TOKEN=tu_meta_token_de_acceso
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id

# Mapeo de múltiples líneas oficiales a bandejas de Chatwoot
WHATSAPP_INBOX_MAPPING={"1163688356822125": {"inbox_id": 1, "sucursal": "Centro", "access_token": "tu_meta_token"}}

# Integración con Chatwoot
CHATWOOT_BASE_URL=http://chatwoot-web:3000
CHATWOOT_API_TOKEN=naCTc3dv6qfvbhfwVar9CmDA
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

### 3. Levantar contenedores
Para levantar todos los contenedores y dependencias, ejecuta:
```bash
docker compose up -d
```

### 4. Reiniciar componentes tras cambios en configuración
Si realizas modificaciones en el archivo `.env` o en el código fuente, reinicia los contenedores involucrados para aplicar los cambios:
```bash
docker compose restart backend whatsapp-gateway
```

### 5. Configurar el Webhook en la consola de Meta Developers
*   **Callback URL**: `https://<tu-subdominio-ngrok>/webhooks/whatsapp`
*   **Verify Token**: El valor configurado en `WHATSAPP_VERIFY_TOKEN` (ej. `ferreteria_verify_token_2026`).
*   **Suscripciones a campos**: Suscríbete a los campos `messages` dentro de los eventos de Webhooks de WhatsApp de tu aplicación de Meta Developers.
