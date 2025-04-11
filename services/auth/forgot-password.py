from flask import request, jsonify
from services.models import User
from werkzeug.security import generate_password_hash

def forgot_password():
    username = request.json.get("username", None)
    new_password = request.json.get("new_password", None)

    # Kiểm tra nếu người dùng có tồn tại
    user = User.get_user_by_username(username)
    if user:
        # Cập nhật mật khẩu mới
        hashed_password = generate_password_hash(new_password)
        User.update_password(username, hashed_password)
        return jsonify({"msg": "Password updated successfully"}), 200

    return jsonify({"msg": "User not found"}), 404
