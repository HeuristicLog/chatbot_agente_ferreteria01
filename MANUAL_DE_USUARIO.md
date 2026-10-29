# MANUAL DE USUARIO Y OPERACIÓN
## Sistema de Atención WhatsApp con IA (LangChain) y Chatwoot Cloud
### Concesionario AutoEcuador Motors 2026
> **Rama Oficial:** `KevinAG23/langchain-chatwoot-interactive-suite`  
> **Licencia:** 1 Asiento Humano ($19 USD/mes) | Hasta 25 Números WhatsApp a Costo $0  
> **Estado:** 100% Verificado y Aprobado en Producción

---

## 1. Introducción y Bienvenida

¡Bienvenido al manual operativo de tu nuevo sistema de atención comercial!

Este sistema combina la inteligencia artificial automotriz de **Alex** (asesor comercial virtual) con una potente mesa de ayuda en **Chatwoot Cloud**. Con esta herramienta, tu concesionario puede:
- **Atender clientes las 24 horas del día, los 7 días de la semana** de forma inmediata.
- **Cotizar vehículos 2026** (Camionetas 4x4, SUVs familiares, Híbridos Cero Pico y Placa) con cálculo de cuotas y entradas del 20%.
- **Abrir una vitrina virtual interactiva** directamente dentro de WhatsApp sin que el cliente salga de la aplicación.
- **Supervisar y gestionar hasta 25 números telefónicos de WhatsApp** desde un único panel centralizado en Chatwoot pagando **una sola licencia de $19 USD al mes**.
- **Medir el tiempo de respuesta y calificar a cada cliente** en tiempo real con métricas automotrices visibles en pantalla.

---

## 2. El Modelo de Licencia: 25 Números por $19 USD/mes

### ¿Por qué NO necesitas pagar licencias adicionales?
En la mayoría de plataformas tradicionales te cobran por cada número de WhatsApp que conectes. En nuestra arquitectura:
1. **Chatwoot Cloud cobra por Asesor Humano (Usuario), NO por número ni por mensaje.**
   - Tu plan actual cuenta con **1 agente comercial** (`Christianb`) a un costo fijo de **$19 USD al mes**.
2. **Las Bandejas de Entrada (Inboxes) son 100% ILIMITADAS y GRATUITAS.**
   - Puedes crear 1, 5, 10 o hasta **25 bandejas de entrada** en Chatwoot Cloud a costo \$0.
3. **Evolution API permite múltiples instancias de WhatsApp a costo $0.**
   - En tu servidor se ejecutan las instancias de WhatsApp (`sucursal_1`, `sucursal_2`... `sucursal_25`) sin pagar ninguna tarifa por número.

**Resultado:** El asesor único (`Christianb`) atiende y controla las conversaciones de los 25 números desde una sola pantalla por **$19 USD en total al mes**.

---

## 3. Cómo Conectar un Nuevo Número de WhatsApp (Paso a Paso con Código QR)

Puedes conectar hasta 25 números de WhatsApp (por ejemplo: matriz Quito, sucursal Guayaquil, sucursal Cuenca, o líneas personales de vendedores).

### Paso 1: Crear la nueva instancia en el sistema
Abre tu terminal de comandos (PowerShell) o utiliza la interfaz web de Evolution API:

```powershell
# Ejemplo: Crear la instancia para la sucursal de Guayaquil
Invoke-RestMethod -Uri "http://localhost:8082/instance/create" `
  -Headers @{"apikey"="ferreteria_evolution_key_2026"} `
  -Method Post -ContentType "application/json" `
  -Body '{"instanceName":"sucursal_guayaquil","token":"token_guayaquil","qrcode":true}'
```

### Paso 2: Escanear el Código QR con tu teléfono móvil
1. Toma el teléfono celular que tiene el número de WhatsApp de esa sucursal.
2. Abre la app de **WhatsApp** en el teléfono.
3. Toca los **tres puntos verticales** (Android) o **Configuración** (iPhone).
4. Selecciona **Dispositivos vinculados** ➔ **Vincular un dispositivo**.
5. Abre la página para ver el código QR en tu navegador web:
   ```
   http://localhost:8082/instance/connect/sucursal_guayaquil
   ```
   *(También puedes abrir el archivo `escanear_qr.html` incluido en el proyecto).*
6. Apunta la cámara del teléfono hacia la pantalla y escanea el código QR.

### Paso 3: Confirmación de conexión
En 3 a 5 segundos, la pantalla mostrará:
```json
{"status": "open", "ownerJid": "593XXXXXXXXX@s.whatsapp.net"}
```
¡Listo! El nuevo número ya está conectado al bot inteligente.

> [!TIP]
> **Coexistencia con WhatsApp Web:** Puedes seguir usando WhatsApp en el teléfono móvil y en WhatsApp Web en tu computadora al mismo tiempo. El bot trabaja como un dispositivo vinculado adicional sin interferir en tu uso diario.

---

## 4. Cómo Generar la Entrada / Bandeja en Chatwoot (Para cada uno de los 25 números)

Para que los mensajes de cada número se organicen de forma ordenada en Chatwoot:

### Paso 1: Iniciar sesión en Chatwoot Cloud
1. Ingresa a [https://app.chatwoot.com](https://app.chatwoot.com).
2. Inicia sesión con el correo oficial: `christianb@heuristiclog.com`.

### Paso 2: Añadir una nueva Bandeja de Entrada (Inbox)
1. En el menú lateral izquierdo, haz clic en el ícono de engranaje (**Ajustes** / **Settings**).
2. Haz clic en **Bandejas de entrada** (Inboxes).
3. Presiona el botón azul **"Añadir bandeja de entrada"** (Add Inbox).
4. En las opciones de canales, selecciona **Canal API** (API Channel).

### Paso 3: Configurar los datos de la bandeja
* **Nombre del canal:** Escribe el nombre descriptivo del número (ejemplos):
  - `WhatsApp - Sucursal Quito Centro`
  - `WhatsApp - Sucursal Guayaquil Norte`
  - `WhatsApp - Sucursal Cuenca`
  - `WhatsApp - Campaña Facebook D-Max`
* **URL del Webhook (Webhook URL):** Escribe la URL pública segura de tu túnel:
  ```
  https://usable-thorn-kabob.ngrok-free.dev/webhooks/chatwoot
  ```
* Presiona **"Crear canal API"**.

### Paso 4: Asignar al Asesor Comercial
1. En la siguiente pantalla, marca la casilla del asesor `Christianb`.
2. Presiona **"Añadir agentes"**.
3. ¡Listo! La nueva entrada ya está creada y visible en la lista de bandejas.

---

## 5. Control Operativo de Conversaciones (Día a Día del Asesor)

### 5.1 Cómo atiende el Bot Automático (Modo IA)
Cuando un cliente escribe por primera vez o consulta información:
- El bot **Alex** responde de forma inmediata (en menos de 1 segundo).
- Si el cliente pregunta precios, cuotas o requisitos, el bot le brinda la información oficial de AutoEcuador Motors 2026.
- En Chatwoot, tú puedes ver toda la conversación en vivo sin necesidad de intervenir.

### 5.2 Cómo tomar el control manual de un cliente (Pausa del Bot)
El bot se **pausa automáticamente** en cualquiera de estos dos casos:
1. **El cliente pide hablar con una persona:** Al presionar *"👨‍💼 Hablar con Asesor"* o escribir *"asesor"*, el bot le notifica amablemente que un asesor humano lo atenderá y se silencia.
2. **El asesor escribe un mensaje:** En el instante en que tú escribes un mensaje al cliente (sea desde la web de Chatwoot o desde tu app móvil de WhatsApp), el sistema detecta que un humano tomó la conversación y **el bot no vuelve a responder**.

### 5.3 Cómo responder al cliente desde Chatwoot
1. Entra a la conversación en [https://app.chatwoot.com](https://app.chatwoot.com).
2. En la parte inferior, escribe tu respuesta en el cuadro de texto.
3. Presiona **Enviar** (o tecla Enter).
4. El mensaje llegará instantáneamente al WhatsApp del cliente con la línea de la sucursal correspondiente.

### 5.4 Cómo enviar Fotos, Cotizaciones en PDF y Audios
* En el cuadro de texto de Chatwoot, haz clic en el **ícono de clip (adjunto)**.
* Selecciona la foto del vehículo, la ficha técnica en PDF o graba un audio.
* Presiona **Enviar**.
* El cliente recibirá el archivo multimedia directamente en su chat de WhatsApp.

### 5.5 Cómo escribir desde tu celular sin romper nada
Si estás en la calle o en el patio de autos y respondes al cliente directamente desde tu WhatsApp del celular:
* Nuestro sistema detecta automáticamente tu mensaje.
* **Sube el mensaje a Chatwoot** para que quede en el historial.
* **Pone al bot en pausa** para que no interrumpa tu negociación.
* **Bloquea duplicados**, garantizando que tu mensaje no se reenvíe dos veces.

### 5.6 Cómo finalizar la atención y reactivar el Bot
Cuando termines de atender la consulta del cliente:
1. En la parte superior derecha de la conversación en Chatwoot, haz clic en el botón verde **"Resolver"** (Resolve).
2. El sistema enviará un mensaje de confirmación al cliente:
   > *"✅ Atención al cliente finalizada. El asesor comercial virtual Alex de AutoEcuador Motors 🇪🇨 vuelve a estar activo. Escribe hola para ver el menú o explorar vehículos."*
3. A partir de ese momento, si el cliente vuelve a escribir en el futuro, el bot con IA lo atenderá nuevamente desde cero.

---

## 6. Métricas en Tiempo Real para Cada Número y Entrada

En cada conversación de Chatwoot dispones de un panel de inteligencia comercial en la barra lateral derecha.

### 6.1 Dónde ver las Métricas de un Cliente
1. Abre cualquier conversación en Chatwoot.
2. Mira la columna derecha bajo la sección **"Información de la conversación"** y **"Atributos de la conversación"** (Custom Attributes).

```
┌────────────────────────────────────────────────────────┐
│ ATRIBUTOS DE LA CONVERSACIÓN                           │
├──────────────────────────┬─────────────────────────────┤
│ Tiempo de Respuesta (FRT)│ 24 seg (frt-rapido)         │
│ Flujo / Intención        │ Camionetas 4x4              │
│ Modelo de Interés        │ Chevrolet D-Max 3.0L Diésel │
│ Sucursal Asignada        │ Quito Centro                │
│ Entrada Estimada (USD)   │ $6,998 USD                  │
│ Banco de Financiamiento  │ Banco Pichincha             │
│ Archivos Multimedia      │ 1 Imagen recibida           │
│ Resumen de Consulta      │ Cliente solicita cotización │
└──────────────────────────┴─────────────────────────────┘
```

### 6.2 Significado de las Métricas
* **Tiempo de Respuesta (FRT - First Response Time):** Mide con exactitud cuántos segundos o minutos tardó el asesor en enviar el primer mensaje desde que el cliente lo solicitó.
  - Etiqueta verde `frt-rapido`: Menos de 60 segundos (Excelente atención).
  - Etiqueta azul `frt-normal`: Entre 1 y 5 minutos.
* **Flujo / Intención:** Identifica automáticamente si el cliente busca camionetas, híbridos sin pico y placa, financiamiento o plan retoma.
* **Modelo de Interés:** Registra el auto específico por el que preguntó el lead.

### 6.3 Cómo agregar nuevas métricas con 1 solo clic
Si tu concesionario desea medir un dato nuevo (por ejemplo: *"Año de modelo usado para retoma"* o *"Profesión del cliente"*):
1. Abre en tu navegador el panel de métricas:
   ```
   https://usable-thorn-kabob.ngrok-free.dev/metricas?ngrok-skip-browser-warning=1
   ```
2. En la sección **"Crear Nueva Métrica en Chatwoot"**:
   - **Nombre de la Métrica:** Escribe el nombre (ej: *Año de Vehículo Retoma*).
   - **Descripción:** Breve explicación (ej: *Año del auto usado del cliente*).
   - **Tipo de Dato:** Texto, Número, o Casilla.
3. Haz clic en el botón azul **"Registrar Métrica en Chatwoot Cloud"**.
4. ¡Listo! La métrica se creará automáticamente en Chatwoot y aparecerá de inmediato en la barra lateral de todas las conversaciones.

---

## 7. Catálogo Digital Interactivo en WhatsApp (`/catalogo-autos`)

### 7.1 ¿Qué es la Vitrina Virtual Webview?
Es una página web interactiva ultra-rápida diseñada para abrirse **dentro de la misma pantalla de WhatsApp** (mediante el navegador interno de WhatsApp) cuando el cliente presiona el botón o enlace:

```
https://usable-thorn-kabob.ngrok-free.dev/catalogo-autos?phone=593988921136&ngrok-skip-browser-warning=1
```

### 7.2 Qué puede hacer el cliente en la vitrina
1. **Explorar Modelos 2026:** Ver fotografías en alta resolución de D-Max, Hilux, Poer, Yaris Cross Híbrido, Tracker, Sportage, Tucson, Tiggo y Sonet.
2. **Simulador de Crédito en Vivo:**
   - Mover una barra deslizante para elegir la entrada (desde el 20% hasta el 50%).
   - Elegir el plazo (12, 24, 36, 48 o 60 meses).
   - El simulador calcula automáticamente la cuota fija mensual estimada.
3. **Botón "Solicitar Cotización Formal":**
   - El cliente presiona el botón y sus datos quedan guardados en la base de datos de PostgreSQL (`vehicle_quotes`).
   - Se crea una nota interna en Chatwoot alertando al asesor: *"El cliente ha solicitado una cotización formal para el modelo X con cuota de \$Y"*.

---

## 8. Preguntas Frecuentes y Solución de Problemas (Troubleshooting)

### P1: ¿Qué hago si se reinicia la computadora o el servidor?
1. Abre PowerShell y verifica que los contenedores estén encendidos:
   ```powershell
   docker ps
   ```
2. Si están apagados, enciéndelos con un solo comando:
   ```powershell
   docker-compose up -d
   ```
3. Verifica que el túnel de Ngrok esté activo en su ventana de fondo o inícialo con:
   ```powershell
   ngrok http 8095 --url=usable-thorn-kabob.ngrok-free.dev
   ```

### P2: ¿Qué hago si un número de WhatsApp se desconecta?
1. Abre tu navegador en:
   ```
   http://localhost:8082/instance/connect/nombre_de_la_instancia
   ```
2. Escanea el código QR nuevamente desde WhatsApp en tu teléfono celular.
3. La sesión volverá a estar en estado `open` y el bot reanudará la atención al instante.

### P3: ¿El cliente nota que está hablando con una IA?
El asesor virtual **Alex** se presenta cordialmente como el asesor inteligente de AutoEcuador Motors 2026. Sus respuestas están redactadas con lenguaje comercial ecuatoriano, tono profesional, emojis automotrices y datos exactos de precios y promociones. Cuando la consulta requiere negociación final, Alex transfiere la conversación al asesor humano sin rodeos.

---

## 9. Contactos de Soporte y Datos de Cuenta

| Concepto | Valor Oficial del Sistema |
| :--- | :--- |
| **Plataforma de Asesores** | [https://app.chatwoot.com](https://app.chatwoot.com) |
| **Cuenta Chatwoot ID** | `193795` (Heuristic Log) |
| **Bandeja Principal** | Inbox ID `150556` (*WhatsApp*) |
| **Asesor Asignado** | Christianb (`christianb@heuristiclog.com`) |
| **Línea Principal Conectada** | `+593 98 892 1136` (Instancia: `sucursal_centro`) |
| **URL Pública del Catálogo** | `https://usable-thorn-kabob.ngrok-free.dev/catalogo-autos` |
| **Panel de Métricas** | `https://usable-thorn-kabob.ngrok-free.dev/metricas` |
| **Costo Mensual Total** | **$19.00 USD / mes** (1 Asiento, hasta 25 números) |
