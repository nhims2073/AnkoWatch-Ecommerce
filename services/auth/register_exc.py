from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app import mongo

def register_exc():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        fullname = request.form.get('fullname')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm-password')

        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp!', 'error')
            return redirect(url_for('register'))

        if mongo.db.users.find_one({'email': email}):
            flash('Email đã được sử dụng!', 'error')
            return redirect(url_for('register'))

        if mongo.db.users.find_one({'username': username}):
            flash('Tên đăng nhập đã được sử dụng!', 'error')
            return redirect(url_for('register'))

        # Sử dụng werkzeug.security để hash mật khẩu (đồng bộ với login_exc.py)
        hashed_password = generate_password_hash(password)

        new_user = {
            'email': email,
            'username': username,
            'fullname': fullname,
            'password': hashed_password,
            'role': 'member'
        }

        mongo.db.users.insert_one(new_user)

        flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')