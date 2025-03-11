from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from flask_caching import Cache
import cloudinary
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

from routes import *

if __name__ == '__main__':
    app.run(debug=True)

jwt = JWTManager(app)
cache = Cache(app)
mongo = PyMongo(app)