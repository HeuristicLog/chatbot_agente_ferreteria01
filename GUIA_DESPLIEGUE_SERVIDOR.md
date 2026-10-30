# GUÍA PASO A PASO: DESPLIEGUE EN SERVIDOR DE PRODUCCIÓN (VPS / CLOUD)
## Ecosistema WhatsApp con IA (LangChain), Vitrina In-App y Chatwoot Cloud
### AutoEcuador Motors 2026 — Imágenes Oficiales en Docker Hub

> **Imágenes Publicadas en Docker Hub:**  
> • Backend LangChain: `docker.io/kevinagk/autoeconomotors-backend:latest`  
> • Gateway WhatsApp & Webview: `docker.io/kevinagk/autoeconomotors-gateway:latest`  
> • Evolution API: `docker.io/evoapicloud/evolution-api:latest`  
> **Rama de Git:** `KevinAG23/langchain-chatwoot-interactive-suite`

---

## 1. Requisitos Previos del Servidor

* **Sistema Operativo:** Ubuntu 22.04 LTS o 24.04 LTS (o cualquier distribución Linux con Docker).
* **Hardware recomendado:** Mínimo 2 vCPU, 4 GB de memoria RAM y 20 GB de disco SSD (ej: DigitalOcean Droplet, AWS EC2 t3.medium, Hetzner Cloud CPX21 o similar).
* **Puertos de red abiertos en el Firewall / Security Group:**
  * `80` (HTTP para emisión de certificados SSL Let's Encrypt).
  * `443` (HTTPS para tráfico cifrado público).
  * `8082` (Opcional, interfaz web de Evolution API para vincular el QR desde tu navegador).
* **Dominio o Subdominio:** Un registro tipo `A` que apunte a la dirección IP pública de tu servidor (ejemplo: `bot.tudominio.com` ➔ `IP_DEL_SERVIDOR`).

---

## 2. Paso 1: Instalar Docker y Docker Compose en el Servidor

Conéctate por SSH a tu servidor:
```bash
ssh usuario@TU_IP_SERVIDOR
```

Actualiza el sistema e instala Docker oficial:
```bash
# Actualizar repositorios
sudo apt update && sudo apt upgrade -y

# Instalar dependencias necesarias
sudo apt install -y curl git ufw

# Instalar Docker mediante el script oficial
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Habilitar Docker para iniciar automáticamente
sudo systemctl enable docker
sudo systemctl start docker

# Permitir a tu usuario ejecutar Docker sin sudo
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalación
docker --version
docker compose version
```

---

## 3. Paso 2: Clonar el Proyecto y Seleccionar la Rama

```bash
# 1. Clonar el repositorio
git clone https://github.com/HeuristicLog/chatbot_agente_ferreteria01.git autoeconomotors

# 2. Entrar al directorio
cd autoeconomotors

# 3. Cambiar a la rama oficial de producción
git checkout KevinAG23/langchain-chatwoot-interactive-suite
```

---

## 4. Paso 3: Configurar las Variables de Entorno (`.env`)

Copia la plantilla de servidor:
```bash
cp .env.server.example .env
```

Edita el archivo con `nano`:
```bash
nano .env
```

Ajusta los siguientes parámetros:
* **`DOMAIN`**: Coloca tu dominio o subdominio real (ej: `bot.tudominio.com`).
* **`CATALOG_BASE_URL`**: `https://bot.tudominio.com`
* **`SERVER_PUBLIC_URL`**: `https://bot.tudominio.com`
* **`POSTGRES_PASSWORD`**: Escribe una contraseña segura para tu base de datos.
* Guarda con `Ctrl + O`, presiona `Enter` y sal con `Ctrl + X`.

---

## 5. Paso 4: Levantar los Contenedores con Docker Compose

Ejecuta el archivo de servidor optimizado (descargará automáticamente las imágenes desde Docker Hub):

```bash
docker compose -f docker-compose.server.yml up -d
```

Verifica que todos los contenedores estén en estado `Up` y `healthy`:
```bash
docker compose -f docker-compose.server.yml ps
```

Deberás ver los siguientes contenedores activos:
- `autoeconomotors-caddy` (Proxy inverso con SSL automático)
- `autoeconomotors-gateway` (Gateway WhatsApp & Webview)
- `autoeconomotors-backend` (Motor IA LangChain en Python)
- `autoeconomotors-evolution` (Motor WhatsApp Baileys)
- `autoeconomotors-postgres` (Base de datos PostgreSQL 15)
- `autoeconomotors-redis` (Memoria conversacional y cerrojos)

---

## 6. Paso 5: Conectar WhatsApp mediante Código QR

Para conectar el número oficial del concesionario (`+593 98 892 1136` o cualquier línea de las 25 disponibles):

### Opción A: Desde tu navegador web
Abre en tu navegador:
```
http://TU_IP_SERVIDOR:8082/instance/connect/sucursal_centro
```
Escanea el código QR que aparece en pantalla con la app de WhatsApp de tu teléfono móvil (**Dispositivos vinculados** ➔ **Vincular un dispositivo**).

### Opción B: Por línea de comandos en el servidor
```bash
# Crear la instancia si no existiese
curl -X POST "http://localhost:8082/instance/create" \
  -H "apikey: ferreteria_evolution_key_2026" \
  -H "Content-Type: application/json" \
  -d '{"instanceName":"sucursal_centro","token":"sucursal_centro_token","qrcode":true}'

# Ver el estado de conexión
curl -s -X GET "http://localhost:8082/instance/connectionState/sucursal_centro" \
  -H "apikey: ferreteria_evolution_key_2026"
```
Cuando la respuesta sea `{"state":"open"}`, tu WhatsApp ya está sincronizado.

---

## 7. Paso 6: Actualizar el Webhook en Chatwoot Cloud

Dado que tu servidor ahora tiene su propio dominio con HTTPS seguro (ej: `https://bot.tudominio.com`), actualiza el webhook en Chatwoot Cloud para no depender de túneles temporales:

1. Ingresa a [https://app.chatwoot.com](https://app.chatwoot.com) con la cuenta de `Christianb`.
2. Ve a **Ajustes** ➔ **Webhooks** ➔ Edita el Webhook existente (ID `20871`) o añade uno nuevo:
   * **URL del Webhook:** `https://bot.tudominio.com/webhooks/chatwoot`
   * **Eventos a suscribir:**
     - `conversation_created`
     - `conversation_status_changed`
     - `message_created`
     - `message_updated`
3. Guarda los cambios.

---

## 8. Paso 7: Verificación en Vivo del Despliegue

En el servidor, ejecuta la suite de pruebas automatizadas:
```bash
python3 run_full_system_test.py
```

Verifica los siguientes endpoints en tu navegador:
* **Salud del Sistema:** `https://bot.tudominio.com/health` (debe responder `{"status":"ok"}`).
* **Catálogo Webview en Vivo:** `https://bot.tudominio.com/catalogo-autos` (debe abrir la vitrina virtual 2026).
* **Métricas en Vivo:** `https://bot.tudominio.com/metricas`

---

## 9. Mantenimiento y Comandos Útiles

```bash
# Ver registros en vivo de todos los servicios
docker compose -f docker-compose.server.yml logs -f

# Ver registros específicos del bot con IA
docker compose -f docker-compose.server.yml logs -f backend

# Reiniciar los servicios
docker compose -f docker-compose.server.yml restart

# Actualizar a la última versión de las imágenes de Docker Hub
docker compose -f docker-compose.server.yml pull
docker compose -f docker-compose.server.yml up -d
```
