import redis
import os
from dotenv import load_dotenv

load_dotenv()

def check_redis():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"Connecting to Redis at: {redis_url}")
    try:
        r = redis.from_url(redis_url)
        if r.ping():
            print("INFO: Redis connection: OK")
        else:
            print("ERROR: Redis connection: Failed (ping returned False)")
    except Exception as e:
        print(f"ERROR: Redis connection error: {e}")

if __name__ == "__main__":
    check_redis()
