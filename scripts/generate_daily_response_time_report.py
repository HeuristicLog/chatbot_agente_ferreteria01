import os
import asyncio
import httpx
import json
from datetime import datetime, timezone

CHATWOOT_BASE_URL = os.getenv("CHATWOOT_BASE_URL", "https://app.chatwoot.com")
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "193795")
API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "mMJycxtZ3GBmQhNBS3VaJgXC")

HEADERS = {
    "api_access_token": API_TOKEN,
    "Content-Type": "application/json"
}

INBOXES_CONFIG = {
    150556: {
        "name": "Ferretería Castor - WhatsApp Principal",
        "phone": "+593 98 892 1136",
        "tipo": "Evolution API / QR WhatsApp",
        "sucursal": "Centro"
    },
    151924: {
        "name": "Grupo Bonilla Marketing - WhatsApp Oficial",
        "phone": "+593 99 245 1085",
        "tipo": "Meta Cloud API Oficial",
        "sucursal": "Marketing / Ventas"
    }
}

async def generate_response_time_report():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=================================================================================")
        print("📊 INFORME DIARIO DE TIEMPOS DE RESPUESTA POR NÚMERO DE ENTRADA (CHATWOOT)")
        print("=================================================================================\n")

        overall_metrics = {}

        for inbox_id, cfg in INBOXES_CONFIG.items():
            print(f"📞 Analizando Número de Entrada: {cfg['phone']} ({cfg['name']})")
            print(f"   Canal: {cfg['tipo']} | Sede: {cfg['sucursal']}")
            
            url = f"{CHATWOOT_BASE_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations?inbox_id={inbox_id}"
            resp = await client.get(url, headers=HEADERS)
            
            if resp.status_code != 200:
                print(f"   ❌ Error al consultar inbox {inbox_id}: {resp.status_code}\n")
                continue

            convs = resp.json().get("data", {}).get("payload", [])
            total_chats = len(convs)
            
            frt_list = []
            instant_bot_count = 0  # < 10 segundos
            fast_human_count = 0   # 10s a 3 minutos
            delayed_count = 0      # > 3 minutos

            for c in convs:
                created_at = c.get("created_at")
                first_reply = c.get("first_reply_created_at")
                
                if created_at and first_reply and first_reply >= created_at:
                    delta_seconds = int(first_reply - created_at)
                    frt_list.append(delta_seconds)
                    if delta_seconds <= 10:
                        instant_bot_count += 1
                    elif delta_seconds <= 180:
                        fast_human_count += 1
                    else:
                        delayed_count += 1

            valid_samples = len(frt_list)
            avg_frt = round(sum(frt_list) / valid_samples, 1) if valid_samples > 0 else 0
            min_frt = min(frt_list) if valid_samples > 0 else 0
            max_frt = max(frt_list) if valid_samples > 0 else 0

            # Formato legible
            if avg_frt < 60:
                avg_frt_display = f"{avg_frt} seg"
            else:
                avg_frt_display = f"{int(avg_frt // 60)}m {int(avg_frt % 60)}s"

            bot_sla = round((instant_bot_count / valid_samples * 100), 1) if valid_samples > 0 else 100.0

            overall_metrics[inbox_id] = {
                "phone": cfg["phone"],
                "name": cfg["name"],
                "total_chats": total_chats,
                "measured_chats": valid_samples,
                "avg_frt": avg_frt,
                "avg_frt_display": avg_frt_display,
                "min_frt": f"{min_frt}s",
                "max_frt": f"{max_frt}s",
                "instant_bot_count": instant_bot_count,
                "bot_sla": bot_sla
            }

            print(f"   • Total Conversaciones Registradas: {total_chats}")
            print(f"   • Conversaciones con Primera Respuesta: {valid_samples}")
            print(f"   • Tiempo Promedio de 1ª Respuesta (FRT): {avg_frt_display}")
            print(f"   • Mejor Tiempo Registrado: {min_frt} seg | Máximo: {max_frt} seg")
            print(f"   • Respuestas Inmediatas del Bot (<10s): {instant_bot_count} ({bot_sla}% de efectividad)")
            print("   -----------------------------------------------------------------------------")

        print("\n=================================================================================")
        print("🏆 CUADRO COMPARATIVO DIARIO CONSOLIDADO POR NÚMERO DE ENTRADA")
        print("=================================================================================")
        print(f"{'NÚMERO':<18} | {'BANDEJA':<28} | {'CHATS':<6} | {'FRT PROMEDIO':<14} | {'EFECTIVIDAD BOT'}")
        print("-" * 85)
        for _, m in overall_metrics.items():
            print(f"{m['phone']:<18} | {m['name'][:28]:<28} | {m['total_chats']:<6} | {m['avg_frt_display']:<14} | {m['bot_sla']}%")
        print("=================================================================================\n")

if __name__ == "__main__":
    asyncio.run(generate_response_time_report())
