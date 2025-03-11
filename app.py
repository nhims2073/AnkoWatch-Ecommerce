from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_caching import Cache
import cloudinary
from config import Config

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.config.from_object(Config)

# Khởi tạo các extension
jwt = JWTManager(app)
cache = Cache(app)
mongo = PyMongo(app)

# Import routes sau khi khởi tạo app (để tránh circular import)
from routes import *

