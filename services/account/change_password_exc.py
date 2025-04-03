from flask import session, request
from app import mongo
from bson import ObjectId
import bcrypt

def change_password_exc():
    """
    Xử lý logic đổi mật khẩu.
    Trả về thông báo thành công hoặc lỗi.
    """
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Bạn cần đăng nhập để thực hiện thao tác này."}

    # Lấy dữ liệu từ form
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    # Kiểm tra dữ liệu đầu vào
    if not current_password or not new_password or not confirm_password:
        return {"error": "Vui lòng điền đầy đủ các trường."}

    if new_password != confirm_password:
        return {"error": "Mật khẩu mới và xác nhận mật khẩu không khớp."}

    if len(new_password) < 6:
        return {"error": "Mật khẩu mới phải có ít nhất 6 ký tự."}

    # Lấy thông tin người dùng
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return {"error": "Người dùng không tồn tại."}

    # Kiểm tra mật khẩu hiện tại
    if not bcrypt.checkpw(current_password.encode('utf-8'), user['password']):
        return {"error": "Mật khẩu hiện tại không đúng."}

    # Mã hóa mật khẩu mới
    hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    try:
        # Cập nhật mật khẩu mới
        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": hashed_new_password}}
        )
        if result.modified_count > 0:
            return {"success": "Đổi mật khẩu thành công!"}
        else:
            return {"error": "Không có thay đổi nào được thực hiện."}
    except Exception as e:
        return {"error": f"Lỗi khi đổi mật khẩu: {str(e)}"}