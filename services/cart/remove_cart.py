from venv import logger
from bson import ObjectId
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mongo

@jwt_required()
def remove_cart_exc(product_id):
    try:
        # Lấy user_id từ token JWT (là một chuỗi)
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"success": False, "message": "Vui lòng đăng nhập để xóa sản phẩm khỏi giỏ hàng!"}), 401

        # Tìm giỏ hàng của user
        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})
        if not cart or 'products' not in cart or not cart['products']:
            return jsonify({"success": False, "message": "Giỏ hàng trống!"}), 400

        # Xóa sản phẩm khỏi giỏ hàng
        # So sánh product_id dưới dạng chuỗi
        cart['products'] = [item for item in cart['products'] if str(item['product_id']) != product_id]

        # Cập nhật giỏ hàng trong MongoDB
        mongo.db.carts.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": {"products": cart['products']}}
        )

        # Tính tổng số lượng sản phẩm trong giỏ hàng
        cart_count = sum(item["quantity"] for item in cart['products']) if cart['products'] else 0
        logger.info(f"Removed product {product_id} from cart for user {user_id}. New cart count: {cart_count}")

        # Trả về phản hồi thành công
        response = jsonify({
            "success": True,
            "message": "Sản phẩm đã được xóa khỏi giỏ hàng!",
            "cart_count": cart_count
        })
        response.headers['HX-Trigger'] = 'updateCartBadge'  # Kích hoạt cập nhật badge giỏ hàng
        return response, 200

    except Exception as e:
        logger.error(f"Error removing from cart: {str(e)}")
        return jsonify({"success": False, "message": f"Có lỗi xảy ra: {str(e)}"}), 500