from bson import ObjectId
from flask import jsonify, session
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app import mongo

def cart_count_exc():
    try:
        user_id = None
        # Kiểm tra xem token có tồn tại và hợp lệ không
        try:
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
        except Exception as e:
            pass

        # Fallback về session nếu không có token
        if not user_id:
            user_id = session.get("user_id")

        # Nếu không có user_id, trả về count 0
        if not user_id:
            return jsonify({"count": 0})

        # Tìm giỏ hàng của user
        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})
        if not cart or 'products' not in cart:
            return jsonify({"count": 0})

        # Đếm số lượng sản phẩm riêng lẻ (số phần tử trong mảng products)
        total_items = len(cart['products'])
        return jsonify({"count": total_items})

    except Exception as e:
        return jsonify({"count": 0, "error": str(e)}), 500