import cloudinary
from flask import session, request
from app import mongo
from bson import ObjectId
from datetime import datetime
import pytz

def get_user_info():
    """
    Lấy thông tin người dùng từ collection users dựa trên user_id trong session.
    Trả về thông tin người dùng hoặc None nếu không tìm thấy.
    """
    user_id = session.get("user_id")
    if not user_id:
        return None

    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        user['_id'] = str(user['_id'])
        # Chuyển đổi ngày sinh sang định dạng dd/MM/yyyy nếu có
        if user.get('birthday'):
            try:
                # Chỉ lấy ngày từ chuỗi ISO, không cần chuyển đổi múi giờ
                birthday = datetime.fromisoformat(user['birthday'].replace("Z", "+00:00"))
                user['birthday'] = birthday.strftime('%d/%m/%Y')
            except:
                user['birthday'] = ''
    return user

def update_user_info():
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Bạn cần đăng nhập để thực hiện thao tác này."}

    fullname = request.form.get("fullname", "").strip()
    phone = request.form.get("phone", "").strip()
    birthday = request.form.get("birthday", "").strip()

    if not fullname:
        return {"error": "Họ và tên không được để trống."}

    update_data = {
        "fullname": fullname,
        "phone": phone,
    }

    if birthday:
        try:
            birthday_dt = datetime.strptime(birthday, '%d/%m/%Y')
            birthday_dt = birthday_dt.replace(tzinfo=pytz.timezone('Asia/Ho_Chi_Minh'))
            update_data["birthday"] = birthday_dt.isoformat()
        except ValueError:
            return {"error": "Ngày sinh không hợp lệ. Vui lòng nhập theo định dạng dd/MM/yyyy."}

    # Xử lý upload avatar lên Cloudinary
    avatar_file = request.files.get('avatar')
    if avatar_file:
        upload_result = cloudinary.uploader.upload(avatar_file)
        update_data["image"] = upload_result.get("secure_url")

    try:
        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        if result.modified_count > 0:
            session["fullname"] = fullname
            return {"success": "Cập nhật thông tin thành công!"}
        else:
            return {"success": "Không có thay đổi nào được thực hiện."}
    except Exception as e:
        return {"error": f"Lỗi khi cập nhật thông tin: {str(e)}"}
    