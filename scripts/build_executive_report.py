import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# 1. GENERACIÓN DEL EXCEL PROFESIONAL MULTI-HOJA (.XLSX)
# ==============================================================================

def create_executive_excel(file_path):
    wb = openpyxl.Workbook()
    
    NAVY = "1E3A8A"
    LIGHT_NAVY = "DBEAFE"
    DARK_TEXT = "0F172A"
    WHITE = "FFFFFF"
    GRAY_BORDER = "CBD5E1"
    EMERALD = "059669"
    LIGHT_GRAY = "F8FAFC"

    font_title = Font(name="Calibri", size=15, bold=True, color=NAVY)
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="475569")
    font_header = Font(name="Calibri", size=11, bold=True, color=WHITE)
    font_bold = Font(name="Calibri", size=11, bold=True, color=DARK_TEXT)
    font_regular = Font(name="Calibri", size=11, color=DARK_TEXT)
    font_kpi_num = Font(name="Calibri", size=18, bold=True, color=NAVY)
    font_kpi_sub = Font(name="Calibri", size=9, bold=True, color="64748B")

    fill_header = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
    fill_zebra = PatternFill(start_color=LIGHT_GRAY, end_color=LIGHT_GRAY, fill_type="solid")
    fill_kpi = PatternFill(start_color=LIGHT_NAVY, end_color=LIGHT_NAVY, fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=GRAY_BORDER),
        right=Side(style='thin', color=GRAY_BORDER),
        top=Side(style='thin', color=GRAY_BORDER),
        bottom=Side(style='thin', color=GRAY_BORDER)
    )

    # ── Hoja 1: Resumen Consolidado ──
    ws1 = wb.active
    ws1.title = "Consolidado Todas Entradas"
    ws1.views.sheetView[0].showGridLines = True

    ws1["A1"] = "FERRETERÍA CASTOR & GRUPO BONILLA"
    ws1["A1"].font = font_title
    ws1["A2"] = "Informe Consolidado de Rendimiento y Tiempos de Respuesta Omnicanal"
    ws1["A2"].font = font_subtitle
    ws1["A3"] = "Período Auditado: 31 de Octubre al 07 de Noviembre de 2026 | Fuente: Chatwoot Cloud"
    ws1["A3"].font = Font(name="Calibri", size=9, color="64748B")

    kpis = [
        ("A", "C", "TIEMPO 1ª RESPUESTA (BOT)", "1.3 Segundos", "Línea WhatsApp Castor (+593 98 892 1136)"),
        ("D", "F", "TIEMPO 1ª RESPUESTA (HUMANO)", "1 hora 42 min", "Línea Asesores (+593 99 245 1085)"),
        ("G", "I", "AHORRO OPERATIVO DE TIEMPO", "99.9%", "Reducción de espera con Asistente Castor"),
        ("J", "L", "TOTAL MENSAJES PROCESADOS", "259 Mensajes", "134 Recibidos | 125 Enviados")
    ]

    for start_col, end_col, title, value, sub in kpis:
        ws1.merge_cells(f"{start_col}5:{end_col}5")
        ws1.merge_cells(f"{start_col}6:{end_col}6")
        ws1.merge_cells(f"{start_col}7:{end_col}7")
        ws1[f"{start_col}5"].value = title
        ws1[f"{start_col}5"].font = font_kpi_sub
        ws1[f"{start_col}5"].alignment = Alignment(horizontal="center", vertical="center")
        ws1[f"{start_col}5"].fill = fill_kpi

        ws1[f"{start_col}6"].value = value
        ws1[f"{start_col}6"].font = font_kpi_num
        ws1[f"{start_col}6"].alignment = Alignment(horizontal="center", vertical="center")
        ws1[f"{start_col}6"].fill = fill_kpi

        ws1[f"{start_col}7"].value = sub
        ws1[f"{start_col}7"].font = Font(name="Calibri", size=8, color="475569")
        ws1[f"{start_col}7"].alignment = Alignment(horizontal="center", vertical="center")
        ws1[f"{start_col}7"].fill = fill_kpi

    ws1["A9"] = "AUDITORÍA COMPARATIVA POR BANDEJA Y NÚMERO DE ENTRADA"
    ws1["A9"].font = Font(name="Calibri", size=13, bold=True, color=NAVY)

    headers = [
        "Bandeja de Entrada", "Canal / Tecnología", "Número Telefónico", 
        "Conversaciones", "Msjs Recibidos", "Msjs Enviados", 
        "1ª Respuesta (FRT)", "Tiempo Resolución", "Tasa de Automatización"
    ]

    for col_idx, h in enumerate(headers, start=1):
        cell = ws1.cell(row=10, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    rows_data = [
        ["WhatsApp (Ferretería Castor)", "Evolution API (QR Baileys)", "+593 98 892 1136", 7, 60, 57, "1.3 segundos", "2.0 segundos", "100.0% (Bot Activo)"],
        ["Grupo Bonilla Marketing", "Meta Cloud API Oficial", "+593 99 245 1085", 61, 74, 68, "1 hora 42 min", "2 horas 23 min", "60.0% (Híbrido Humano)"],
        ["Heuristic Log (Chat Web)", "Website Live Chat Widget", "N/A (Web)", 0, 0, 0, "N/A", "N/A", "0.0%"]
    ]

    for r_idx, r_data in enumerate(rows_data, start=11):
        for c_idx, val in enumerate(r_data, start=1):
            cell = ws1.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx in [4, 5, 6]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            elif c_idx in [7, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if r_idx % 2 == 0:
                cell.fill = fill_zebra

    total_row = 14
    ws1.cell(row=total_row, column=1, value="TOTALES CONSOLIDADOS").font = font_bold
    ws1.cell(row=total_row, column=1).border = thin_border
    ws1.cell(row=total_row, column=2, value="").border = thin_border
    ws1.cell(row=total_row, column=3, value="").border = thin_border
    ws1.cell(row=total_row, column=4, value="=SUM(D11:D13)").font = font_bold
    ws1.cell(row=total_row, column=4).border = thin_border
    ws1.cell(row=total_row, column=4).alignment = Alignment(horizontal="right")
    ws1.cell(row=total_row, column=5, value="=SUM(E11:E13)").font = font_bold
    ws1.cell(row=total_row, column=5).border = thin_border
    ws1.cell(row=total_row, column=5).alignment = Alignment(horizontal="right")
    ws1.cell(row=total_row, column=6, value="=SUM(F11:F13)").font = font_bold
    ws1.cell(row=total_row, column=6).border = thin_border
    ws1.cell(row=total_row, column=6).alignment = Alignment(horizontal="right")
    ws1.cell(row=total_row, column=7, value="1.3s (Bot) / 1h 42m (Hum)").font = font_bold
    ws1.cell(row=total_row, column=7).border = thin_border
    ws1.cell(row=total_row, column=7).alignment = Alignment(horizontal="center")
    ws1.cell(row=total_row, column=8, value="").border = thin_border
    ws1.cell(row=total_row, column=9, value="").border = thin_border

    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # ── Hoja 2: Línea Individual Castor ──
    ws2 = wb.create_sheet(title="Entrada WhatsApp Castor")
    ws2.views.sheetView[0].showGridLines = True
    ws2["A1"] = "REPORTE ESPECÍFICO: NÚMERO DE ENTRADA +593 98 892 1136"
    ws2["A1"].font = font_title
    ws2["A2"] = "Bandeja: WhatsApp (ID: 150556) | Canal: Evolution API Baileys QR | Sucursal: Centro"
    ws2["A2"].font = font_subtitle

    castor_kpis = [
        ("A", "C", "TIEMPO 1ª RESPUESTA", "1.3 Segundos ⚡", "SLA Inmediato (Castor IA activo)"),
        ("D", "F", "TIEMPO DE RESOLUCIÓN", "2.0 Segundos", "Resolución automatizada en WhatsApp"),
        ("G", "I", "MENSAJES INTERCAMBIADOS", "117 Mensajes", "60 Recibidos | 57 Enviados"),
        ("J", "L", "TASA DE EFECTIVIDAD", "100.0%", "7 de 7 conversaciones respondidas <10s")
    ]
    for start_col, end_col, title, value, sub in castor_kpis:
        ws2.merge_cells(f"{start_col}4:{end_col}4")
        ws2.merge_cells(f"{start_col}5:{end_col}5")
        ws2.merge_cells(f"{start_col}6:{end_col}6")
        ws2[f"{start_col}4"].value = title
        ws2[f"{start_col}4"].font = font_kpi_sub
        ws2[f"{start_col}4"].alignment = Alignment(horizontal="center")
        ws2[f"{start_col}4"].fill = fill_kpi

        ws2[f"{start_col}5"].value = value
        ws2[f"{start_col}5"].font = font_kpi_num
        ws2[f"{start_col}5"].alignment = Alignment(horizontal="center")
        ws2[f"{start_col}5"].fill = fill_kpi

        ws2[f"{start_col}6"].value = sub
        ws2[f"{start_col}6"].font = Font(name="Calibri", size=8, color="475569")
        ws2[f"{start_col}6"].alignment = Alignment(horizontal="center")
        ws2[f"{start_col}6"].fill = fill_kpi

    ws2["A8"] = "HISTORIAL DIARIO DE INTERACCIONES DE ESTA LÍNEA"
    ws2["A8"].font = Font(name="Calibri", size=12, bold=True, color=NAVY)
    c_heads = ["Fecha", "Conversaciones Nuevas", "Mensajes Recibidos", "Mensajes Enviados", "Tiempo 1ª Respuesta Promedio", "Estado Operativo"]
    for idx, ch in enumerate(c_heads, start=1):
        c = ws2.cell(row=9, column=idx, value=ch)
        c.font = font_header
        c.fill = fill_header
        c.border = thin_border
        c.alignment = Alignment(horizontal="center")

    c_rows = [
        ["05-Nov-2026", 2, 59, 55, "1.3 seg", "Óptimo - 100% Bot"],
        ["06-Nov-2026", 1, 1, 2, "3.0 seg", "Óptimo - 100% Bot"]
    ]
    for r_i, r_d in enumerate(c_rows, start=10):
        for c_i, v in enumerate(r_d, start=1):
            cell = ws2.cell(row=r_i, column=c_i, value=v)
            cell.font = font_regular
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")
            if r_i % 2 == 1:
                cell.fill = fill_zebra

    for col in ws2.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws2.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # ── Hoja 3: Línea Individual Bonilla ──
    ws3 = wb.create_sheet(title="Entrada Bonilla Marketing")
    ws3.views.sheetView[0].showGridLines = True
    ws3["A1"] = "REPORTE ESPECÍFICO: NÚMERO DE ENTRADA +593 99 245 1085"
    ws3["A1"].font = font_title
    ws3["A2"] = "Bandeja: Grupo Bonilla Marketing (ID: 151924) | Canal: Meta Cloud API Oficial | Área: Ventas"
    ws3["A2"].font = font_subtitle

    bonilla_kpis = [
        ("A", "C", "TIEMPO 1ª RESPUESTA", "1 hora 42 min ⏳", "Promedio con atención humana"),
        ("D", "F", "TIEMPO DE RESOLUCIÓN", "2 horas 23 min", "Cierre por asesor comercial"),
        ("G", "I", "CONVERSACIONES TOTALES", "61 Chats", "Atendidas en la bandeja"),
        ("J", "L", "TASA DE EFECTIVIDAD", "60.0%", "15 respondidas <10s por bot inicial")
    ]
    for start_col, end_col, title, value, sub in bonilla_kpis:
        ws3.merge_cells(f"{start_col}4:{end_col}4")
        ws3.merge_cells(f"{start_col}5:{end_col}5")
        ws3.merge_cells(f"{start_col}6:{end_col}6")
        ws3[f"{start_col}4"].value = title
        ws3[f"{start_col}4"].font = font_kpi_sub
        ws3[f"{start_col}4"].alignment = Alignment(horizontal="center")
        ws3[f"{start_col}4"].fill = fill_kpi

        ws3[f"{start_col}5"].value = value
        ws3[f"{start_col}5"].font = font_kpi_num
        ws3[f"{start_col}5"].alignment = Alignment(horizontal="center")
        ws3[f"{start_col}5"].fill = fill_kpi

        ws3[f"{start_col}6"].value = sub
        ws3[f"{start_col}6"].font = Font(name="Calibri", size=8, color="475569")
        ws3[f"{start_col}6"].alignment = Alignment(horizontal="center")
        ws3[f"{start_col}6"].fill = fill_kpi

    for col in ws3.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws3.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # ── Hoja 4: Demanda por Etiquetas ──
    ws4 = wb.create_sheet(title="Demanda por Etiquetas")
    ws4.views.sheetView[0].showGridLines = True
    ws4["A1"] = "DISTRIBUCIÓN DE DEMANDA COMERCIAL (ETIQUETAS SEMÁNTICAS IA)"
    ws4["A1"].font = font_title
    ws4["A2"] = "Monitoreo del interés de clientes categorizado en Chatwoot Cloud"
    ws4["A2"].font = font_subtitle

    tag_headers = ["Etiqueta (Label)", "Departamento Ferretero", "Conversaciones", "Impacto Comercial", "Estrategia de Stock"]
    for idx, th in enumerate(tag_headers, start=1):
        cell = ws4.cell(row=4, column=idx, value=th)
        cell.font = font_header
        cell.fill = fill_header
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center")

    tag_rows = [
        ["asesor-humano", "Atención Personalizada", 22, "Clientes que solicitaron hablar con asesor", "Asignar vendedores dedicados en tienda"],
        ["pedido-web", "Comercio Digital & Carrito", 16, "Intención de compra formal o cotización", "Seguimiento y cierre inmediato con link de pago"],
        ["tiempo_de_respuesta", "Auditoría de SLA", 25, "Monitoreo activo de rapidez de respuesta", "Mantener FRT < 5 segundos en bot"],
        ["construccion", "Materiales Pesados", 2, "Cemento Holcim, Varillas Adelca, Arena", "Asegurar stock en Bodega Centro"],
        ["herramientas", "Herramientas Eléctricas", 1, "Taladros, Amoladoras Makita/DeWalt", "Promociones con accesorios y discos"],
        ["pinturas", "Pinturas y Acabados", 1, "Látex, Esmaltes, Brochas y Rodillos", "Impulsar ventas cruzadas en mostrador"]
    ]
    for r_idx, r_data in enumerate(tag_rows, start=5):
        for c_idx, val in enumerate(r_data, start=1):
            cell = ws4.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx == 3:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if r_idx % 2 == 1:
                cell.fill = fill_zebra

    for col in ws4.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws4.column_dimensions[col_letter].width = max(max_len + 4, 16)

    wb.save(file_path)
    print(f"[OK] Excel multi-hoja profesional generado en: {file_path}")


# ==============================================================================
# 2. GENERACIÓN DEL REPORTE WEB CON PESTAÑAS POR NÚMERO Y GRÁFICAS DINÁMICAS
# ==============================================================================

def create_executive_html(file_path):
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Informe Ejecutivo Multilínea | Ferretería Castor & Grupo Bonilla</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0f172a; color: #f8fafc; }
    @media print {
      body { background-color: #ffffff !important; color: #0f172a !important; }
      .no-print { display: none !important; }
      .print-shadow { box-shadow: none !important; border: 1px solid #e2e8f0 !important; }
      .print-dark-text { color: #0f172a !important; }
      .print-bg-white { background-color: #ffffff !important; }
    }
  </style>
</head>
<body class="p-4 md:p-8 min-h-screen">

  <div class="max-w-6xl mx-auto space-y-6">

    <!-- BARRA SUPERIOR EJECUTIVA -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center text-2xl shadow-lg shadow-amber-500/20">
          🦫
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-extrabold text-white tracking-tight">FERRETERÍA CASTOR & GRUPO BONILLA</h1>
            <span id="live-badge" class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> En Vivo con Chatwoot Cloud
            </span>
          </div>
          <p class="text-sm text-slate-400">Auditoría Diaria de Tiempos de Respuesta, Rendimiento de Bot y Clasificación de Clientes</p>
        </div>
      </div>

      <div class="flex items-center gap-3 no-print">
        <a href="/api/v1/reporte-ejecutivo/excel" download="Reporte_Ejecutivo_Tiempos_de_Respuesta_Chatwoot.xlsx" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-emerald-400 font-bold rounded-lg border border-emerald-500/30 shadow-lg flex items-center gap-2 transition text-sm">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          📥 Descargar Excel (.xlsx)
        </a>
        <button onclick="window.print()" class="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-lg shadow-lg shadow-blue-600/20 flex items-center gap-2 transition text-sm">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"/></svg>
          📄 Imprimir / Guardar en PDF
        </button>
      </div>
    </div>

    <!-- SELECTOR DE NÚMERO / BANDEJA DE ENTRADA (PESTAÑAS) -->
    <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-2 bg-slate-900 border border-slate-800 rounded-xl no-print">
      <div class="flex flex-wrap items-center gap-1.5">
        <span class="text-xs font-bold text-slate-400 px-3 uppercase tracking-wider">Filtrar por Entrada:</span>
        <button onclick="setInboxFilter('all')" id="tab-all" class="inbox-btn px-4 py-2 rounded-lg text-xs font-bold transition bg-blue-600 text-white shadow-sm">
          🌐 Consolidado (Todas las Entradas)
        </button>
        <button onclick="setInboxFilter('150556')" id="tab-150556" class="inbox-btn px-4 py-2 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition">
          📱 Línea Castor (+593 98 892 1136)
        </button>
        <button onclick="setInboxFilter('151924')" id="tab-151924" class="inbox-btn px-4 py-2 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition">
          💼 Línea Bonilla (+593 99 245 1085)
        </button>
      </div>
      <div class="text-[11px] text-slate-400 px-3 font-medium flex items-center gap-1">
        <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span>
        <span id="active-line-label">Mostrando: Consolidado Corporativo</span>
      </div>
    </div>

    <!-- TARJETAS DE KPIS DINÁMICAS -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      
      <!-- KPI 1 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1" id="kpi-title-1">1ª Respuesta (FRT)</div>
        <div id="kpi-val-1" class="text-3xl font-extrabold text-blue-400 flex items-baseline gap-2 print-dark-text">
          1.3 <span class="text-lg font-medium text-slate-400">segundos</span>
        </div>
        <div id="kpi-sub-1" class="mt-2 text-xs text-emerald-400 font-semibold flex items-center gap-1">
          ⚡ 100% SLA Inmediato con Bot Castor
        </div>
      </div>

      <!-- KPI 2 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1" id="kpi-title-2">Tiempo de Resolución</div>
        <div id="kpi-val-2" class="text-3xl font-extrabold text-amber-400 flex items-baseline gap-2 print-dark-text">
          2.0 <span class="text-lg font-medium text-slate-400">segundos</span>
        </div>
        <div id="kpi-sub-2" class="mt-2 text-xs text-amber-400 font-semibold flex items-center gap-1">
          ⏱️ Cierre de tickets automatizado
        </div>
      </div>

      <!-- KPI 3 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1" id="kpi-title-3">Ahorro de Tiempo con Bot</div>
        <div id="kpi-val-3" class="text-3xl font-extrabold text-emerald-400 flex items-baseline gap-2 print-dark-text">
          99.9%
        </div>
        <div id="kpi-sub-3" class="mt-2 text-xs text-emerald-400 font-semibold flex items-center gap-1">
          🚀 Eliminación de tiempos muertos
        </div>
      </div>

      <!-- KPI 4 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1" id="kpi-title-4">Mensajes en Período</div>
        <div id="kpi-val-4" class="text-3xl font-extrabold text-purple-400 flex items-baseline gap-2 print-dark-text">
          117 <span class="text-lg font-medium text-slate-400">msjs</span>
        </div>
        <div id="kpi-sub-4" class="mt-2 text-xs text-slate-400 font-medium">
          60 Recibidos | 57 Enviados
        </div>
      </div>

    </div>

    <!-- SECCIÓN DE GRÁFICAS -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

      <!-- GRÁFICA 1: Tiempos de Respuesta -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm print-shadow print-bg-white">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-base font-bold text-white print-dark-text" id="chart-frt-title">Velocidad de 1ª Respuesta por Número</h2>
            <p class="text-xs text-slate-400">Comparativa en segundos (Escala logarítmica de alta precisión)</p>
          </div>
          <span class="px-2 py-1 text-[10px] font-bold rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">Chatwoot API</span>
        </div>
        <div class="h-64">
          <canvas id="frtChart"></canvas>
        </div>
      </div>

      <!-- GRÁFICA 2: Demanda Comercial por Etiquetas -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm print-shadow print-bg-white">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-base font-bold text-white print-dark-text">Distribución de Consultas por Etiqueta</h2>
            <p class="text-xs text-slate-400">Clasificación de intenciones con Inteligencia Artificial</p>
          </div>
          <span class="px-2 py-1 text-[10px] font-bold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">NLP Semántico</span>
        </div>
        <div class="h-64">
          <canvas id="tagsChart"></canvas>
        </div>
      </div>

    </div>

    <!-- TABLA AUDITORÍA POR NÚMERO -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm print-shadow print-bg-white">
      <div class="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div>
          <h2 class="text-base font-bold text-white print-dark-text">Auditoría Individual por Número de Entrada</h2>
          <p class="text-xs text-slate-400">Registro verificado de cada línea conectada al sistema</p>
        </div>
        <span class="text-xs text-slate-400 font-medium">Período Auditado: Últimos 7 Días</span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-950/60 text-xs uppercase font-bold text-slate-400 tracking-wider border-b border-slate-800 print-bg-white print-dark-text">
            <tr>
              <th class="py-3.5 px-4">Bandeja / Entrada</th>
              <th class="py-3.5 px-4">Canal / Número</th>
              <th class="py-3.5 px-4 text-center">Conversaciones</th>
              <th class="py-3.5 px-4 text-center">Msjs Recibidos</th>
              <th class="py-3.5 px-4 text-center">Msjs Enviados</th>
              <th class="py-3.5 px-4 text-center">1ª Respuesta (FRT)</th>
              <th class="py-3.5 px-4 text-center">Resolución</th>
              <th class="py-3.5 px-4 text-right">Efectividad</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 text-xs" id="table-rows">
            <tr id="row-150556" class="hover:bg-slate-800/30 transition">
              <td class="py-4 px-4 font-bold text-white flex items-center gap-2 print-dark-text">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                WhatsApp (Ferretería Castor Principal)
              </td>
              <td class="py-4 px-4 font-mono text-slate-300">
                <span class="bg-slate-800 px-2 py-0.5 rounded text-[11px] text-blue-400 font-semibold">+593 98 892 1136</span>
              </td>
              <td class="py-4 px-4 text-center font-bold text-white print-dark-text">7</td>
              <td class="py-4 px-4 text-center text-blue-400 font-bold">60</td>
              <td class="py-4 px-4 text-center text-indigo-400 font-bold">57</td>
              <td class="py-4 px-4 text-center">
                <span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">1.3 seg ⚡</span>
              </td>
              <td class="py-4 px-4 text-center font-semibold text-emerald-400">2.0 seg</td>
              <td class="py-4 px-4 text-right font-extrabold text-emerald-400">100% Inmediato</td>
            </tr>

            <tr id="row-151924" class="hover:bg-slate-800/30 transition">
              <td class="py-4 px-4 font-bold text-white flex items-center gap-2 print-dark-text">
                <span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
                Grupo Bonilla Marketing (Ventas)
              </td>
              <td class="py-4 px-4 font-mono text-slate-300">
                <span class="bg-slate-800 px-2 py-0.5 rounded text-[11px] text-amber-400 font-semibold">+593 99 245 1085</span>
              </td>
              <td class="py-4 px-4 text-center font-bold text-white print-dark-text">61</td>
              <td class="py-4 px-4 text-center text-blue-400 font-bold">74</td>
              <td class="py-4 px-4 text-center text-indigo-400 font-bold">68</td>
              <td class="py-4 px-4 text-center">
                <span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">1 h 42 min</span>
              </td>
              <td class="py-4 px-4 text-center font-semibold text-amber-400">2 h 23 min</td>
              <td class="py-4 px-4 text-right font-bold text-amber-400">60% Híbrido</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>

  <!-- SCRIPT DE FILTRADO INTERACTIVO Y SINCRONIZACIÓN -->
  <script>
    let currentFilter = 'all';
    let cachedData = null;

    // Configuración de Gráficas Chart.js
    const ctxFrt = document.getElementById('frtChart').getContext('2d');
    window.chartFrt = new Chart(ctxFrt, {
      type: 'bar',
      data: {
        labels: ['Bot Castor (+593 98 892 1136)', 'Asesores Bonilla (+593 99 245 1085)'],
        datasets: [{
          label: 'Segundos',
          data: [1.3, 6120],
          backgroundColor: ['#3b82f6', '#f59e0b'],
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            type: 'logarithmic',
            ticks: {
              color: '#94a3b8',
              callback: v => v === 1 ? '1s' : (v === 60 ? '1m' : (v === 3600 ? '1h' : ''))
            },
            grid: { color: 'rgba(51, 65, 85, 0.4)' }
          },
          x: { ticks: { color: '#cbd5e1', font: { weight: 'bold' } }, grid: { display: false } }
        }
      }
    });

    const ctxTags = document.getElementById('tagsChart').getContext('2d');
    window.chartTags = new Chart(ctxTags, {
      type: 'doughnut',
      data: {
        labels: ['Asesor Humano', 'Pedido Web / Catálogo', 'Tiempo Respuesta', 'Construcción', 'Herramientas', 'Pinturas'],
        datasets: [{
          data: [15, 11, 17, 1, 1, 1],
          backgroundColor: ['#ec4899', '#06b6d4', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6'],
          borderWidth: 2,
          borderColor: '#0f172a'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'right', labels: { color: '#cbd5e1', font: { size: 11 }, padding: 10 } } },
        cutout: '65%'
      }
    });

    // Función de filtrado por entrada
    function setInboxFilter(inboxKey) {
      currentFilter = inboxKey;
      
      // Actualizar botones
      document.querySelectorAll('.inbox-btn').forEach(btn => {
        btn.className = 'inbox-btn px-4 py-2 rounded-lg text-xs font-bold text-slate-400 hover:text-white transition';
      });
      const activeBtn = document.getElementById(`tab-${inboxKey}`);
      if (activeBtn) {
        activeBtn.className = 'inbox-btn px-4 py-2 rounded-lg text-xs font-bold transition bg-blue-600 text-white shadow-sm';
      }

      const labelEl = document.getElementById('active-line-label');
      const r1 = document.getElementById('row-150556');
      const r2 = document.getElementById('row-151924');

      if (inboxKey === '150556') {
        labelEl.innerText = 'Mostrando: Entrada WhatsApp Castor (+593 98 892 1136)';
        document.getElementById('kpi-title-1').innerText = '1ª Respuesta (Línea Castor)';
        document.getElementById('kpi-val-1').innerHTML = '1.3 <span class="text-lg font-medium text-slate-400">segundos</span>';
        document.getElementById('kpi-sub-1').innerText = '⚡ 100% de consultas atendidas por Bot Castor';

        document.getElementById('kpi-title-2').innerText = 'Tiempo de Resolución';
        document.getElementById('kpi-val-2').innerHTML = '2.0 <span class="text-lg font-medium text-slate-400">segundos</span>';
        document.getElementById('kpi-sub-2').innerText = '⏱️ Resolución automatizada en WhatsApp';

        document.getElementById('kpi-title-3').innerText = 'Efectividad del Bot';
        document.getElementById('kpi-val-3').innerHTML = '100.0%';
        document.getElementById('kpi-sub-3').innerText = '🎯 7 de 7 conversaciones respondidas <10s';

        document.getElementById('kpi-title-4').innerText = 'Mensajes en esta Línea';
        document.getElementById('kpi-val-4').innerHTML = '117 <span class="text-lg font-medium text-slate-400">msjs</span>';
        document.getElementById('kpi-sub-4').innerText = '60 Recibidos | 57 Enviados';

        if (r1) r1.style.display = '';
        if (r2) r2.style.display = 'none';

        window.chartFrt.data.labels = ['Bot WhatsApp (+593 98 892 1136)'];
        window.chartFrt.data.datasets[0].data = [1.3];
        window.chartFrt.data.datasets[0].backgroundColor = ['#3b82f6'];
        window.chartFrt.update();

      } else if (inboxKey === '151924') {
        labelEl.innerText = 'Mostrando: Entrada Grupo Bonilla (+593 99 245 1085)';
        document.getElementById('kpi-title-1').innerText = '1ª Respuesta (Línea Bonilla)';
        document.getElementById('kpi-val-1').innerHTML = '1 h 42 <span class="text-lg font-medium text-slate-400">min</span>';
        document.getElementById('kpi-sub-1').innerText = '⏳ Tiempo promedio con agentes humanos';

        document.getElementById('kpi-title-2').innerText = 'Tiempo de Resolución';
        document.getElementById('kpi-val-2').innerHTML = '2 h 23 <span class="text-lg font-medium text-slate-400">min</span>';
        document.getElementById('kpi-sub-2').innerText = '🤝 Cierre manual de negociaciones';

        document.getElementById('kpi-title-3').innerText = 'Efectividad Híbrida';
        document.getElementById('kpi-val-3').innerHTML = '60.0%';
        document.getElementById('kpi-sub-3').innerText = '👥 Atención combinada con asesores';

        document.getElementById('kpi-title-4').innerText = 'Mensajes en esta Línea';
        document.getElementById('kpi-val-4').innerHTML = '142 <span class="text-lg font-medium text-slate-400">msjs</span>';
        document.getElementById('kpi-sub-4').innerText = '74 Recibidos | 68 Enviados';

        if (r1) r1.style.display = 'none';
        if (r2) r2.style.display = '';

        window.chartFrt.data.labels = ['Asesores Bonilla (+593 99 245 1085)'];
        window.chartFrt.data.datasets[0].data = [6120];
        window.chartFrt.data.datasets[0].backgroundColor = ['#f59e0b'];
        window.chartFrt.update();

      } else {
        labelEl.innerText = 'Mostrando: Consolidado Corporativo (Ambas Entradas)';
        document.getElementById('kpi-title-1').innerText = '1ª Respuesta (Línea Bot)';
        document.getElementById('kpi-val-1').innerHTML = '1.3 <span class="text-lg font-medium text-slate-400">segundos</span>';
        document.getElementById('kpi-sub-1').innerText = '⚡ 100% SLA Inmediato con Bot Castor';

        document.getElementById('kpi-title-2').innerText = '1ª Respuesta (Humana)';
        document.getElementById('kpi-val-2').innerHTML = '1 h 42 <span class="text-lg font-medium text-slate-400">min</span>';
        document.getElementById('kpi-sub-2').innerText = '⏳ Demoras por colas y horarios';

        document.getElementById('kpi-title-3').innerText = 'Ahorro de Tiempo con Bot';
        document.getElementById('kpi-val-3').innerHTML = '99.9%';
        document.getElementById('kpi-sub-3').innerText = '🚀 Reducción de espera para clientes';

        document.getElementById('kpi-title-4').innerText = 'Total Mensajes';
        document.getElementById('kpi-val-4').innerHTML = '259 <span class="text-lg font-medium text-slate-400">msjs</span>';
        document.getElementById('kpi-sub-4').innerText = '134 Recibidos | 125 Enviados';

        if (r1) r1.style.display = '';
        if (r2) r2.style.display = '';

        window.chartFrt.data.labels = ['Bot Castor (+593 98 892 1136)', 'Asesores Bonilla (+593 99 245 1085)'];
        window.chartFrt.data.datasets[0].data = [1.3, 6120];
        window.chartFrt.data.datasets[0].backgroundColor = ['#3b82f6', '#f59e0b'];
        window.chartFrt.update();
      }
    }

    // Sincronización en vivo cada 10s
    async function syncChatwoot() {
      try {
        const res = await fetch('/api/v1/reporte-ejecutivo/live-data');
        if (!res.ok) return;
        cachedData = await res.json();
        if (cachedData.status === 'connected') {
          if (cachedData.labels && window.chartTags) {
            const keys = ['asesor-humano', 'pedido-web', 'tiempo_de_respuesta', 'construccion', 'herramientas', 'pinturas'];
            window.chartTags.data.datasets[0].data = keys.map(k => cachedData.labels[k] || 0);
            window.chartTags.update();
          }
        }
      } catch (e) {
        console.debug('Live sync error:', e);
      }
    }
    syncChatwoot();
    setInterval(syncChatwoot, 10000);
  </script>

</body>
</html>
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Reporte HTML interactivo con pestanas generado en: {file_path}")

if __name__ == "__main__":
    base_dir = r"c:\Users\User\Desktop\KEVIN\ChatbotFlowise"
    excel_path = os.path.join(base_dir, "Reporte_Ejecutivo_Tiempos_de_Respuesta_Chatwoot.xlsx")
    html_path = os.path.join(base_dir, "reporte_ejecutivo_metricas.html")
    
    create_executive_excel(excel_path)
    create_executive_html(html_path)
