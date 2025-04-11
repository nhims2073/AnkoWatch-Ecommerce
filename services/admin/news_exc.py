from app import mongo
from bson import ObjectId
from datetime import datetime
import pytz

def create_news(user_id, content, card_image, content_image):
    created_time = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

    result = mongo.db.news.insert_one({
        "user_id": ObjectId(user_id),
        "created_time": created_time,
        "content": content,
        "card_image": card_image,
        "content_image": content_image
    })
    return result

def update_news(news_id, content, card_image, content_image):
    updated_time = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))

    result = mongo.db.news.update_one(
        {"_id": ObjectId(news_id)},
        {"$set": {"content": content, "card_image": card_image, "content_image": content_image, "updated_time": updated_time}}
    )
    return result

def delete_news(news_id):
    result = mongo.db.news.delete_one({"_id": ObjectId(news_id)})
    return result
