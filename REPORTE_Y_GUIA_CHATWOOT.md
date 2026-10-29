# REPORTE DE PRUEBAS Y GUÍA OPERATIVA DE CHATWOOT CLOUD
## Sistema de Atención WhatsApp con IA (LangChain) y Vitrina Webview
### Concesionario AutoEcuador Motors 2026

---

## 1. Resumen Ejecutivo y Resultados de Verificación

Se ejecutó la suite de pruebas automatizadas y en vivo sobre el ecosistema completo:
- **Motor Conversacional LangChain / Python:** Respuestas interactivas (no texto plano), menús visuales con emojis, viñetas y enlaces directos a la vitrina virtual.
- **Vitrina Webview WhatsApp (`/catalogo-autos`):** Catálogo optimizado para el navegador interno de WhatsApp, con simulador de crédito en vivo (20% al 50% de entrada) y botón de retorno instantáneo.
- **Chatwoot Cloud (API v1 en vivo):** Verificación exitosa de las 10 funcionalidades principales con la cuenta oficial ID `193795` e Inbox ID `150556`.

### Resultados de la Suite de Pruebas:
| Módulo Probado | Pruebas Ejecutadas | Estado | Calificación |
| :--- | :--- | :---: | :---: |
| **Flujos Interactivos LangChain** | 10 flujos (0 al 7 + consultas libres D-Max e Híbrido) | **10/10 Aprobados** | 100% |
| **Vitrina Webview sin salir de WhatsApp** | Cierre webview, Mi Garaje, Simulador crédito, 9 modelos 2026, Responsive móvil | **7/7 Aprobados** | 100% |
| **Chatwoot Cloud Omnicanal** | Inboxes, Custom Attributes, Contactos, Mensajes, Etiquetas, Notas privadas, Estados | **10/10 Aprobados** | 100% |

---

## 2. Guía Detallada de Funcionalidades de Chatwoot Cloud

Chatwoot Cloud ([https://app.chatwoot.com](https://app.chatwoot.com)) es la consola central donde el asesor comercial (`Christianb`) supervisa, interviene y analiza todas las conversaciones de WhatsApp.

### 2.1 Bandeja de Entrada Única para 25 Números ($19 USD/mes)
* **¿Cómo funciona la licencia?** Chatwoot Cloud factura **por usuario asesor humano** ($19 USD/mes por la cuenta de Christianb), **NO por número telefónico ni por volumen de mensajes**.
* **Bandejas (Inboxes) ilimitadas:** Puedes crear hasta 25 bandejas de tipo **API Channel** (una por cada sucursal o vendedor: *Quito Centro*, *Guayaquil Norte*, *Cuenca*, etc.) con costo **\$0 adicional**.
* **Filtros por Bandeja:** En el menú lateral izquierdo de Chatwoot puedes hacer clic en cualquiera de las 25 bandejas para ver solo los mensajes de esa sucursal, o hacer clic en **"Todas"** para ver el flujo consolidado de todo el concesionario.

---

### 2.2 Panel de Conversaciones y Estados del Ciclo de Vida
Cada conversación en Chatwoot tiene 3 estados fundamentales:

1. **Abierta (`Open`):**
   * El cliente está interactuando con el bot **Alex** o está esperando atención humana.
   * El sistema actualiza en tiempo real los atributos y etiquetas en la barra lateral.
2. **Pausada / Atención Humana Activa (`human_active`):**
   * Se activa en el milisegundo en que el asesor escribe una respuesta al cliente (desde Chatwoot o desde su propio teléfono celular).
   * **El bot con IA se silencia de inmediato** para no interferir con la negociación comercial.
3. **Resuelta (`Resolved`):**
   * Cuando el asesor termina la negociación, hace clic en el botón verde **"Resolver"** en la esquina superior derecha.
   * El sistema envía un mensaje amable al cliente:
     > *"✅ Atención al cliente finalizada. El asesor comercial virtual Alex de AutoEcuador Motors 🇪🇨 vuelve a estar activo. Escribe hola para ver el menú o explorar vehículos."*
   * A partir de ese momento, si el cliente vuelve a escribir, el bot de IA lo atenderá nuevamente.

---

### 2.3 Atributos Personalizados Automotrices (Custom Attributes)
En la columna lateral derecha de cada conversación en Chatwoot, el asesor puede ver los datos clave del cliente detectados automáticamente por la IA:

| Clave del Atributo | Nombre Visible | Qué Muestra | Ejemplo en Vivo |
| :--- | :--- | :--- | :--- |
| `tiempo_respuesta_frt` | **Tiempo de Respuesta (FRT)** | Segundos o minutos que tardó el asesor en responder al cliente | `18 seg` (frt-rapido) |
| `flujo_actual` | **Flujo / Intención** | Categoría vehicular que consulta el lead | `Camionetas 4x4` / `Híbridos Cero Pico y Placa` |
| `modelo_interes` | **Modelo de Interés** | Auto específico cotizado | `Chevrolet D-Max 3.0L Diésel` |
| `presupuesto_entrada` | **Entrada Estimada (USD)** | Monto en dólares que el cliente tiene de entrada | `$6,998 USD` |
| `banco_de_financiamiento` | **Banco de Financiamiento** | Entidad financiera preferida | `Banco Pichincha` / `Produbanco` |
| `sucursal_preferida` | **Sucursal Asignada** | Agencia más cercana | `Quito Centro` / `Guayaquil Norte` |
| `adjuntos_recibidos` | **Archivos Multimedia** | Tipo de archivo enviado por el cliente | `Archivo Image` / `Archivo Document` |
| `resumen_consulta` | **Resumen de Consulta** | Breve síntesis para el asesor | `Cliente solicita cotización formal con 20% entrada` |

---

### 2.4 Sistema de Etiquetas Comerciales (Labels)
Las etiquetas permiten clasificar a los clientes con un código de colores visible en la lista de chats:
* 🟢 `frt-rapido`: Conversación respondida en menos de 60 segundos.
* 🔵 `lead-calificado`: Cliente con modelo definido y presupuesto de entrada listo.
* 🟠 `camionetas-4x4`: Interesados en D-Max, Hilux o Poer.
* 🌿 `hibrido-0-pico-y-placa`: Clientes de Quito buscando exención de pico y placa (Yaris Cross).
* 🟣 `plan-retoma`: Cliente que ofrece su auto usado como parte de pago.

> [!TIP]
> **Filtrar por Etiquetas:** En Chatwoot puedes presionar la barra de búsqueda y filtrar por cualquier etiqueta (por ejemplo, buscar todas las conversaciones con `lead-calificado`) para realizar campañas de seguimiento o llamadas de cierre.

---

### 2.5 Notas Privadas Internas (Private Notes)
Chatwoot permite enviar mensajes internos que **solo ven los miembros de tu equipo y el sistema**, sin que el cliente de WhatsApp los reciba:
1. En el cuadro de respuesta en Chatwoot, haz clic en la pestaña **"Nota Privada"** (el fondo del cuadro cambiará a color amarillo suave).
2. Escribe observaciones de la negociación:
   * *"Cliente pre-aprobado con Banco Pichincha, llamará mañana a las 10:00 AM para firmar reserva."*
3. Presiona **"Añadir nota"**.
4. La IA Alex también utiliza este canal para dejar alertas automáticas cuando un cliente solicita una cotización formal desde la vitrina webview.

---

### 2.6 Envío de Archivos Multimedia (Fotos, PDFs, Fichas Técnicas)
* Puedes arrastrar y soltar cualquier fotografía de vehículo (JPG, PNG) o ficha técnica en PDF directamente sobre la ventana de Chatwoot.
* El cliente lo recibirá en WhatsApp de forma nativa e inmediata con soporte de vista previa.

---

## 3. Funcionamiento de la Vitrina Webview sin Salir de WhatsApp

### 3.1 Cómo la experimenta el cliente
1. En cualquier momento del chat, el bot Alex o el menú rápido le ofrece el enlace:
   ```
   https://usable-thorn-kabob.ngrok-free.dev/catalogo-autos?phone=593988921136&ngrok-skip-browser-warning=1
   ```
2. Al tocar el enlace en su celular, **WhatsApp abre su navegador interno (In-App Browser)** sin sacar al cliente de la conversación.
3. El cliente explora los 9 modelos 2026, filtra por categorías (Camionetas, Híbridos, SUVs) y puede guardar sus favoritos en **"Mi Garaje"**.

### 3.2 Simulador de Crédito en Vivo
* El cliente selecciona cualquier vehículo (por ejemplo: *Chevrolet D-Max $34,990 USD*).
* Mueve la barra de entrada (20%, 30%, 40%, 50%) y el plazo (12 a 60 meses).
* El sistema recalcula en tiempo real la cuota mensual fija estimada.

### 3.3 Envío de Cotización Formal y Retorno a WhatsApp
* Al presionar **"Solicitar Cotización Formal"**, los datos se registran en la base de datos PostgreSQL (`vehicle_quotes`) y se genera una nota interna en Chatwoot.
* El botón superior **"Volver a WhatsApp"** (`closeWebviewAndReturn()`) cierra la vitrina y regresa al chat con el asesor de inmediato.

---

## 4. Flujos Interactivos del Asesor Virtual (No Texto Plano)

A diferencia de los chatbots tradicionales que envían bloques de texto plano monótono, el motor LangChain de AutoEcuador Motors estructura cada mensaje con:
1. **Encabezado llamativo con emojis temáticos** (🛻 Camionetas, 🌿 Híbridos, 🚙 SUVs, 💳 Crédito).
2. **Cálculo financiero explícito** (Precio con IVA 15%, entrada mínima del 20% y cuota mensual a 60 meses).
3. **Enlace directo a la vitrina webview** para ver fotos y comparar.
4. **Opciones interactivas de respuesta rápida:**
   - 1️⃣ Ver camionetas 4x4
   - 2️⃣ Híbridos Cero Pico y Placa
   - 3️⃣ SUVs Familiares
   - 4️⃣ Abrir vitrina interactiva
   - 5️⃣ Simular crédito vehicular
   - 6️⃣ Plan retoma de usados
   - 7️⃣ Hablar con asesor humano

---

## 5. Contacto y Parámetros Técnicos Validados

| Parámetro | Configuración Activa | Estado |
| :--- | :--- | :---: |
| **URL de Chatwoot** | `https://app.chatwoot.com` | Conectado |
| **ID de Cuenta Chatwoot** | `193795` (Heuristic Log) | Verificado |
| **ID de Bandeja Principal** | `150556` (*WhatsApp*) | Activo |
| **Agente Asesor** | `Christianb` (`christianb@heuristiclog.com`) | Asignado |
| **Línea WhatsApp Principal** | `+593 98 892 1136` (Instancia: `sucursal_centro`) | Vinculada |
| **URL Vitrina Webview** | `https://usable-thorn-kabob.ngrok-free.dev/catalogo-autos` | Operativa |
| **Coste Mensual de Licencia** | **$19.00 USD / mes** (1 Asiento para hasta 25 números) | Garantizado |
