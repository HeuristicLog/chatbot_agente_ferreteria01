import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/product.dart';
import '../models/order_request.dart';

class ApiService {
  // Base URL: En web utiliza la misma ruta relativa o localhost en desarrollo móvil
  static String baseUrl = 'http://localhost:8085';

  static Future<List<String>> getCategories() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/catalog/categories'));
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (data['success'] == true) {
          final List categoriesData = data['data'];
          return ['Todos', ...categoriesData.map((c) => c['name'].toString())];
        }
      }
      return ['Todos', 'Herramientas Eléctricas', 'Construcción', 'Pinturas', 'Plomería', 'Electricidad'];
    } catch (e) {
      return ['Todos', 'Herramientas Eléctricas', 'Construcción', 'Pinturas', 'Plomería', 'Electricidad'];
    }
  }

  static Future<List<Product>> getProducts({String? category, String? query, String? sucursal}) async {
    try {
      final queryParams = <String, String>{};
      if (category != null && category != 'Todos') queryParams['category'] = category;
      if (query != null && query.isNotEmpty) queryParams['q'] = query;
      if (sucursal != null) queryParams['sucursal'] = sucursal;

      final uri = Uri.parse('$baseUrl/api/catalog/products').replace(queryParameters: queryParams);
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        if (data['success'] == true) {
          final List productsList = data['data'];
          return productsList.map((p) => Product.fromJson(p)).toList();
        }
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  static Future<Map<String, dynamic>> submitOrder(OrderRequest order) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/catalog/orders'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(order.toJson()),
      );

      final data = json.decode(utf8.decode(response.bodyBytes));
      if (response.statusCode == 200 && data['success'] == true) {
        return {
          'success': true,
          'order_number': data['data']['order_number'],
          'total': data['data']['total'],
        };
      } else {
        return {
          'success': false,
          'message': data['message'] ?? 'Error al procesar el pedido.',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'Error de conexión con el servidor de Ferretería Castor.',
      };
    }
  }
}
