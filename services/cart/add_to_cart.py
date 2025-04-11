from bson import ObjectId
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mongo
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@jwt_required()
def add_to_cart_exc(product_id):
    try:
        # Lấy user_id từ token JWT
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"success": False, "message": "Vui lòng đăng nhập để thêm sản phẩm vào giỏ hàng!"}), 401

        # Kiểm tra sản phẩm có tồn tại trong collection products không
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            return jsonify({"success": False, "message": "Sản phẩm không tồn tại!"}), 404

        # Tìm giỏ hàng của user trong collection carts
        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})
        
        if cart:
            # Nếu giỏ hàng đã tồn tại, kiểm tra sản phẩm trong giỏ
            products = cart.get("products", [])
            product_exists = False
            
            # Cập nhật số lượng nếu sản phẩm đã có trong giỏ
            for item in products:
                if str(item["product_id"]) == product_id:
                    item["quantity"] += 1
                    product_exists = True
                    break
            
            # Nếu sản phẩm chưa có, thêm mới vào danh sách sản phẩm
            if not product_exists:
                products.append({"product_id": ObjectId(product_id), "quantity": 1})
            
            # Cập nhật giỏ hàng trong collection carts
            mongo.db.carts.update_one(
                {"user_id": ObjectId(user_id)},
                {"$set": {"products": products}}
            )
        else:
            # Nếu chưa có giỏ hàng, tạo mới trong collection carts
            mongo.db.carts.insert_one({
                "user_id": ObjectId(user_id),
                "products": [{"product_id": ObjectId(product_id), "quantity": 1}]
            })

        logger.info(f"Added product {product_id} to cart for user {user_id}")
        response = jsonify({"success": True, "message": "Đã thêm sản phẩm vào giỏ hàng!"})
        response.headers['HX-Trigger'] = 'updateCartBadge'  # Kích hoạt cập nhật badge giỏ hàng
        return response

    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return jsonify({"success": False, "message": f"Có lỗi xảy ra: {str(e)}"}), 500