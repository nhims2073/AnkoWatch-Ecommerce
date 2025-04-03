from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app import mongo
from bson import ObjectId
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_exc():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')

        # Kiểm tra các trường bắt buộc
        if not all([email, username, fullname, password, confirm_password]):
            flash('Vui lòng điền đầy đủ thông tin!', 'error')
            return redirect(url_for('register'))

        # Kiểm tra mật khẩu xác nhận
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return redirect(url_for('register'))

        # Kiểm tra email và username trùng lặp
        if mongo.db.users.find_one({'email': email}):
            flash('Email đã được sử dụng!', 'error')
            return redirect(url_for('register'))

        if mongo.db.users.find_one({'username': username}):
            flash('Tên đăng nhập đã được sử dụng!', 'error')
            return redirect(url_for('register'))

        # Truy vấn role "Member" từ collection roles
        member_role = mongo.db.roles.find_one({"name": "Member"})
        if not member_role:
            logger.error("Role 'Member' not found in the system!")
            flash('Không tìm thấy vai trò "Member" trong hệ thống! Vui lòng liên hệ quản trị viên.', 'error')
            return redirect(url_for('register'))

        # Sử dụng werkzeug.security để hash mật khẩu
        hashed_password = generate_password_hash(password)

        # Tạo user mới
        new_user = {
            'email': email,
            'username': username,
            'fullname': fullname,
            'password': hashed_password,
            'role_id': member_role['_id'],  # Gán role_id
            'image': 'https://res.cloudinary.com/dsbfsc7ii/image/upload/v1743159055/avatar_default_user_mxakar.webp',
            'discount_amount': 0  # Thêm trường mặc định
        }

        try:
            mongo.db.users.insert_one(new_user)
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Error inserting new user {username}: {str(e)}")
            flash('Đã xảy ra lỗi khi đăng ký! Vui lòng thử lại sau.', 'error')
            return redirect(url_for('register'))

    return render_template('auth/register.html')