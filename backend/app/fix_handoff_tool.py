import sqlite3
import json

db_path = '/app/app/database.sqlite'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Final fix of transferir_a_asesor - no reference to $phone at all
new_func = """const fetch = require('node-fetch');
const session_id = $flow.chatId || "sess_default";
// Phone comes from vars injected by backend - use empty string if not available
const userPhone = ($vars && $vars.user_phone) ? $vars.user_phone : "";
const url = 'http://backend:8080/tools/handoff?session_id=' + encodeURIComponent(session_id);

try {
    const ticketIdRaw = typeof $ticket_id !== 'undefined' ? $ticket_id : null;
    const opIdRaw = typeof $operation_id !== 'undefined' ? $operation_id : null;
    const summaryRaw = typeof $summary !== 'undefined' ? $summary : '';

    const ticketIdParsed = (ticketIdRaw && ticketIdRaw !== 'null' && ticketIdRaw !== '') ? parseInt(ticketIdRaw, 10) : null;
    const opIdParsed = (opIdRaw && opIdRaw !== 'null' && opIdRaw !== '') ? parseInt(opIdRaw, 10) : null;

    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: session_id,
            phone: userPhone,
            reason: $reason,
            summary: summaryRaw || '',
            ticket_id: (ticketIdParsed !== null && !isNaN(ticketIdParsed)) ? ticketIdParsed : null,
            operation_id: (opIdParsed !== null && !isNaN(opIdParsed)) ? opIdParsed : null
        })
    });
    const data = await response.json();
    return JSON.stringify(data);
} catch (error) {
    return 'Error al registrar transferencia: ' + error.message;
}"""

new_schema = [
    {
        "property": "reason",
        "type": "string",
        "description": "Razón de la transferencia o tema de consulta del usuario (ej. 'reclamo de garantía', 'consulta de pedido', etc.)",
        "required": True
    },
    {
        "property": "summary",
        "type": "string",
        "description": "Resumen breve de la conversación para contextualizar al asesor humano",
        "required": False
    },
    {
        "property": "ticket_id",
        "type": "string",
        "description": "ID del ticket consultado si aplica (opcional)",
        "required": False
    },
    {
        "property": "operation_id",
        "type": "string",
        "description": "ID de la operación logística si aplica (opcional)",
        "required": False
    }
]

new_schema_str = json.dumps(new_schema)
cursor.execute("UPDATE tool SET func = ?, schema = ? WHERE name = 'transferir_a_asesor';", (new_func, new_schema_str))
print("FINAL UPDATE: transferir_a_asesor - removed $phone reference, uses $vars.user_phone only.")

conn.commit()
conn.close()
