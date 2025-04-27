import logging
from flask import redirect, request, url_for, flash
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from functools import wraps
from app import mongo
from bson import ObjectId

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if request.path in ('/payments_return', 'order_complete', 'invoice_detail', '/login'):
                return fn(*args, **kwargs)
            
            try:
                # Xác minh JWT token từ cookies
                verify_jwt_in_request(locations=["cookies"])
                
                # Lấy toàn bộ claims từ token JWT
                jwt_data = get_jwt()
                
                # Lấy role từ claims
                user_role = jwt_data.get("role")
                if not user_role:
                    flash("Không tìm thấy vai trò của người dùng!", "danger")
                    return redirect(url_for("login"))

                # Kiểm tra role
                if user_role.lower() != role.lower():
                    flash("Không được phép truy cập! Vai trò không phù hợp.", "danger")
                    return redirect(url_for("login"))

            except Exception as e:
                flash("Phiên đăng nhập đã hết hạn hoặc không được phép truy cập!", "danger")
                return redirect(url_for("login"))

            return fn(*args, **kwargs)
        return decorator
    return wrapper

def permission_required(permission):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            if request.path in ('/payments_return', 'order_complete', 'invoice_detail', '/login'):
                return fn(*args, **kwargs)
            
            try:
                # Xác minh JWT token từ cookies
                verify_jwt_in_request(locations=["cookies"])
                
                # Lấy toàn bộ claims từ token JWT
                jwt_data = get_jwt()
                
                # Lấy user_id từ claims
                user_id = jwt_data.get("sub")
                if not user_id:
                    flash("Không tìm thấy thông tin người dùng!", "danger")
                    return redirect(url_for("login"))

                # Truy vấn dữ liệu người dùng để lấy role_id
                user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
                if not user_data or "role_id" not in user_data:
                    flash("Không tìm thấy vai trò của người dùng!", "danger")
                    return redirect(url_for("login"))

                # Truy vấn dữ liệu vai trò để lấy permission_ids
                role = mongo.db.roles.find_one({"_id": ObjectId(user_data["role_id"])})
                if not role or "permission_ids" not in role:  # Sửa từ "permissions" thành "permission_ids"
                    flash("Không tìm thấy quyền của vai trò!", "danger")
                    return redirect(url_for("login"))

                # Lấy danh sách permission_ids từ vai trò
                permission_ids = role.get("permission_ids", [])  # Sửa từ "permissions" thành "permission_ids"
                if not permission_ids:
                    flash("Vai trò không có quyền nào được gán!", "danger")
                    return redirect(url_for("login"))

                # Lọc các permission_ids hợp lệ và chuyển đổi thành ObjectId
                valid_permission_ids = []
                for pid in permission_ids:
                    try:
                        valid_permission_ids.append(ObjectId(pid))
                    except Exception as e:
                        continue

                if not valid_permission_ids:
                    flash("Không tìm thấy quyền hợp lệ nào trong vai trò!", "danger")
                    return redirect(url_for("login"))

                # Truy vấn mã quyền (code) từ collection permissions
                permissions = mongo.db.permissions.find({"_id": {"$in": valid_permission_ids}})
                permission_codes = [perm["code"] for perm in permissions]

                # Kiểm tra xem người dùng có quyền cần thiết không
                if permission not in permission_codes:
                    flash(f"Không được phép truy cập! Bạn không có quyền {permission}.", "danger")
                    return redirect(url_for("login"))

            except Exception as e:
                flash("Phiên đăng nhập đã hết hạn hoặc không được phép truy cập!", "danger")
                return redirect(url_for("login"))

            return fn(*args, **kwargs)
        return decorator
    return wrapper

def log_request():
    from flask import request
    print(f"Yêu cầu: {request.method} {request.path}")