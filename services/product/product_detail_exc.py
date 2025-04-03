from bson import ObjectId
from flask import render_template
import traceback
from app import mongo
from bson.errors import InvalidId

def product_detail_exc(product_id):
    try:
        # Kiểm tra xem product_id có phải là ObjectId hợp lệ không
        if not ObjectId.is_valid(product_id):
            return f"ID sản phẩm không hợp lệ: {product_id}", 400

        # Truy vấn sản phẩm chính
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            return "Sản phẩm không tồn tại", 404

        # Chuyển ObjectId thành chuỗi
        product['_id'] = str(product['_id'])
        print(f"Product ID: {product['_id']}")  # Debug: Log the product_id

        # Đảm bảo các trường cần thiết có giá trị mặc định
        product['brand'] = product.get('brand', '')  # Đảm bảo brand có giá trị mặc định
        product['category_ids'] = product.get('category_ids', [])  # Đảm bảo category_ids là mảng, mặc định là rỗng
        product['material'] = product.get('material', 'Không xác định')  # Đảm bảo material có giá trị mặc định
        product['origin'] = product.get('origin', 'Không xác định')  # Đảm bảo origin có giá trị mặc định
        product['technology'] = product.get('technology', 'Không xác định')  # Đảm bảo technology có giá trị mặc định
        product['year'] = product.get('year', 'Không xác định')  # Đảm bảo year có giá trị mặc định
        product['price'] = float(product.get('price', 0))  # Đảm bảo price là số
        product['discount'] = float(product.get('discount', 0))  # Đảm bảo discount là số
        product['discounted_price'] = float(product.get('discounted_price', product['price']))  # Đảm bảo discounted_price là số
        product['quantity'] = product.get('quantity', 0)  # Đảm bảo quantity có giá trị mặc định
        product['size'] = product.get('size', [])  # Đảm bảo size là một mảng, mặc định là rỗng nếu không có

        # Lấy tên thương hiệu từ brand_id
        brand_name = "Không xác định"
        if 'brand_id' in product and product['brand_id']:
            brand = mongo.db.brands.find_one({'_id': ObjectId(product['brand_id'])}, {'name': 1})
            brand_name = brand['name'] if brand else "Không xác định"
        product['brand_name'] = brand_name

        # Lấy mô tả từ collection descriptions
        current_product_id = product['_id']
        description_doc = mongo.db.descriptions.find_one({"product_id": current_product_id})
        if description_doc:
            product['description'] = description_doc['description']
            print(f"Description found for product {current_product_id}: {product['description']}")
        else:
            product['description'] = "No description available"
            print(f"No description found for product {current_product_id} in descriptions collection")

        # Truy vấn danh mục dựa trên category_ids
        category_name = "Đồng hồ"  # Giá trị mặc định nếu không tìm thấy danh mục
        if product['category_ids']:
            # Lấy category_id đầu tiên (giả sử mỗi sản phẩm chỉ thuộc một danh mục chính)
            category_id = product['category_ids'][0]
            if ObjectId.is_valid(category_id):
                category = mongo.db.categories.find_one({"_id": ObjectId(category_id)}, {"name": 1})
                if category:
                    category_name = category['name']

        # Truy vấn sản phẩm liên quan (cùng category_ids hoặc brand, không bao gồm sản phẩm hiện tại)
        related_products_query = {
            "_id": {"$ne": ObjectId(product_id)}  # Không lấy sản phẩm hiện tại
        }
        if product['category_ids'] or product['brand']:
            related_products_query["$or"] = []
            if product['category_ids']:
                # Tìm các sản phẩm có ít nhất một category_id trùng với sản phẩm hiện tại
                related_products_query["$or"].append({"category_ids": {"$in": product['category_ids']}})
            if product['brand']:
                related_products_query["$or"].append({"brand": product['brand']})

        related_products = list(mongo.db.products.find(related_products_query).limit(4))

        # Chuyển ObjectId thành chuỗi và lấy mô tả cho các sản phẩm liên quan
        for related_product in related_products:
            related_product['_id'] = str(related_product['_id'])
            # Đảm bảo các trường cần thiết có giá trị mặc định
            related_product['price'] = float(related_product.get('price', 0))  # Đảm bảo price là số
            related_product['discount'] = float(related_product.get('discount', 0))  # Đảm bảo discount là số
            related_product['discounted_price'] = float(related_product.get('discounted_price', related_product['price']))  # Đảm bảo discounted_price là số
            related_product['size'] = related_product.get('size', [])  # Đảm bảo size là một mảng, mặc định là rỗng
            # Lấy mô tả cho sản phẩm liên quan
            description_doc = mongo.db.descriptions.find_one({"product_id": related_product['_id']})
            if description_doc:
                related_product['description'] = description_doc['description']
            else:
                related_product['description'] = "No description available"

        return render_template(
            "product/product_detail.html",
            product=product,
            related_products=related_products,
            category_name=category_name
        )

    except InvalidId as e:
        return f"Lỗi: ID sản phẩm không hợp lệ: {str(e)}", 400
    except Exception as e:
        error_message = f"Lỗi truy vấn sản phẩm: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return error_message, 500