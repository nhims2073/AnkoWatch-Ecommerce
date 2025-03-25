import json
from flask import jsonify, request, redirect, url_for, flash, render_template, session, make_response
from werkzeug.security import check_password_hash
from app import mongo, login_manager, User
from flask_login import login_user
from flask_jwt_extended import create_access_token, set_access_cookies
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": user_id})
    if user_data:
        return User(user_data)
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

from flask import session, jsonify, request, make_response, redirect, url_for
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash
from app import mongo

def login_exc():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = mongo.db.users.find_one({"username": username})
        if not user:
            return jsonify({"success": False, "message": "User not found!"}), 404

        if not check_password_hash(user["password"], password):
            return jsonify({"success": False, "message": "Invalid password!"}), 401

        # Lưu user_id vào session
        session["user_id"] = str(user["_id"])
        session["fullname"] = user.get("fullname", "")
        session["role"] = user.get("role", "user")

        # Tạo token với sub là user_id (chuỗi)
        user_id = str(user["_id"])
        additional_claims = {
            "fullname": user.get("fullname", ""),
            "role": user.get("role", "user"),
            "discount_amount": user.get("discount_amount", 0)
        }
        access_token = create_access_token(identity=user_id, additional_claims=additional_claims)

        # Tạo response và đặt cookie
        response = make_response(redirect(url_for('home')))
        response.set_cookie("access_token_cookie", access_token, httponly=True, secure=False)
        response.headers['HX-Trigger'] = 'updateCartBadge'
        return response

    return render_template("auth/login.html")