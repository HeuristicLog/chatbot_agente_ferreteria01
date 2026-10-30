# GUÍA DE E-COMMERCE, NUEVO NÚMERO Y CONFIGURACIÓN DE MÉTRICAS EN CHATWOOT
## Ecosistema WhatsApp con IA (LangChain) y Vitrina In-App
### Concesionario AutoEcuador Motors 2026

---

## 1. Funcionamiento del E-commerce, Carrito y Dominio

### 1.1 ¿Cómo funciona la tienda digital en nuestro sistema?
A diferencia de un e-commerce tradicional (como WooCommerce o Shopify) donde se venden productos de $10 o $50 que se pagan directamente con tarjeta de crédito, en la venta automotriz de vehículos de **$18,000 a $40,000 USD** el flujo comercial es distinto:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FLUJO COMERCIAL IN-APP                          │
│                                                                        │
│  [ WhatsApp Chat ] ➔ [ Vitrina Webview ] ➔ [ Mi Garaje / Carrito ]    │
│  Bot Alex envía link   Abre sin salir de     Simula Entrada (20%-50%)  │
│  interactivo           WhatsApp (<250ms)     y Cuota mensual estimada │
│                                                                        │
│  ➔ [ Enviar Cotización ] ➔ [ Alerta Chatwoot ] ➔ [ Asesor Humano ]    │
│     Guarda en Postgres      Nota interna con        Negocia y cierra   │
│     y genera Lead           datos financieros       la venta en vivo   │
└────────────────────────────────────────────────────────────────────────┘
```

* **El "Carrito" = "Mi Garaje / Carrito de Cotización":**
  - El cliente explora los 9 modelos 2026 (D-Max, Hilux, Poer, Yaris Cross Híbrido, Tracker, etc.).
  - Presiona el ícono de garaje para guardar sus modelos favoritos.
  - Ajusta el deslizador de entrada (desde el 20% hasta el 50%) y el plazo (12 a 60 meses).
  - Al presionar **"Solicitar Cotización Formal"**, no se le cobra dinero en tarjeta; se genera una **orden de cotización formal** guardada en la base de datos PostgreSQL (`vehicle_quotes`) y se inserta una nota interna inmediata en la conversación de Chatwoot con todos los datos financieros calculados.
* **El Dominio:**
  - **No necesitas comprar dos dominios separados ni montar dos servidores.**
  - Todo funciona bajo **un único dominio central** (tu dominio en producción `https://bot.tudominio.com` o el túnel público seguro `https://usable-thorn-kabob.ngrok-free.dev`):
    - `https://bot.tudominio.com/catalogo-autos` ➔ Vitrina webview optimizada.
    - `https://bot.tudominio.com/webhooks/whatsapp` ➔ Webhook de WhatsApp.
    - `https://bot.tudominio.com/webhooks/chatwoot` ➔ Webhook de Chatwoot Cloud.
    - `https://bot.tudominio.com/metricas` ➔ Panel de métricas y analítica en vivo.

---

## 2. Verificación del Nuevo Número Conectado

Se ha verificado la conexión del nuevo número oficial agregado en Chatwoot:

### 2.1 Datos de la Nueva Línea:
* **Nombre de la Bandeja:** `Grupo Bonilla Marketing / Ing.Diana Flores WhatsApp`
* **Número Telefónico Oficial:** `+593 99 245 1085` (`593992451085`)
* **ID de Bandeja (Inbox ID):** `151924`
* **Tipo de Canal:** `Channel::Whatsapp` (Meta WhatsApp Cloud API oficial vía Embedded Signup)
* **Phone Number ID en Meta:** `1256511970882085`
* **WABA Account ID:** `1731464744642875`
* **Estado Actual:** 🟢 **Conectado y Operativo.** Ya registra conversaciones activas en Chatwoot (Conv #9, #10 y #11).

### 2.2 Sincronización Aplicada en el Backend:
Actualizamos el archivo `.env` (`WHATSAPP_INBOX_MAPPING`) y el enrutador en `backend/app/api/webhooks.py`:
1. Cuando un asesor responda a un cliente dentro de la bandeja `151924`, el sistema detecta las credenciales oficiales de Meta Cloud y envía el mensaje prioritariamente a través de la API oficial de WhatsApp Cloud.
2. Si el mensaje proviene de la bandeja `150556` (`+593 98 892 1136`), se enruta automáticamente por Evolution API (WhatsApp QR Baileys).
3. Ambas líneas conviven en la misma cuenta de Chatwoot bajo el **mismo asesor comercial (`Christianb`) por los mismos $19 USD/mes**.

---

## 3. Cómo Agregar y Configurar Nuevas Métricas en Cada Conversación

Chatwoot Cloud y nuestro backend cuentan con un sistema de **Atributos Personalizados (Custom Attributes)** que permite medir cualquier variable de negocio en tiempo real.

Actualmente el sistema ya mide y muestra en la barra lateral derecha de cada conversación:
* `tiempo_respuesta_frt`: Tiempo que tardó el asesor en responder (ej: `18 seg` - frt-rápido).
* `flujo_actual`: Categoría consultada (`Camionetas 4x4`, `Híbridos Cero Pico y Placa`, etc.).
* `modelo_interes`: Vehículo exacto cotizado (ej: `Chevrolet D-Max 3.0L Diésel`).
* `presupuesto_entrada`: Monto de entrada disponible (ej: `$6,998 USD`).
* `banco_de_financiamiento`: Banco preferido (`Banco Pichincha`, `Produbanco`, etc.).
* `sucursal_preferida`: Agencia asignada (`Quito Centro`, `Guayaquil Norte`, etc.).

---

### 3.1 Método 1: Crear Nuevas Métricas desde el Panel Web (`/metricas`)

La forma más rápida (con 1 solo clic):
1. Abre en tu navegador:
   ```
   https://usable-thorn-kabob.ngrok-free.dev/metricas?ngrok-skip-browser-warning=1
   ```
2. Desplázate hacia la sección **"Crear Nueva Métrica en Chatwoot"**:
   - **Nombre de la Métrica:** Escribe el nombre visible (ej: *Año de Auto Usado Retoma*, *Profesión del Cliente*, *Estado de Crédito*).
   - **Tipo de Dato:** Selecciona:
     * `Texto` (para nombres, notas o descripciones).
     * `Número` (para presupuestos, años, montos).
     * `Lista de selección` (para opciones como: Aprobado, Pendiente, Rechazado).
     * `Casilla de verificación` (Sí / No).
   - **Descripción:** Breve explicación del objetivo comercial.
3. Haz clic en **"Registrar Métrica en Chatwoot Cloud"**.
4. ¡Listo! La métrica se registra de inmediato vía API y aparecerá en la barra lateral de todas las conversaciones en Chatwoot.

---

### 3.2 Método 2: Crear Métricas Directamente en Chatwoot Cloud

Si prefieres hacerlo desde la consola de Chatwoot:
1. Inicia sesión en [https://app.chatwoot.com](https://app.chatwoot.com) con `christianb@heuristiclog.com`.
2. En la barra lateral izquierda inferior, haz clic en el ícono de engranaje (**Ajustes** / **Settings**).
3. En el menú de opciones, selecciona **"Atributos personalizados"** (Custom Attributes).
4. Haz clic en el botón superior azul **"Añadir atributo personalizado"**.
5. Configura el formulario:
   * **Se aplica a:** Selecciona **Conversación** (Conversation Attribute).
   * **Nombre para mostrar:** El nombre que verá el asesor (ej: *Entidad Bancaria Solicitada*).
   * **Clave de atributo:** El identificador en minúsculas y sin espacios (ej: `entidad_bancaria`).
   * **Tipo de atributo:** Texto, Número, Moneda, Selección, o Casilla.
6. Haz clic en **"Crear"**.

---

### 3.3 Método 3: Extracción y Autocompletado Automático con Inteligencia Artificial

Para que no tengas que escribir la métrica a mano en cada chat y el bot la extraiga solo:
En el archivo [`backend/app/api/webhooks.py`](file:///c:/Users/User/Desktop/KEVIN/ChatbotFlowise/backend/app/api/webhooks.py) (línea 550 a 590), el bot analiza el mensaje del cliente y autocompleta los campos.

Por ejemplo, si deseas medir si el cliente tiene un auto usado para el Plan Retoma:
```python
# Ejemplo en backend/app/api/webhooks.py:
if any(k in clean_lower for k in ["retoma", "usado", "mi auto", "cambio"]):
    cust_attrs["flujo_actual"] = "Plan Retoma"
    cust_attrs["tiene_auto_usado"] = "Sí"
    labels.append("plan-retoma")
```

En cuanto el cliente menciona que tiene un auto usado, el sistema actualiza automáticamente el atributo en Chatwoot y agrega la etiqueta `plan-retoma`.

---

## 4. Resumen de Estados

| Componente | Estado | Detalle |
| :--- | :---: | :--- |
| **Línea WhatsApp 1 (`+593 98 892 1136`)** | 🟢 **Open** | Instancia Evolution `sucursal_centro` (QR Baileys). |
| **Línea WhatsApp 2 (`+593 99 245 1085`)** | 🟢 **Open** | Bandeja Meta Cloud `151924` (Grupo Bonilla Marketing). |
| **Vitrina Digital In-App** | 🟢 **Activa** | `/catalogo-autos` con simulador de crédito (20%-50%). |
| **Panel de Métricas** | 🟢 **Activo** | `/metricas` para creación de atributos y analítica en vivo. |
| **Túnel Público Seguro** | 🟢 **Online** | `usable-thorn-kabob.ngrok-free.dev` |
