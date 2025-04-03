from flask import jsonify, request, render_template, redirect, url_for
from app import mongo
from bson import ObjectId
from datetime import datetime
from services.middleware import role_required
import random
import string

def generate_voucher_code(prefix="VOUCHER"):
    """Tạo mã voucher ngẫu nhiên với tiền tố và 8 ký tự ngẫu nhiên."""
    random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{random_chars}"

def get_all_vouchers(search_query=None):
    """Lấy tất cả voucher, có thể lọc theo từ khóa tìm kiếm."""
    try:
        query = {}
        if search_query:
            query["code"] = {"$regex": search_query, "$options": "i"}  # Tìm kiếm không phân biệt hoa thường
        vouchers = mongo.db.vouchers.find(query)
        return [{
            "_id": str(voucher["_id"]),
            "code": voucher["code"],
            "discount": voucher["discount"],
            "quantity": voucher["quantity"],
            "created_at": voucher["created_at"],
            "expiry_date": voucher["expiry_date"]
        } for voucher in vouchers]
    except Exception as e:
        print(f"Error in get_all_vouchers: {str(e)}")
        return []

def get_voucher_details(voucher_id):
    """Lấy chi tiết một voucher theo ID."""
    try:
        voucher = mongo.db.vouchers.find_one({"_id": ObjectId(voucher_id)})
        if voucher:
            voucher["_id"] = str(voucher["_id"])
            return voucher
        return None
    except Exception as e:
        print(f"Error in get_voucher_details: {str(e)}")
        return None

def add_voucher_exc():
    """Thêm mới voucher."""
    try:
        data = request.form
        code = data.get("code")
        discount = float(data.get("discount"))
        quantity = int(data.get("quantity"))
        expiry_date = data.get("expiry_date")

        if mongo.db.vouchers.find_one({"code": code}):
            return jsonify({"error": "Mã voucher đã tồn tại!"})

        voucher = {
            "code": code,
            "discount": discount,
            "quantity": quantity,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "expiry_date": expiry_date
        }
        mongo.db.vouchers.insert_one(voucher)
        return jsonify({"success": "Thêm voucher thành công!"})
    except Exception as e:
        return jsonify({"error": str(e)})

def update_voucher_exc():
    """Cập nhật voucher."""
    try:
        data = request.form
        voucher_id = data.get("voucher_id")
        code = data.get("code")
        discount = float(data.get("discount"))
        quantity = int(data.get("quantity"))
        expiry_date = data.get("expiry_date")

        existing_voucher = mongo.db.vouchers.find_one({"code": code, "_id": {"$ne": ObjectId(voucher_id)}})
        if existing_voucher:
            return jsonify({"error": "Mã voucher đã tồn tại!"})

        mongo.db.vouchers.update_one(
            {"_id": ObjectId(voucher_id)},
            {"$set": {
                "code": code,
                "discount": discount,
                "quantity": quantity,
                "expiry_date": expiry_date
            }}
        )
        return jsonify({"success": "Cập nhật voucher thành công!"})
    except Exception as e:
        return jsonify({"error": str(e)})

def delete_voucher_exc(voucher_id):
    """Xóa voucher."""
    try:
        result = mongo.db.vouchers.delete_one({"_id": ObjectId(voucher_id)})
        if result.deleted_count > 0:
            return jsonify({"success": "Xóa voucher thành công!"})
        return jsonify({"error": "Không tìm thấy voucher!"})
    except Exception as e:
        return jsonify({"error": str(e)})