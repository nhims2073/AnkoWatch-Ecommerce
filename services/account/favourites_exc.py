from flask_jwt_extended import get_jwt_identity
from app import mongo
from bson import ObjectId

def add_to_favourites_exc(product_id):
    user_id = ObjectId(get_jwt_identity())
    
    favourites = mongo.db.favourites.find_one({"user_id": user_id})
    if favourites:
        if ObjectId(product_id) not in favourites['product_ids']:
            mongo.db.favourites.update_one(
                {"user_id": user_id},
                {"$push": {"product_ids": ObjectId(product_id)}}
            )
    else:
        mongo.db.favourites.insert_one({
            "user_id": user_id,
            "product_ids": [ObjectId(product_id)]
        })

    return {"success": "Sản phẩm đã được thêm vào danh sách yêu thích!"}

def get_favorite_products_exc():
    user_id = ObjectId(get_jwt_identity())
    
    favourites = mongo.db.favourites.find_one({"user_id": user_id})
    
    if not favourites or not favourites.get('product_ids'):
        return []

    # Lưu ý quan trọng: Ép kiểu ObjectId trước khi truy vấn
    products = list(mongo.db.products.find(
        {"_id": {"$in": [ObjectId(pid) for pid in favourites['product_ids']]}},
        {"name":1, "image":1, "price":1, "brand_id":1}
    ))
    
    for product in products:
        brand = mongo.db.brands.find_one({"_id": ObjectId(product['brand_id'])}, {"name":1})
        product['brand'] = brand['name'] if brand else "Không xác định"
        product['_id'] = str(product['_id'])

    return products
    
def remove_from_favorites_exc(product_id):
    user_id = ObjectId(get_jwt_identity())
        
    favourites = mongo.db.favourites.find_one({"user_id": user_id})
    if favourites and ObjectId(product_id) in favourites['product_ids']:
        mongo.db.favourites.update_one(
            {"user_id": user_id},
            {"$pull": {"product_ids": ObjectId(product_id)}}
        )
        return {"success": "Sản phẩm đã được xoá khỏi danh sách yêu thích!"}
        
    return {"error": "Sản phẩm không tồn tại trong danh sách yêu thích!"}
