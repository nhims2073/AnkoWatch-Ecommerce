from flask import session, request, redirect, url_for
from app import mongo
from bson import ObjectId

def get_addresses_exc():
    """
    Lấy danh sách địa chỉ của người dùng từ collection list_address.
    """
    user_id = session.get("user_id")
    if not user_id:
        return []

    addresses = list(mongo.db.list_address.find({"user_id": ObjectId(user_id)}))
    for address in addresses:
        address['_id'] = str(address['_id'])
        address['user_id'] = str(address['user_id'])
    return addresses

def add_address_exc():
    """
    Thêm địa chỉ mới vào collection list_address.
    """
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Bạn cần đăng nhập để thực hiện thao tác này."}

    # Lấy dữ liệu từ form
    name = request.form.get("name", "").strip()
    street = request.form.get("street", "").strip()
    phone = request.form.get("phone", "").strip()

    # Kiểm tra dữ liệu đầu vào
    if not name or not street or not phone:
        return {"error": "Vui lòng điền đầy đủ thông tin địa chỉ."}

    # Kiểm tra giá trị của name
    if name not in ["Nhà riêng", "Văn phòng"]:
        return {"error": "Loại địa chỉ không hợp lệ."}

    new_address = {
        "user_id": ObjectId(user_id),
        "name": name,
        "street": street,
        "phone": phone
    }

    try:
        result = mongo.db.list_address.insert_one(new_address)
        if result.inserted_id:
            return {"success": "Thêm địa chỉ thành công!", "redirect": url_for('address')}
        else:
            return {"error": "Không thể thêm địa chỉ."}
    except Exception as e:
        return {"error": f"Lỗi khi thêm địa chỉ: {str(e)}"}

def update_address_exc(address_id):
    """
    Cập nhật thông tin địa chỉ trong collection list_address.
    """
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Bạn cần đăng nhập để thực hiện thao tác này."}

    # Lấy dữ liệu từ form
    name = request.form.get("name", "").strip()
    street = request.form.get("street", "").strip()
    phone = request.form.get("phone", "").strip()

    # Kiểm tra dữ liệu đầu vào
    if not name or not street or not phone:
        return {"error": "Vui lòng điền đầy đủ thông tin địa chỉ."}

    # Kiểm tra giá trị của name
    if name not in ["Nhà riêng", "Văn phòng"]:
        return {"error": "Loại địa chỉ không hợp lệ."}

    try:
        result = mongo.db.list_address.update_one(
            {"_id": ObjectId(address_id), "user_id": ObjectId(user_id)},
            {"$set": {"name": name, "street": street, "phone": phone}}
        )
        if result.modified_count > 0:
            return {"success": "Cập nhật địa chỉ thành công!", "redirect": url_for('address')}
        else:
            return {"error": "Không thể cập nhật địa chỉ.", "redirect": url_for('address')}
    except Exception as e:
        return {"error": f"Lỗi khi cập nhật địa chỉ: {str(e)}", "redirect": url_for('address')}

def delete_address_exc(address_id):
    """
    Xóa địa chỉ khỏi collection list_address.
    """
    user_id = session.get("user_id")
    if not user_id:
        return {"error": "Bạn cần đăng nhập để thực hiện thao tác này."}

    try:
        result = mongo.db.list_address.delete_one(
            {"_id": ObjectId(address_id), "user_id": ObjectId(user_id)}
        )
        if result.deleted_count > 0:
            return {"success": "Xóa địa chỉ thành công!", "redirect": url_for('address')}
        else:
            return {"error": "Không thể xóa địa chỉ.", "redirect": url_for('address')}
    except Exception as e:
        return {"error": f"Lỗi khi xóa địa chỉ: {str(e)}", "redirect": url_for('address')}