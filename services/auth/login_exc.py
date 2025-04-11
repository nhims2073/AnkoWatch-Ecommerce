from flask import jsonify, request, make_response, redirect, url_for, session, render_template
from werkzeug.security import check_password_hash
from app import mongo, login_manager, User
from flask_login import login_user
from flask_jwt_extended import create_access_token, set_access_cookies
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data)
        return None
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        return None

def verify_user(username, password):
    """Xác thực thông tin người dùng"""
    if not username or not password:
        return None
    user_data = mongo.db.users.find_one({'username': username})
    if not user_data:
        return None
    try:
        if check_password_hash(user_data["password"], password):
            return User(user_data)
    except ValueError as e:
        logger.error(f"Error verifying password for user {username}: {str(e)}")
    return None

def login_exc():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Truy vấn user từ collection users
        user_data = mongo.db.users.find_one({"username": username})
        if not user_data:
            return jsonify({"success": False, "message": "User not found!"}), 404

        # Kiểm tra mật khẩu
        if not check_password_hash(user_data["password"], password):
            return jsonify({"success": False, "message": "Invalid password!"}), 401

        # Truy vấn thông tin vai trò từ role_id
        role_name = "Member"  # Giá trị mặc định nếu không tìm thấy role
        if 'role_id' in user_data and user_data['role_id']:
            try:
                role = mongo.db.roles.find_one({"_id": ObjectId(user_data['role_id'])})
                if role:
                    role_name = role['name']
                else:
                    logger.warning(f"Role not found for role_id {user_data['role_id']} for user {username}")
            except Exception as e:
                logger.error(f"Error querying role for user {username}: {str(e)}")

        # Tạo đối tượng User để sử dụng với flask_login
        user = User(user_data)

        # Đăng nhập người dùng với flask_login
        login_user(user)

        # Lưu user_id và các thông tin khác vào session
        session["user_id"] = str(user_data["_id"])
        session["fullname"] = user_data.get("fullname", "")
        session["role"] = role_name  # Lưu role_name vào session

        # Tạo token với sub là user_id (chuỗi)
        user_id = str(user_data["_id"])
        additional_claims = {
            "fullname": user_data.get("fullname", ""),
            "role": role_name,  # Sử dụng role_name trong claims
            "discount_amount": user_data.get("discount_amount", 0)
        }
        access_token = create_access_token(identity=user_id, additional_claims=additional_claims)

        # Tạo response và đặt cookie
        response = make_response(
            redirect(url_for('dashboard') if role_name.lower() == "admin" else url_for('home'))
        )
        response.set_cookie(
            "access_token_cookie",
            access_token,
            httponly=True,
            secure=True if request.is_secure else False,  # Đặt secure=True nếu dùng HTTPS
            samesite="Strict"
        )
        response.headers['HX-Trigger'] = 'updateCartBadge'
        return response

    return render_template("auth/login.html")