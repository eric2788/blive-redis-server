import redis
import json
import asyncio
from redis.client import Redis

async def initRedis(data: any = None) -> Redis:
    if not data:
        f = open('./settings/config.json')
        data = json.load(f)['redis']
    try:
        global redis_client
        password = data['password'] if 'password' in data and data['password'] else None
        redis_client = redis.Redis(host=data['host'], port=data['port'], db=data['database'], password=password)
        redis_client.info() # ensure connection
        await send_live_room_status(-1, "server-started")
        return redis_client
    except redis.exceptions.RedisError as e:
        print(f'連接到 Redis 時出現錯誤: {e}')
        print(f'等待五秒後重連...')
        await asyncio.sleep(5)
        return await initRedis(data)


async def send_live_room_status(room, status: str):
    info = {
        'platform': 'blibili',
        'id': room, 
        'status': status
    }
    data = json.dumps(info)
    redis_client.publish("live-room-status", data)