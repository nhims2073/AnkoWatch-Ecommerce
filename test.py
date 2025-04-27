from flask import Flask
from redis import Redis

app = Flask(__name__)
redis = Redis(host='localhost', port=6379, db=0)

@app.route('/')
def hello():
    redis.incr('hits')
    return f'Hello! This page has been viewed {redis.get("hits").decode("utf-8")} time(s).'

if __name__ == '__main__':
    try:
        redis.ping()
        print("Successfully connected to Redis!")
        app.run(debug=True)
    except redis.ConnectionError:
        print("Failed to connect to Redis. Make sure Redis is running.")
    except Exception as e:
        print(f"Error while interacting with Redis: {e}")
