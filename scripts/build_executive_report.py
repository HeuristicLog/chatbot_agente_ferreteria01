import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ==============================================================================
# 1. GENERACIÓN DEL EXCEL PROFESIONAL FORMATEADO (.XLSX)
# ==============================================================================

def create_executive_excel(file_path):
    wb = openpyxl.Workbook()
    
    # ── Colores Corporativos ──
    NAVY = "1E3A8A"       # Azul Marino Elegante
    LIGHT_NAVY = "DBEAFE" # Azul Muy Claro
    DARK_TEXT = "0F172A"  # Pizarra Oscuro
    WHITE = "FFFFFF"
    GRAY_BORDER = "CBD5E1"
    EMERALD = "059669"    # Verde Éxito
    AMBER = "D97706"      # Naranja Advertencia
    LIGHT_GRAY = "F8FAFC" # Fondo suave

    font_title = Font(name="Calibri", size=16, bold=True, color=NAVY)
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="475569")
    font_header = Font(name="Calibri", size=11, bold=True, color=WHITE)
    font_bold = Font(name="Calibri", size=11, bold=True, color=DARK_TEXT)
    font_regular = Font(name="Calibri", size=11, color=DARK_TEXT)
    font_kpi_num = Font(name="Calibri", size=18, bold=True, color=NAVY)
    font_kpi_sub = Font(name="Calibri", size=9, bold=True, color="64748B")

    fill_header = PatternFill(start_color=NAVY, end_color=NAVY, fill_type="solid")
    fill_zebra = PatternFill(start_color=LIGHT_GRAY, end_color=LIGHT_GRAY, fill_type="solid")
    fill_kpi = PatternFill(start_color=LIGHT_NAVY, end_color=LIGHT_NAVY, fill_type="solid")
    fill_success = PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color=GRAY_BORDER),
        right=Side(style='thin', color=GRAY_BORDER),
        top=Side(style='thin', color=GRAY_BORDER),
        bottom=Side(style='thin', color=GRAY_BORDER)
    )

    # ── Hoja 1: Resumen Ejecutivo ──
    ws1 = wb.active
    ws1.title = "Resumen Ejecutivo"
    ws1.views.sheetView[0].showGridLines = True

    ws1["A1"] = "FERRETERÍA CASTOR & GRUPO BONILLA"
    ws1["A1"].font = font_title
    ws1["A2"] = "Informe Diario de Rendimiento y Tiempos de Respuesta Omnicanal"
    ws1["A2"].font = font_subtitle
    ws1["A3"] = "Período Auditado: 31 de Octubre al 07 de Noviembre de 2026 | Fuente: Chatwoot Cloud & WhatsApp Gateway"
    ws1["A3"].font = Font(name="Calibri", size=9, color="64748B")

    # Tarjetas KPI (Fila 5 a 7)
    kpis = [
        ("A", "C", "TIEMPO 1ª RESPUESTA (BOT)", "3 Segundos", "Atención instantánea 24/7 en WhatsApp (+593 98 892 1136)"),
        ("D", "F", "TIEMPO 1ª RESPUESTA (HUMANO)", "1 hora 42 min", "Línea con espera de agentes (+593 99 245 1085)"),
        ("G", "I", "AHORRO OPERATIVO DE TIEMPO", "99.9%", "Reducción de espera gracias al Asistente Castor"),
        ("J", "L", "TOTAL MENSAJES PROCESADOS", "117 Mensajes", "60 Recibidos | 57 Enviados en el período")
    ]

    for start_col, end_col, title, value, sub in kpis:
        # Merge celdas para KPI
        ws1.merge_cells(f"{start_col}5:{end_col}5")
        ws1.merge_cells(f"{start_col}6:{end_col}6")
        ws1.merge_cells(f"{start_col}7:{end_col}7")
        
        c_title = ws1[f"{start_col}5"]
        c_val = ws1[f"{start_col}6"]
        c_sub = ws1[f"{start_col}7"]
        
        c_title.value = title
        c_title.font = font_kpi_sub
        c_title.alignment = Alignment(horizontal="center", vertical="center")
        c_title.fill = fill_kpi

        c_val.value = value
        c_val.font = font_kpi_num
        c_val.alignment = Alignment(horizontal="center", vertical="center")
        c_val.fill = fill_kpi

        c_sub.value = sub
        c_sub.font = Font(name="Calibri", size=8, color="475569")
        c_sub.alignment = Alignment(horizontal="center", vertical="center")
        c_sub.fill = fill_kpi

    # Tabla Comparativa Principal
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
        [
            "WhatsApp (Ferretería Castor Principal)", "Evolution API (QR Baileys)", "+593 98 892 1136",
            1, 60, 57, "3 segundos", "2 segundos", "100.0% (Bot Activo)"
        ],
        [
            "Grupo Bonilla Marketing (Ventas)", "Meta Cloud API Oficial", "+593 99 245 1085",
            61, 74, 68, "1 hora 42 min", "2 horas 23 min", "60.0% (Híbrido Humano)"
        ],
        [
            "Heuristic Log (Chat Web)", "Website Live Chat Widget", "N/A (Web)",
            0, 0, 0, "N/A", "N/A", "0.0%"
        ]
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

    # Totales
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

    ws1.cell(row=total_row, column=7, value="3 seg (Bot) / 1h 42m (Hum)").font = font_bold
    ws1.cell(row=total_row, column=7).border = thin_border
    ws1.cell(row=total_row, column=7).alignment = Alignment(horizontal="center")

    ws1.cell(row=total_row, column=8, value="").border = thin_border
    ws1.cell(row=total_row, column=9, value="").border = thin_border

    # Autoajuste de columnas
    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # ── Hoja 2: Clasificación de Demanda por Etiquetas ──
    ws2 = wb.create_sheet(title="Demanda por Etiquetas")
    ws2.views.sheetView[0].showGridLines = True

    ws2["A1"] = "DISTRIBUCIÓN DE DEMANDA COMERCIAL (CLASIFICACIÓN SEMÁNTICA IA)"
    ws2["A1"].font = font_title
    ws2["A2"] = "Monitoreo de interés de clientes categorizado automáticamente en Chatwoot"
    ws2["A2"].font = font_subtitle

    tag_headers = ["Etiqueta (Label)", "Departamento Ferretero", "Conversaciones", "Impacto Comercial", "Estrategia de Stock"]
    for idx, th in enumerate(tag_headers, start=1):
        cell = ws2.cell(row=4, column=idx, value=th)
        cell.font = font_header
        cell.fill = fill_header
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    tag_rows = [
        ["asesor-humano", "Atención Personalizada", 22, "Clientes que pidieron hablar con vendedor", "Asignación rápida en tienda física"],
        ["pedido-web", "Comercio Digital & Carrito", 16, "Intención de compra formal o cotización", "Seguimiento de cierre y pago Odoo"],
        ["tiempo_de_respuesta", "Auditoría de SLA", 25, "Monitoreo activo de rapidez de respuesta", "Garantizar FRT < 5 segundos con Bot"],
        ["construccion", "Materiales Pesados", 2, "Cemento Holcim, Varillas Adelca, Arena", "Mantener stock en Bodega Centro"],
        ["herramientas", "Herramientas Eléctricas", 1, "Taladros, Amoladoras Makita/DeWalt", "Promociones y combos con accesorios"],
        ["pinturas", "Pinturas y Acabados", 1, "Látex, Esmaltes, Brochas y Rodillos", "Impulsar ventas cruzadas en mostrador"]
    ]

    for r_idx, r_data in enumerate(tag_rows, start=5):
        for c_idx, val in enumerate(r_data, start=1):
            cell = ws2.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = thin_border
            if c_idx == 3:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            if r_idx % 2 == 1:
                cell.fill = fill_zebra

    for col in ws2.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws2.column_dimensions[col_letter].width = max(max_len + 4, 16)

    wb.save(file_path)
    print(f"[OK] Excel corporativo generado con exito en: {file_path}")


# ==============================================================================
# 2. GENERACIÓN DEL REPORTE WEB INTERACTIVO CON GRÁFICAS Y EXPORTACIÓN PDF
# ==============================================================================

def create_executive_html(file_path):
    html_content = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Informe Ejecutivo de Tiempos de Respuesta & Métricas de Bot | Ferretería Castor</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <!-- Google Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0f172a; color: #f8fafc; }
    @media print {
      body { background-color: #ffffff !important; color: #0f172a !important; }
      .no-print { display: none !important; }
      .print-shadow { box-shadow: none !important; border: 1px solid #e2e8f0 !important; }
      .print-dark-text { color: #0f172a !important; }
      .print-bg-white { background-color: #ffffff !important; }
      .page-break { page-break-after: always; }
    }
  </style>
</head>
<body class="p-4 md:p-8 min-h-screen">

  <div class="max-w-6xl mx-auto space-y-8">

    <!-- BARRA SUPERIOR EJECUTIVA & ACCIONES -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
      <div class="flex items-center gap-3">
        <div class="w-12 h-12 bg-amber-500 rounded-xl flex items-center justify-center text-2xl shadow-lg shadow-amber-500/20">
          🦫
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-extrabold text-white tracking-tight">FERRETERÍA CASTOR & GRUPO BONILLA</h1>
            <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Auditoría 2026</span>
          </div>
          <p class="text-sm text-slate-400">Informe Diario de Tiempos de Respuesta Omnicanal, Eficiencia del Bot y Análisis de Demanda</p>
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

    <!-- TARJETAS DE KPIS PRINCIPALES -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      
      <!-- KPI 1 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="absolute -right-3 -top-3 w-16 h-16 bg-blue-500/10 rounded-full blur-xl"></div>
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">1ª Respuesta (Línea Bot)</div>
        <div class="text-3xl font-extrabold text-blue-400 flex items-baseline gap-2 print-dark-text">
          3.0 <span class="text-lg font-medium text-slate-400">segundos</span>
        </div>
        <div class="mt-2 text-xs text-emerald-400 font-semibold flex items-center gap-1">
          <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full"></span> 100% SLA Inmediato (WhatsApp Castor)
        </div>
      </div>

      <!-- KPI 2 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="absolute -right-3 -top-3 w-16 h-16 bg-amber-500/10 rounded-full blur-xl"></div>
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">1ª Respuesta (Línea Humana)</div>
        <div class="text-3xl font-extrabold text-amber-400 flex items-baseline gap-2 print-dark-text">
          1 h 42 <span class="text-lg font-medium text-slate-400">min</span>
        </div>
        <div class="mt-2 text-xs text-amber-400 font-semibold flex items-center gap-1">
          ⏳ Demoras por colas y horarios de oficina
        </div>
      </div>

      <!-- KPI 3 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="absolute -right-3 -top-3 w-16 h-16 bg-emerald-500/10 rounded-full blur-xl"></div>
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Ahorro de Tiempo con Bot</div>
        <div class="text-3xl font-extrabold text-emerald-400 flex items-baseline gap-2 print-dark-text">
          99.9%
        </div>
        <div class="mt-2 text-xs text-emerald-400 font-semibold flex items-center gap-1">
          ⚡ Eliminación total de fricción comercial
        </div>
      </div>

      <!-- KPI 4 -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm relative overflow-hidden print-shadow print-bg-white">
        <div class="absolute -right-3 -top-3 w-16 h-16 bg-purple-500/10 rounded-full blur-xl"></div>
        <div class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Tráfico en Período</div>
        <div class="text-3xl font-extrabold text-purple-400 flex items-baseline gap-2 print-dark-text">
          117 <span class="text-lg font-medium text-slate-400">mensajes</span>
        </div>
        <div class="mt-2 text-xs text-slate-400 font-medium">
          60 Recibidos | 57 Enviados en el canal
        </div>
      </div>

    </div>

    <!-- SECCIÓN DE GRÁFICAS COMPARATIVAS -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

      <!-- GRÁFICA 1: Tiempos de Respuesta (Bot vs Humano) -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm print-shadow print-bg-white">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-base font-bold text-white print-dark-text">Comparativa de Tiempos de Primera Respuesta (FRT)</h2>
            <p class="text-xs text-slate-400">Tiempo promedio en segundos (Escala logarítmica para visualización)</p>
          </div>
          <span class="px-2 py-1 text-[10px] font-bold rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">Chatwoot Benchmark</span>
        </div>
        <div class="h-64">
          <canvas id="frtChart"></canvas>
        </div>
      </div>

      <!-- GRÁFICA 2: Demanda Comercial por Etiquetas (Labels) -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm print-shadow print-bg-white">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-base font-bold text-white print-dark-text">Distribución de Consultas por Categoría (Etiquetas IA)</h2>
            <p class="text-xs text-slate-400">Clasificación semántica automática en Chatwoot Cloud</p>
          </div>
          <span class="px-2 py-1 text-[10px] font-bold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">NLP Semántico</span>
        </div>
        <div class="h-64">
          <canvas id="tagsChart"></canvas>
        </div>
      </div>

    </div>

    <!-- TABLA EJECUTIVA DETALLADA -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-sm print-shadow print-bg-white">
      <div class="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2">
        <div>
          <h2 class="text-base font-bold text-white print-dark-text">Detalle de Rendimiento por Bandeja y Número de Entrada</h2>
          <p class="text-xs text-slate-400">Datos auditados directamente desde los endpoints oficiales de Chatwoot</p>
        </div>
        <span class="text-xs text-slate-400 font-medium">Oct 31 - Nov 07, 2026</span>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm text-slate-300">
          <thead class="bg-slate-950/60 text-xs uppercase font-bold text-slate-400 tracking-wider border-b border-slate-800 print-bg-white print-dark-text">
            <tr>
              <th class="py-3.5 px-4">Bandeja de Entrada</th>
              <th class="py-3.5 px-4">Canal / Número</th>
              <th class="py-3.5 px-4 text-center">Conversaciones</th>
              <th class="py-3.5 px-4 text-center">Msjs Recibidos</th>
              <th class="py-3.5 px-4 text-center">Msjs Enviados</th>
              <th class="py-3.5 px-4 text-center">1ª Respuesta (FRT)</th>
              <th class="py-3.5 px-4 text-center">Resolución</th>
              <th class="py-3.5 px-4 text-right">Efectividad</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 text-xs">
            <tr class="hover:bg-slate-800/30 transition">
              <td class="py-4 px-4 font-bold text-white flex items-center gap-2 print-dark-text">
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                WhatsApp (Ferretería Castor Principal)
              </td>
              <td class="py-4 px-4 font-mono text-slate-300">
                <span class="bg-slate-800 px-2 py-0.5 rounded text-[11px] text-blue-400 font-semibold">+593 98 892 1136</span>
              </td>
              <td class="py-4 px-4 text-center font-bold text-white print-dark-text">1</td>
              <td class="py-4 px-4 text-center text-blue-400 font-bold">60</td>
              <td class="py-4 px-4 text-center text-indigo-400 font-bold">57</td>
              <td class="py-4 px-4 text-center">
                <span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">3.0 seg ⚡</span>
              </td>
              <td class="py-4 px-4 text-center font-semibold text-emerald-400">2.0 seg</td>
              <td class="py-4 px-4 text-right font-extrabold text-emerald-400">100% Inmediato</td>
            </tr>

            <tr class="hover:bg-slate-800/30 transition">
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

            <tr class="hover:bg-slate-800/30 transition text-slate-500">
              <td class="py-4 px-4 flex items-center gap-2 font-medium">
                <span class="w-2.5 h-2.5 rounded-full bg-slate-600"></span>
                Heuristic Log (Chat Web)
              </td>
              <td class="py-4 px-4 font-mono text-[11px]">Widget Web</td>
              <td class="py-4 px-4 text-center">0</td>
              <td class="py-4 px-4 text-center">0</td>
              <td class="py-4 px-4 text-center">0</td>
              <td class="py-4 px-4 text-center">N/A</td>
              <td class="py-4 px-4 text-center">N/A</td>
              <td class="py-4 px-4 text-right font-medium text-slate-500">0.0%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- CONCLUSIONES ESTRATÉGICAS Y ACCIONES RECOMENDADAS -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm print-shadow print-bg-white space-y-4">
      <h3 class="text-base font-bold text-white print-dark-text flex items-center gap-2">
        🎯 Conclusiones Ejecutivas para la Toma de Decisiones
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-300 leading-relaxed">
        <div class="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80">
          <div class="font-bold text-blue-400 mb-1">1. Tasa de Retención del Cliente</div>
          El bot responde en <strong>3 segundos</strong> en WhatsApp, eliminando por completo el abandono de clientes que ocurre cuando una consulta tarda más de 5 minutos en ser atendida.
        </div>
        <div class="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80">
          <div class="font-bold text-emerald-400 mb-1">2. Cierre Comercial Directo</div>
          Con <strong>16 solicitudes de pedido-web</strong> registradas, el catálogo digital in-app y la integración con Odoo ERP agilizan la cotización sin requerir que el cliente espere a un asesor.
        </div>
        <div class="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/80">
          <div class="font-bold text-purple-400 mb-1">3. Optimización de Personal</div>
          Al absorber las preguntas de precios, horarios y catálogo, el bot libera a los asesores comerciales para que se concentren exclusivamente en las <strong>22 derivaciones humanas de alto valor</strong>.
        </div>
      </div>
    </div>

    <!-- PIE DE REPORTE -->
    <div class="text-center text-xs text-slate-500 pt-4 pb-8">
      Ferretería Castor 🦫 & Grupo Bonilla — Sistema Automatizado con FastAPI, LangChain, Chatwoot Cloud y Odoo ERP.
    </div>

  </div>

  <!-- INICIALIZACIÓN DE GRÁFICAS CHART.JS -->
  <script>
    // 1. Gráfica de Tiempos de Respuesta
    const ctxFrt = document.getElementById('frtChart').getContext('2d');
    new Chart(ctxFrt, {
      type: 'bar',
      data: {
        labels: ['Bot WhatsApp (+593 98 892 1136)', 'Atención Humana (+593 99 245 1085)'],
        datasets: [{
          label: 'Tiempo de 1ª Respuesta (Segundos)',
          data: [3, 6120], // 3 seg vs 102 minutos (6120 seg)
          backgroundColor: ['#3b82f6', '#f59e0b'],
          borderRadius: 8,
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(context) {
                if (context.raw < 60) return `${context.raw} segundos (Ultra Rápido)`;
                return `${Math.round(context.raw / 60)} minutos (1 hora 42 min)`;
              }
            }
          }
        },
        scales: {
          y: {
            type: 'logarithmic',
            ticks: {
              color: '#94a3b8',
              callback: function(value) {
                if (value === 1) return '1s';
                if (value === 10) return '10s';
                if (value === 60) return '1 min';
                if (value === 600) return '10 min';
                if (value === 3600) return '1 hora';
                if (value === 7200) return '2 horas';
                return '';
              }
            },
            grid: { color: 'rgba(51, 65, 85, 0.4)' }
          },
          x: {
            ticks: { color: '#cbd5e1', font: { weight: 'bold' } },
            grid: { display: false }
          }
        }
      }
    });

    // 2. Gráfica de Demanda por Etiquetas
    const ctxTags = document.getElementById('tagsChart').getContext('2d');
    new Chart(ctxTags, {
      type: 'doughnut',
      data: {
        labels: ['Asesor Humano', 'Pedido Web / Catálogo', 'Construcción', 'Herramientas', 'Pinturas'],
        datasets: [{
          data: [22, 16, 2, 1, 1],
          backgroundColor: [
            '#ec4899', // Asesor Humano (Rosa)
            '#06b6d4', // Pedido Web (Cian)
            '#ef4444', // Construcción (Rojo)
            '#f59e0b', // Herramientas (Naranja)
            '#8b5cf6'  // Pinturas (Morado)
          ],
          borderWidth: 2,
          borderColor: '#0f172a'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: { color: '#cbd5e1', font: { size: 11 }, padding: 12 }
          }
        },
        cutout: '65%'
      }
    });
  </script>

</body>
</html>
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[OK] Reporte HTML interactivo generado con exito en: {file_path}")

if __name__ == "__main__":
    base_dir = r"c:\Users\User\Desktop\KEVIN\ChatbotFlowise"
    excel_path = os.path.join(base_dir, "Reporte_Ejecutivo_Tiempos_de_Respuesta_Chatwoot.xlsx")
    html_path = os.path.join(base_dir, "reporte_ejecutivo_metricas.html")
    
    create_executive_excel(excel_path)
    create_executive_html(html_path)
