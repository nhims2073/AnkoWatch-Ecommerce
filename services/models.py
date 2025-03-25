from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import mongo

class BaseModel:
    def __init__(self, collection):
        self.collection = mongo.db[collection]
    
    def save(self, data):
        return self.collection.insert_one(data)

    def find_one(self, query):
        return self.collection.find_one(query)

class UserModel(UserMixin):
    collection = mongo.db.users

    def __init__(self, username, password, fullname, email, role="member"):
        if not all([username, password, fullname, email]):
            raise ValueError("All fields are required")
        self.username = username.strip()
        self.password = generate_password_hash(password)  # Hash mật khẩu ngay khi khởi tạo
        self.fullname = fullname.strip()
        self.email = email.strip()
        self.role = role

    def save(self):
        self.collection.insert_one({
            "username": self.username,
            "password": self.password,  # Đã được hash
            "fullname": self.fullname,
            "email": self.email,
            "role": self.role
        })

    @classmethod
    def find_by_username(cls, username):
        return cls.collection.find_one({"username": username})

    @staticmethod
    def validate_password(stored_hashed_password, provided_password):
        return check_password_hash(stored_hashed_password, provided_password)
    
class Product:
    def __init__(self, name, price, quantity, description, image_url):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.description = description
        self.image_url = image_url

    def save(self):
        mongo.db.products.insert_one({
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "description": self.description,
            "image": self.image_url
        })

    @classmethod
    def find_by_name(cls, name):
        return mongo.db.products.find_one({"name": name})

    @classmethod
    def find_by_id(cls, product_id):
        return mongo.db.products.find_one({"_id": product_id})

    @classmethod
    def update(cls, product_id, updates):
        mongo.db.products.update_one({"_id": product_id}, {"$set": updates})

    @classmethod
    def delete(cls, product_id):
        mongo.db.products.delete_one({"_id": product_id})