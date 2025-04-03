from flask import request
from app import mongo
from bson import ObjectId
import re

def search_exc():
    """
    Hàm xử lý logic tìm kiếm sản phẩm dựa trên các bộ lọc người dùng nhập.
    Trả về danh sách sản phẩm, category_mapping và thông báo nếu không tìm thấy.
    """
    # Lấy các tham số từ query string
    query = request.args.get('q', '').strip()
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'relevance')
    brands = request.args.getlist('brand')
    price_ranges = request.args.getlist('price_range')

    final_condition = {}
    message = None

    # Tìm kiếm theo từ khóa
    if query:
        search_conditions = []
        keywords = query.split()
        for keyword in keywords:
            regex = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)
            search_conditions.append({
                '$or': [
                    {'name': regex},
                    {'material': regex},
                    {'origin': regex},
                    {'technology': regex}
                ]
            })
        if search_conditions:
            final_condition['$and'] = search_conditions

    # Bộ lọc danh mục
    category_mapping = {
        'dong_ho_nam': 'Đồng hồ nam',
        'dong_ho_nu': 'Đồng hồ nữ'
    }
    if category:
        category_name = category_mapping.get(category)
        if category_name:
            category_doc = mongo.db.categories.find_one({'name': category_name}, {'_id': 1})
            if category_doc:
                final_condition['category_ids'] = {'$in': [category_doc['_id']]}
            else:
                message = f"Không tìm thấy danh mục: {category_name}"
                return [], category_mapping, message

    # Bộ lọc thương hiệu
    if brands:
        brand_mapping = {
            'audemars_piguet': 'Audemars Piguet',  # Sửa lỗi chính tả 'audemas_piguet'
            'jacques_lemans': 'Jacques Lemans',
            'epos_swiss': 'Epos Swiss',
            'philippe_auguste': 'Philippe Auguste'
        }
        brand_ids = []
        for brand_name in brands:
            corrected_brand_name = brand_mapping.get(brand_name, brand_name.replace('_', ' ').title())
            brand = mongo.db.brands.find_one(
                {'name': {'$regex': f'^{re.escape(corrected_brand_name)}$', '$options': 'i'}},
                {'_id': 1}
            )
            if brand:
                brand_ids.append(brand['_id'])
        if brand_ids:
            final_condition['brand_id'] = {'$in': brand_ids}
        else:
            message = f"Không tìm thấy thương hiệu: {', '.join(brands)}"
            return [], category_mapping, message

    # Bộ lọc giá
    if price_ranges:
        price_conditions = []
        for price_range in price_ranges:
            try:
                min_price, max_price = map(int, price_range.split('-'))
                price_conditions.append({
                    'price': {'$gte': min_price, '$lte': max_price}
                })
            except ValueError:
                continue
        if price_conditions:
            final_condition['$or'] = price_conditions

    # Truy vấn sản phẩm từ collection products
    products = mongo.db.products.find(final_condition)

    # Sắp xếp kết quả
    if sort == 'price_asc':
        products = products.sort('price', 1)
    elif sort == 'price_desc':
        products = products.sort('price', -1)
    else:
        products = products.sort('_id', -1)

    # Chuẩn hóa dữ liệu sản phẩm
    product_list = []
    for product in products:
        product['_id'] = str(product['_id'])  # Chuyển ObjectId thành string
        product['name'] = product.get('name', 'Không xác định')
        product['image'] = product.get('image', '/static/images/default-product.jpg')
        if 'brand_id' in product and product['brand_id']:
            brand = mongo.db.brands.find_one({'_id': ObjectId(product['brand_id'])}, {'name': 1})
            product['brand'] = brand['name'] if brand else 'Không xác định'
        else:
            product['brand'] = 'Không xác định'
        product['price'] = float(product.get('price', 0))
        product_list.append(product)

    # Thông báo nếu không tìm thấy sản phẩm
    if not product_list and not message:
        if brands:
            message = f"Không tìm thấy sản phẩm nào thuộc thương hiệu: {', '.join(brands)}"
        elif category:
            message = f"Không tìm thấy sản phẩm nào thuộc danh mục: {category_name}"
        else:
            message = "Không tìm thấy sản phẩm nào."

    return product_list, category_mapping, message