import 'cart_item.dart';

class OrderRequest {
  final String customerName;
  final String customerPhone;
  final String deliveryType; // 'pickup' | 'delivery'
  final String? deliveryAddress;
  final String sucursal;
  final String paymentMethod; // 'efectivo' | 'transferencia' | 'tarjeta'
  final String? notes;
  final List<CartItem> items;

  OrderRequest({
    required this.customerName,
    required this.customerPhone,
    this.deliveryType = 'pickup',
    this.deliveryAddress,
    this.sucursal = 'Centro',
    this.paymentMethod = 'efectivo',
    this.notes,
    required this.items,
  });

  Map<String, dynamic> toJson() {
    return {
      'customer_name': customerName,
      'customer_phone': customerPhone,
      'delivery_type': deliveryType,
      'delivery_address': deliveryAddress,
      'sucursal': sucursal,
      'payment_method': paymentMethod,
      'notes': notes,
      'items': items.map((i) => i.toJson()).toList(),
    };
  }
}
