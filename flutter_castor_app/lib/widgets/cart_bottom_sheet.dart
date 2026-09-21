import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/cart_provider.dart';
import '../models/order_request.dart';
import '../services/api_service.dart';

class CartBottomSheet extends StatefulWidget {
  const CartBottomSheet({Key? key}) : super(key: key);

  @override
  State<CartBottomSheet> createState() => _CartBottomSheetState();
}

class _CartBottomSheetState extends State<CartBottomSheet> {
  String _deliveryType = 'pickup'; // 'pickup' | 'delivery'
  String _paymentMethod = 'efectivo'; // 'efectivo' | 'transferencia' | 'tarjeta'
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _addressController = TextEditingController();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    final cart = Provider.of<CartProvider>(context, listen: false);
    _nameController.text = cart.customerName;
    _phoneController.text = cart.customerPhone;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  void _handleCheckout() async {
    final cart = Provider.of<CartProvider>(context, listen: false);
    if (cart.items.isEmpty) return;

    if (_nameController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor ingresa tu nombre completo.')),
      );
      return;
    }

    if (_phoneController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor ingresa tu número de WhatsApp.')),
      );
      return;
    }

    if (_deliveryType == 'delivery' && _addressController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor ingresa la dirección de entrega.')),
      );
      return;
    }

    setState(() => _isLoading = true);

    final orderReq = OrderRequest(
      customerName: _nameController.text.trim(),
      customerPhone: _phoneController.text.trim(),
      deliveryType: _deliveryType,
      deliveryAddress: _deliveryType == 'delivery' ? _addressController.text.trim() : null,
      sucursal: cart.selectedSucursal,
      paymentMethod: _paymentMethod,
      items: cart.items.values.toList(),
    );

    final result = await ApiService.submitOrder(orderReq);
    setState(() => _isLoading = false);

    if (result['success'] == true) {
      final orderNumber = result['order_number'];
      final total = result['total'];
      cart.clearCart();
      if (!mounted) return;
      Navigator.pop(context);

      // Mostrar diálogo de éxito con retorno directo a WhatsApp
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          contentPadding: const EdgeInsets.all(24),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 60,
                height: 60,
                decoration: BoxDecoration(
                  color: Colors.green.shade100,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(Icons.check_circle, color: Colors.green, size: 36),
              ),
              const SizedBox(height: 16),
              const Text(
                '¡Pedido Confirmado! 🎉',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'N° de Pedido: $orderNumber\nTotal: \$${total.toStringAsFixed(2)}',
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.grey, height: 1.4),
              ),
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () async {
                    Navigator.pop(ctx);
                    final waUrl = Uri.parse('whatsapp://send?phone=593988921136&text=Hola,%20acabo%20de%20realizar%20el%20pedido%20$orderNumber');
                    if (await canLaunchUrl(waUrl)) {
                      await launchUrl(waUrl);
                    }
                  },
                  icon: const Icon(Icons.chat),
                  label: const Text('Volver a WhatsApp'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0F766E),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    } else {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message'] ?? 'Error al procesar pedido')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = Provider.of<CartProvider>(context);

    return Container(
      height: MediaQuery.of(context).size.height * 0.85,
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Header Drawer
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const Icon(Icons.shopping_cart, color: Color(0xFF0F766E)),
                    const SizedBox(width: 8),
                    Text(
                      'Tu Carrito (${cart.totalItemCount})',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                  constraints: const Size(32, 32),
                  padding: EdgeInsets.zero,
                ),
              ],
            ),
          ),

          // Lista de Items y Formulario de Checkout
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                // Items en Carrito
                ...cart.items.values.map(
                  (item) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.product.name,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                              ),
                              Text(
                                '${item.quantity}x \$${item.product.price.toStringAsFixed(2)}',
                                style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                              ),
                            ],
                          ),
                        ),
                        Text(
                          '\$${item.subtotal.toStringAsFixed(2)}',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ),

                const Divider(height: 24),

                // Modalidad de Entrega
                const Text('Modalidad de Entrega', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: ChoiceChip(
                        label: const Text('📍 Retiro en Sucursal'),
                        selected: _deliveryType == 'pickup',
                        onSelected: (val) => setState(() => _deliveryType = 'pickup'),
                        selectedColor: const Color(0xFF0F766E).withOpacity(0.15),
                        labelStyle: TextStyle(
                          color: _deliveryType == 'pickup' ? const Color(0xFF0F766E) : Colors.grey.shade700,
                          fontWeight: FontWeight.w600,
                          fontSize: 11,
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ChoiceChip(
                        label: const Text('🛵 A Domicilio'),
                        selected: _deliveryType == 'delivery',
                        onSelected: (val) => setState(() => _deliveryType = 'delivery'),
                        selectedColor: const Color(0xFF0F766E).withOpacity(0.15),
                        labelStyle: TextStyle(
                          color: _deliveryType == 'delivery' ? const Color(0xFF0F766E) : Colors.grey.shade700,
                          fontWeight: FontWeight.w600,
                          fontSize: 11,
                        ),
                      ),
                    ),
                  ],
                ),

                if (_deliveryType == 'delivery') ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: _addressController,
                    decoration: InputDecoration(
                      labelText: 'Dirección de Entrega',
                      hintText: 'Ej: Av. 10 de Agosto y Colón, Edif. 4',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    ),
                    style: const TextStyle(fontSize: 12),
                  ),
                ],

                const SizedBox(height: 16),

                // Datos de Contacto
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _nameController,
                        decoration: InputDecoration(
                          labelText: 'Tu Nombre',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: TextField(
                        controller: _phoneController,
                        keyboardType: TextInputType.phone,
                        decoration: InputDecoration(
                          labelText: 'WhatsApp',
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        ),
                        style: const TextStyle(fontSize: 12),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 16),

                // Forma de Pago
                const Text('Forma de Pago', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _paymentMethod,
                  decoration: InputDecoration(
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'efectivo', child: Text('💵 Efectivo contra entrega', style: TextStyle(fontSize: 12))),
                    DropdownMenuItem(value: 'transferencia', child: Text('🏦 Transferencia Bancaria', style: TextStyle(fontSize: 12))),
                    DropdownMenuItem(value: 'tarjeta', child: Text('💳 Tarjeta de Crédito / Débito', style: TextStyle(fontSize: 12))),
                  ],
                  onChanged: (val) => setState(() => _paymentMethod = val ?? 'efectivo'),
                ),

                const SizedBox(height: 20),

                // Resumen de Totales
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Subtotal:', style: TextStyle(fontSize: 12, color: Colors.grey)),
                          Text('\$${cart.subtotal.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('IVA (15%):', style: TextStyle(fontSize: 12, color: Colors.grey)),
                          Text('\$${cart.tax.toStringAsFixed(2)}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        ],
                      ),
                      const Divider(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Total a Pagar:', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                          Text(
                            '\$${cart.total.toStringAsFixed(2)}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F766E)),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Botón de Confirmación
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: Colors.grey.shade200)),
            ),
            child: SizedBox(
              width: double.infinity,
              height: 48,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleCheckout,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0F766E),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  elevation: 0,
                ),
                child: _isLoading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Confirmar Pedido y Recibir Comprobante', style: TextStyle(fontWeight: FontWeight.bold)),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
