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

        # Truy vấn sản phẩm liên quan (cùng gender hoặc brand, không bao gồm sản phẩm hiện tại)
        related_products = list(mongo.db.products.find({
            "$or": [
                {"gender": product['gender']},
                {"brand": product.get('brand', '')}
            ],
            "_id": {"$ne": ObjectId(product_id)}  # Không lấy sản phẩm hiện tại
        }).limit(4))

        # Chuyển ObjectId thành chuỗi cho các sản phẩm liên quan
        for related_product in related_products:
            related_product['_id'] = str(related_product['_id'])

        return render_template("product/product_detail.html", product=product, related_products=related_products)

    except InvalidId as e:
        return f"Lỗi: ID sản phẩm không hợp lệ: {str(e)}", 400
    except Exception as e:
        error_message = f"Lỗi truy vấn sản phẩm: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return error_message, 500