from pymongo import MongoClient
from bson import ObjectId

# Thông tin kết nối MongoDB
uri = "mongodb+srv://test:12341234@cluster0.i3vkq.mongodb.net/e-commerce?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)

# Truy cập database và collection
db = client['e-commerce']
collection = db['carts']

# ID của người dùng Đức Hiếu
user_id = ObjectId("67daaa59139a00ddacd6929d")

# ID sản phẩm cần cập nhật
product_id = ObjectId("67e27e44e099ab7b7d4ec8f6")

# Số lượng mới cho sản phẩm trong giỏ hàng
new_quantity = 2

# Cập nhật số lượng sản phẩm trong giỏ hàng
result = collection.update_one(
    {
        "user_id": user_id,  # Tìm giỏ hàng theo user_id
        "products.product_id": product_id  # Tìm sản phẩm cụ thể trong mảng products
    },
    {
        "$set": {"products.$.quantity": new_quantity}  # Cập nhật chỉ số lượng của sản phẩm
    }
)

# Kiểm tra kết quả cập nhật
if result.matched_count > 0:
    print("Số lượng sản phẩm trong giỏ hàng đã được cập nhật thành công.")
else:
    # Nếu sản phẩm chưa có trong giỏ hàng, thêm sản phẩm mới
    new_product = {
        "product_id": product_id,
        "name": "Model 8096",  # Chỉ thêm các trường thông tin cơ bản nếu cần
        "price": 47833633,
        "quantity": new_quantity,
        "gender": "Unisex",
        "size": "49mm",
        "image": "https://example.com/image70.jpg",
        "brand": "Tsar Bomba",
        "material": "Da",
        "origin": "Nhật Bản",
        "technology": "Chống nước 100m",
        "year": 2009
    }
    collection.update_one(
        {"user_id": user_id},  # Đảm bảo giỏ hàng tồn tại
        {"$push": {"products": new_product}},  # Thêm sản phẩm mới vào giỏ hàng
        upsert=True  # Tạo giỏ hàng nếu chưa tồn tại
    )
    print("Sản phẩm mới đã được thêm vào giỏ hàng.")

# Đóng kết nối
client.close()