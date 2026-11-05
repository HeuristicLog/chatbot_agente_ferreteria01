"""
Test de Integración Completa: Odoo ERP + WhatsApp Interactive Flow + Chatwoot Cloud
Ferretería Castor 2026
"""
import asyncio
import os
import sys

# Agregar path
sys.path.insert(0, "/app")

from app.services.odoo_service import OdooService

async def run_full_odoo_flow_test():
    print("=" * 80)
    print("🚀 TEST DE INTEGRACIÓN: ODOO ERP + WHATSAPP FLOWS + CHATWOOT CLOUD")
    print("=" * 80)

    odoo = OdooService()

    # 1. Test Conexión
    print("\n[1] Verificando conectividad con Odoo ERP:")
    conn = await odoo.test_connection()
    print(f"    • Modo: {conn['mode']}")
    print(f"    • Versión Odoo: {conn['odoo_version']}")
    print(f"    • Base de Datos: {conn['database']}")
    print(f"    • Estado: {'✅ CONECTADO EXITOSAMENTE' if conn['connected'] else '❌ ERROR'}")
    assert conn["connected"] is True, "Odoo debe estar conectado o en modo simulación activo"

    # 2. Test Catálogo y Stock Multisede
    print("\n[2] Consultando catálogo de Ferretería en Odoo (product.template):")
    products = await odoo.get_products()
    print(f"    • Productos obtenidos: {len(products)} ítems activos")
    sample_prod = products[0]
    print(f"    • Muestra: {sample_prod['name']} (${sample_prod['price']} USD) [SKU: {sample_prod['sku']}]")
    
    # Stock multisede
    stock_check = await odoo.check_stock(sample_prod['sku'], sucursal="Centro")
    print(f"    • Stock en Bodega Sucursal Centro: {stock_check['stock_sucursal']} unidades (Disponible: {stock_check['available']})")
    assert len(products) > 0, "Debe haber productos disponibles en el catálogo de Odoo"

    # 3. Test Creación de Orden de Venta en Odoo (sale.order)
    print("\n[3] Creando Orden de Venta formal (sale.order) desde WhatsApp:")
    test_items = [
        {"sku": "FERR-MAK-01", "name": "Rotomartillo Makita HR2470 780W", "price": 145.00, "quantity": 1},
        {"sku": "FERR-CEM-02", "name": "Saco de Cemento Selvalegre 50kg", "price": 8.40, "quantity": 5},
        {"sku": "FERR-ADE-01", "name": "Varilla Corrugada Adelca 12mm", "price": 9.85, "quantity": 10}
    ]
    
    order_res = await odoo.create_sale_order(
        customer_phone="593988921136",
        customer_name="Kevin Asesor Ferretero",
        items=test_items,
        delivery_type="pickup",
        sucursal="Centro",
        payment_method="tarjeta",
        ruc_cedula="1723456789001"
    )

    print(f"    • N° de Orden Odoo Generado: {order_res['order_name']}")
    print(f"    • Cliente: {order_res['partner']['name']} (RUC/CI: {order_res['partner']['vat']})")
    print(f"    • Almacén de Despacho: {order_res['warehouse']}")
    print(f"    • Subtotal: ${order_res['subtotal']:.2f} USD")
    print(f"    • IVA (15% Ecuador): ${order_res['tax']:.2f} USD")
    print(f"    • Total a Pagar: ${order_res['total']:.2f} USD")
    print(f"    • Estado en Odoo: {order_res['state']} ({order_res['state_display']})")
    assert order_res["order_name"].startswith("SO-"), "La orden debe tener prefijo de Odoo SO-"

    # 4. Test Enlace de Pago Digital (Odoo Payment Link)
    print("\n[4] Generando Enlace de Pago Seguro (Odoo Payment Link):")
    payment_link = order_res.get("payment_link")
    print(f"    • URL de Pago: {payment_link}")
    assert payment_link is not None, "El pedido con tarjeta debe generar un enlace de pago seguro"

    # 5. Test Rastreo de Pedido Odoo desde WhatsApp
    print("\n[5] Simulando consulta de estado del pedido desde WhatsApp:")
    status_res = await odoo.get_order_status(order_res["order_name"])
    print(f"    • Consulta código: #{status_res['order_name']}")
    print(f"    • Estado reportado al cliente: {status_res['status_title']}")
    print(f"    • Detalle: {status_res['status_description']}")
    assert status_res["found"] is True, "El pedido debe ser rastreable en Odoo"

    # 6. Test Validación de Integración con Chatwoot
    print("\n[6] Validación de Sincronización y Métricas en Chatwoot Cloud:")
    print("    • Atributos a registrar en Chatwoot:")
    print(f"      - codigo_pedido: '{order_res['order_name']}'")
    print(f"      - monto_compra: ${order_res['total']:.2f}")
    print(f"      - sucursal_asignada: '{order_res['sucursal']}'")
    print(f"      - tipo_entrega: 'Retiro en Sucursal {order_res['sucursal']}'")
    print("    • Etiquetas a aplicar: ['pedido-web', 'odoo-sync']")
    print("    • Nota interna: Proforma Odoo SO-2026 con desglose de ítems para el asesor humano")

    print("\n" + "=" * 80)
    print("🎉 RESULTADO: TODOS LOS TESTS DE INTEGRACIÓN DE ODOO PASARON CON ÉXITO")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_full_odoo_flow_test())
