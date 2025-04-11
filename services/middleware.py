import logging
from flask import redirect, url_for, flash
from flask_jwt_extended import get_jwt, verify_jwt_in_request
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def role_required(role):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
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
                logger.error(f"Error in role_required: {str(e)}")
                flash("Phiên đăng nhập đã hết hạn hoặc không được phép truy cập!", "danger")
                return redirect(url_for("login"))

            return fn(*args, **kwargs)
        return decorator
    return wrapper

def log_request():
    from flask import request
    print(f"Request: {request.method} {request.path}")