class Product {
  final String id;
  final String sku;
  final String name;
  final String category;
  final String description;
  final double price;
  final int stock;
  final Map<String, dynamic> sucursalStocks;
  final String imageUrl;
  final bool inStock;

  Product({
    required this.id,
    required this.sku,
    required this.name,
    required this.category,
    required this.description,
    required this.price,
    required this.stock,
    required this.sucursalStocks,
    required this.imageUrl,
    required this.inStock,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id']?.toString() ?? '',
      sku: json['sku'] ?? '',
      name: json['name'] ?? '',
      category: json['category'] ?? '',
      description: json['description'] ?? '',
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      stock: (json['stock'] as num?)?.toInt() ?? 0,
      sucursalStocks: json['sucursal_stocks'] != null
          ? Map<String, dynamic>.from(json['sucursal_stocks'])
          : {},
      imageUrl: json['image_url'] ??
          'https://images.unsplash.com/photo-1581147036324-c17ac41dfa6c?w=600&auto=format&fit=crop&q=80',
      inStock: json['in_stock'] ?? true,
    );
  }

  int getStockForSucursal(String sucursal) {
    if (sucursalStocks.containsKey(sucursal)) {
      return (sucursalStocks[sucursal] as num?)?.toInt() ?? 0;
    }
    return stock;
  }
}
