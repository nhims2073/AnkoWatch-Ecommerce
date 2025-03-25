from venv import logger
from bson import ObjectId
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mongo

@jwt_required()
def update_cart_exc(product_id, action):
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({"success": False, "message": "Vui lòng đăng nhập để cập nhật giỏ hàng!"}), 401

        cart = mongo.db.carts.find_one({"user_id": ObjectId(user_id)})
        if not cart:
            return jsonify({"success": False, "message": "Giỏ hàng không tồn tại!"}), 404

        products = cart.get("products", [])
        product_found = False

        for item in products:
            if str(item["product_id"]) == product_id:
                product_found = True
                if action == "increase" and item["quantity"] < 99:
                    item["quantity"] += 1
                elif action == "decrease" and item["quantity"] > 1:
                    item["quantity"] -= 1
                break

        if not product_found:
            return jsonify({"success": False, "message": "Sản phẩm không có trong giỏ hàng!"}), 404

        mongo.db.carts.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": {"products": products}}
        )

        logger.info(f"Updated quantity for product {product_id} in cart for user {user_id}")
        return jsonify({"success": True, "message": "Cập nhật số lượng thành công!"})

    except Exception as e:
        logger.error(f"Error updating cart: {str(e)}")
        return jsonify({"success": False, "message": f"Có lỗi xảy ra: {str(e)}"}), 500