from app import mongo
from bson import ObjectId
from datetime import datetime

def get_all_news():
    # Truy vấn tất cả bài viết tin tức, sắp xếp theo thời gian đăng bài
    news = list(mongo.db.news.find().sort("created_time", -1))
    
    # Convert ObjectId thành string để sử dụng trong frontend
    for article in news:
        article['_id'] = str(article['_id'])
        article['user_id'] = str(article['user_id'])
        article['created_time'] = article['created_time'].strftime('%d/%m/%Y %H:%M:%S')
    
    return news

def get_news_detail(news_id):
    # Truy vấn bài viết tin tức theo ID
    article = mongo.db.news.find_one({"_id": ObjectId(news_id)})
    
    if article:
        article['_id'] = str(article['_id'])
        article['user_id'] = str(article['user_id'])
        article['created_time'] = article['created_time'].strftime('%d/%m/%Y %H:%M:%S')
    
    return article
