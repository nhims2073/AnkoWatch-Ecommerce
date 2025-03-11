import os
from pymongo import MongoClient
import redis
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_HOST = os.getenv("CACHE_REDIS_HOST")
    CACHE_REDIS_PORT = int(os.getenv("CACHE_REDIS_PORT"))
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    JWT_SESSION_COOKIE = True
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)

    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Kết nối đến MongoDB Atlas
client = MongoClient(Config.MONGO_URI)
db = client.get_database()

# Cấu hình kết nối Redis
redis_client = redis.StrictRedis(host=Config.CACHE_REDIS_HOST, port=Config.CACHE_REDIS_PORT, db=0)
