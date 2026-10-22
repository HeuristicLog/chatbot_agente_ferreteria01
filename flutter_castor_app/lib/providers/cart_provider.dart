import 'package:flutter/foundation.dart';
import '../models/product.dart';
import '../models/cart_item.dart';

class CartProvider extends ChangeNotifier {
  final Map<String, CartItem> _items = {};
  String _selectedSucursal = 'Centro';
  String _customerPhone = '';
  String _customerName = '';

  Map<String, CartItem> get items => {..._items};
  String get selectedSucursal => _selectedSucursal;
  String get customerPhone => _customerPhone;
  String get customerName => _customerName;

  int get totalItemCount {
    int count = 0;
    _items.forEach((key, item) {
      count += item.quantity;
    });
    return count;
  }

  double get subtotal {
    double sum = 0.0;
    _items.forEach((key, item) {
      sum += item.subtotal;
    });
    return sum;
  }

  double get tax => subtotal * 0.15; // 15% IVA Ecuador

  double get total => subtotal + tax;

  int getItemQuantity(String productId) {
    if (_items.containsKey(productId)) {
      return _items[productId]!.quantity;
    }
    return 0;
  }

  void setSucursal(String sucursal) {
    _selectedSucursal = sucursal;
    notifyListeners();
  }

  void setCustomerInfo({required String phone, required String name}) {
    _customerPhone = phone;
    _customerName = name;
    notifyListeners();
  }

  void addItem(Product product) {
    if (_items.containsKey(product.id)) {
      _items[product.id]!.quantity += 1;
    } else {
      _items[product.id] = CartItem(product: product, quantity: 1);
    }
    notifyListeners();
  }

  void removeSingleItem(String productId) {
    if (!_items.containsKey(productId)) return;
    if (_items[productId]!.quantity > 1) {
      _items[productId]!.quantity -= 1;
    } else {
      _items.remove(productId);
    }
    notifyListeners();
  }

  void updateQuantity(Product product, int quantity) {
    if (quantity <= 0) {
      _items.remove(product.id);
    } else {
      if (_items.containsKey(product.id)) {
        _items[product.id]!.quantity = quantity;
      } else {
        _items[product.id] = CartItem(product: product, quantity: quantity);
      }
    }
    notifyListeners();
  }

  void clearCart() {
    _items.clear();
    notifyListeners();
  }
}
