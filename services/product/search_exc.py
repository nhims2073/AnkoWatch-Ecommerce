from flask import request
from app import mongo
from bson import ObjectId
import re

def search_exc():
    """
    Hàm xử lý logic tìm kiếm sản phẩm dựa trên từ khóa người dùng nhập.
    Trả về danh sách sản phẩm phù hợp để hiển thị trên search.html.
    """
    # Lấy từ khóa tìm kiếm từ query parameter 'q'
    query = request.args.get('q', '').strip()

    # Lấy các bộ lọc khác (nếu có): category, sort, brand, price_range
    category = request.args.get('category', '')
    sort = request.args.get('sort', 'relevance')
    brands = request.args.getlist('brand')  # Danh sách thương hiệu được chọn
    price_ranges = request.args.getlist('price_range')  # Danh sách khoảng giá được chọn

    # Nếu không có từ khóa, trả về danh sách rỗng
    if not query:
        return []

    # Tạo điều kiện tìm kiếm
    search_conditions = []

    # Tách từ khóa thành các từ riêng lẻ để tìm kiếm
    keywords = query.split()
    for keyword in keywords:
        # Tạo regex để tìm kiếm không phân biệt hoa thường
        regex = re.compile(f'.*{re.escape(keyword)}.*', re.IGNORECASE)
        # Tìm kiếm trên các trường: name, brand, material, origin
        search_conditions.append({
            '$or': [
                {'name': regex},
                {'brand': regex},
                {'material': regex},
                {'origin': regex},
                {'technology': regex}
            ]
        })

    # Kết hợp các điều kiện tìm kiếm (tìm sản phẩm khớp với bất kỳ từ khóa nào)
    final_condition = {'$and': search_conditions} if search_conditions else {}

    # Thêm bộ lọc category (nếu có)
    if category:
        final_condition['gender'] = category.upper()  # Ví dụ: "NAM" hoặc "NỮ"

    # Thêm bộ lọc thương hiệu (nếu có)
    if brands:
        final_condition['brand'] = {'$in': [brand.capitalize() for brand in brands]}

    # Thêm bộ lọc khoảng giá (nếu có)
    if price_ranges:
        price_conditions = []
        for price_range in price_ranges:
            try:
                min_price, max_price = map(int, price_range.split('-'))
                price_conditions.append({
                    'price': {'$gte': min_price, '$lte': max_price}
                })
            except:
                continue
        if price_conditions:
            final_condition['$or'] = price_conditions

    # Truy vấn MongoDB
    products = mongo.db.products.find(final_condition)

    # Sắp xếp kết quả
    if sort == 'price_asc':
        products = products.sort('price', 1)  # Sắp xếp giá tăng dần
    elif sort == 'price_desc':
        products = products.sort('price', -1)  # Sắp xếp giá giảm dần
    else:
        # Mặc định: sắp xếp theo độ phù hợp (_id giảm dần)
        products = products.sort('_id', -1)

    # Chuyển đổi dữ liệu để render template
    product_list = []
    for product in products:
        product['_id'] = str(product['_id'])  # Chuyển ObjectId thành string
        product_list.append(product)

    return product_list