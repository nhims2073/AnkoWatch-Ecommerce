# File: customer_exc.py
from app import mongo
from bson import ObjectId
from datetime import datetime

# Các hàm hiện có (giữ nguyên phần liên quan đến customers)
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

# Hàm lấy tất cả quyền (đã thêm ở bước 1)
def get_all_permissions_exc():
    """
    Lấy tất cả quyền từ collection permissions.
    """
    permissions = mongo.db.permissions.find()
    return [{"_id": str(permission['_id']), "name": permission['name'], "description": permission.get('description', '')} for permission in permissions]

# Cập nhật và thêm các hàm liên quan đến roles
def get_all_roles_exc():
    """
    Lấy tất cả vai trò và thông tin quyền của chúng.
    """
    roles = mongo.db.roles.find()
    role_list = []
    
    for role in roles:
        role_data = {
            "_id": str(role['_id']),
            "name": role['name']
        }
        
        # Lấy thông tin quyền từ permission_ids
        permission_ids = role.get('permission_ids', [])
        if permission_ids:
            try:
                permissions = mongo.db.permissions.find({
                    "_id": {"$in": [ObjectId(pid) for pid in permission_ids]}
                })
                role_data['permissions'] = [
                    {"_id": str(perm['_id']), "name": perm['name'], "description": perm.get('description', '')}
                    for perm in permissions
                ]
            except (ValueError, TypeError):
                role_data['permissions'] = []
        else:
            role_data['permissions'] = []
            
        role_list.append(role_data)
    return role_list

def add_role_exc(data):
    """
    Thêm vai trò mới, bao gồm danh sách quyền.
    """
    role_name = data.get('name')
    permission_ids = data.get('permission_ids', [])  # Danh sách permission_ids từ form (checkbox)
    
    if not role_name:
        return {"error": "Tên vai trò là bắt buộc!"}
    
    # Kiểm tra xem vai trò đã tồn tại chưa
    existing_role = mongo.db.roles.find_one({"name": role_name})
    if existing_role:
        return {"error": "Vai trò đã tồn tại!"}

    # Chuyển permission_ids thành ObjectId
    try:
        permission_ids = [ObjectId(pid) for pid in permission_ids if pid]
    except (ValueError, TypeError):
        return {"error": "Danh sách quyền không hợp lệ!"}

    # Kiểm tra xem các permission_ids có tồn tại không
    if permission_ids:
        existing_permissions = mongo.db.permissions.count_documents({"_id": {"$in": permission_ids}})
        if existing_permissions != len(permission_ids):
            return {"error": "Một hoặc nhiều quyền không tồn tại!"}

    role = {
        "name": role_name,
        "permission_ids": permission_ids,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = mongo.db.roles.insert_one(role)
    return {"success": "Thêm vai trò thành công!", "role_id": str(result.inserted_id)}

def update_role_exc(role_id, data):
    """
    Cập nhật thông tin vai trò, bao gồm tên và danh sách quyền.
    """
    try:
        role_id = ObjectId(role_id)
    except (ValueError, TypeError):
        return {"error": "ID vai trò không hợp lệ!"}

    role_name = data.get('name')
    permission_ids = data.get('permission_ids', [])

    if not role_name:
        return {"error": "Tên vai trò là bắt buộc!"}

    # Kiểm tra xem vai trò có tồn tại không
    existing_role = mongo.db.roles.find_one({"_id": role_id})
    if not existing_role:
        return {"error": "Vai trò không tồn tại!"}

    # Kiểm tra xem tên vai trò mới có trùng với vai trò khác không
    if role_name != existing_role['name']:
        if mongo.db.roles.find_one({"name": role_name}):
            return {"error": "Tên vai trò đã tồn tại!"}

    # Chuyển permission_ids thành ObjectId
    try:
        permission_ids = [ObjectId(pid) for pid in permission_ids if pid]
    except (ValueError, TypeError):
        return {"error": "Danh sách quyền không hợp lệ!"}

    # Kiểm tra xem các permission_ids có tồn tại không
    if permission_ids:
        existing_permissions = mongo.db.permissions.count_documents({"_id": {"$in": permission_ids}})
        if existing_permissions != len(permission_ids):
            return {"error": "Một hoặc nhiều quyền không tồn tại!"}

    result = mongo.db.roles.update_one(
        {"_id": role_id},
        {"$set": {
            "name": role_name,
            "permission_ids": permission_ids,
            "updated_at": datetime.utcnow()
        }}
    )
    if result.modified_count > 0:
        return {"success": "Cập nhật vai trò thành công!"}
    return {"error": "Không có thay đổi!"}

def delete_role_exc(role_id):
    """
    Xóa vai trò, với kiểm tra ràng buộc (không xóa nếu vai trò đang được gán cho user).
    """
    try:
        role_id = ObjectId(role_id)
    except (ValueError, TypeError):
        return {"error": "ID vai trò không hợp lệ!"}

    # Kiểm tra xem vai trò có tồn tại không
    role = mongo.db.roles.find_one({"_id": role_id})
    if not role:
        return {"error": "Vai trò không tồn tại!"}

    # Kiểm tra xem vai trò có đang được gán cho user nào không
    user_with_role = mongo.db.users.find_one({"role_id": role_id})
    if user_with_role:
        return {"error": "Vai trò đang được gán cho ít nhất một khách hàng. Vui lòng gỡ vai trò trước khi xóa!"}

    result = mongo.db.roles.delete_one({"_id": role_id})
    if result.deleted_count > 0:
        return {"success": "Xóa vai trò thành công!"}
    return {"error": "Không thể xóa vai trò!"}

def delete_customer_exc(user_id):
    """
    Xóa người dùng khỏi hệ thống.
    """
    try:
        user_id = ObjectId(user_id)
    except (ValueError, TypeError):
        return {"error": "ID người dùng không hợp lệ!"}

    # Kiểm tra xem người dùng có tồn tại không
    user = mongo.db.users.find_one({"_id": user_id})
    if not user:
        return {"error": "Không tìm thấy người dùng!"}

    # Kiểm tra xem người dùng có đơn hàng không
    orders = mongo.db.orders.find_one({"user_id": user_id})
    if orders:
        return {"error": "Không thể xóa người dùng này vì họ đã có đơn hàng trong hệ thống!"}

    # Xóa các địa chỉ của người dùng
    mongo.db.list_address.delete_many({"user_id": user_id})

    # Xóa người dùng
    result = mongo.db.users.delete_one({"_id": user_id})
    if result.deleted_count > 0:
        return {"success": "Xóa người dùng thành công!"}
    return {"error": "Không thể xóa người dùng!"}
