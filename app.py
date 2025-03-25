from bson import ObjectId
from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from config import Config
from flask_login import LoginManager, UserMixin, current_user

app = Flask(__name__)
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)

jwt = JWTManager(app)
cache = Cache(app)
mongo = PyMongo(app)  # PyMongo sẽ sử dụng kết nối từ Config

@app.context_processor
def inject_user():
    return dict(current_user=current_user)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data["_id"])
        self.username = user_data["username"]
        self.fullname = user_data.get("fullname", "")
        self.role = user_data["role"]

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

    @login_manager.user_loader
    def load_user(user_id):
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            user_data = mongo.db.users.find_one({"_id": user_id})
            if user_data:
                return User(user_data)
        except Exception as e:
            print(f"Error loading user: {e}")
        return None

from routes import *

if __name__ == "__main__":
    app.run(debug=True)