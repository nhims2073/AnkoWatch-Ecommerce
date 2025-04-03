from app import mongo
from bson import ObjectId
from datetime import datetime

def get_all_customers_exc():
    """
    Lấy tất cả khách hàng (users) và thông tin vai trò của họ.
    """
    users = mongo.db.users.find()
    user_list = []
    for user in users:
        user['_id'] = str(user['_id'])
        
        # Lấy thông tin vai trò
        role_name = "Không xác định"
        if 'role_id' in user and user['role_id']:
            try:
                role = mongo.db.roles.find_one({"_id": ObjectId(user['role_id'])})
                role_name = role['name'] if role else "Không xác định"
            except (ValueError, TypeError):
                role_name = "Không xác định"
        user['role_name'] = role_name

        # Đảm bảo trường image tồn tại
        user['image'] = user.get('image', 'https://via.placeholder.com/150')
        
        user_list.append(user)
    return user_list

def get_customer_details_exc(user_id):
    """
    Lấy chi tiết thông tin của một khách hàng.
    """
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return {"error": "Không tìm thấy khách hàng!"}
        
        user['_id'] = str(user['_id'])
        
        # Lấy thông tin vai trò
        role_name = "Không xác định"
        if 'role_id' in user and user['role_id']:
            try:
                role = mongo.db.roles.find_one({"_id": ObjectId(user['role_id'])})
                role_name = role['name'] if role else "Không xác định"
            except (ValueError, TypeError):
                role_name = "Không xác định"
        user['role_name'] = role_name

        # Đảm bảo trường image tồn tại
        user['image'] = user.get('image', 'https://via.placeholder.com/150')
        
        return user
    except (ValueError, TypeError):
        return {"error": "ID khách hàng không hợp lệ!"}

def update_customer_role_exc(user_id, data):
    """
    Cập nhật vai trò của khách hàng.
    """
    role_id = data.get('role_id')
    if not role_id:
        return {"error": "Vai trò là bắt buộc!"}
    
    try:
        role_id = ObjectId(role_id)
    except (ValueError, TypeError):
        return {"error": "Vai trò không hợp lệ!"}

    # Kiểm tra xem role_id có tồn tại không
    role = mongo.db.roles.find_one({"_id": role_id})
    if not role:
        return {"error": "Vai trò không tồn tại!"}

    result = mongo.db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "role_id": role_id,
            "updated_at": datetime.utcnow()
        }}
    )
    if result.modified_count > 0:
        return {"success": "Cập nhật vai trò thành công!"}
    return {"error": "Không tìm thấy khách hàng hoặc không có thay đổi!"}

def get_all_roles_exc():
    """
    Lấy tất cả vai trò.
    """
    roles = mongo.db.roles.find()
    return [{"_id": str(role['_id']), "name": role['name']} for role in roles]

def add_role_exc(data):
    """
    Thêm vai trò mới.
    """
    role_name = data.get('name')
    if not role_name:
        return {"error": "Tên vai trò là bắt buộc!"}
    
    # Kiểm tra xem vai trò đã tồn tại chưa
    existing_role = mongo.db.roles.find_one({"name": role_name})
    if existing_role:
        return {"error": "Vai trò đã tồn tại!"}

    role = {
        "name": role_name,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = mongo.db.roles.insert_one(role)
    return {"success": "Thêm vai trò thành công!", "role_id": str(result.inserted_id)}