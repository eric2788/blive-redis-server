from spider import BLiveSpiderError, Spider;
from concurrent.futures import ThreadPoolExecutor
from redis import RedisError
from typing import Dict, List;
from redis_utils import initRedis, send_live_room_status
import time, logging, json, asyncio;


VERSION = 'v1.1'

listenMap: Dict[int, bool] = dict()

async def start_listen(room: int, name: str = None):
    if (room in listenMap and listenMap[room] == True):
        logging.info(f'直播間 {room} 已經被初始化了')
        await send_live_room_status(room, "existed")
        return

    print(f'正在初始化直播間 {room}')

    try:

        task = Spider(room, redis, name)
        await task.init_room()
        task.start()
        listenMap[room] = True

    except BLiveSpiderError as e:
        logging.warning(f'初始化直播間 {room} 時出現錯誤: {e}')
        await send_live_room_status(room, f"error:{e}")
        logging.warning(f'已停止監聽此直播間。')
        started.remove(room)
        excepted.add(str(room))
        return

    except Exception as e:
        logging.warning(f'初始化直播間 {room} 時出現錯誤: {e}')
        await send_live_room_status(room, f"error:{e}")
        logging.warning(f'五秒後重試...')
        await asyncio.sleep(5)
        return await start_listen(room, name)
    
    logging.info(f'{room} 直播間初始化完成。')

    await send_live_room_status(room, "started")

    while room in listenMap and listenMap[room] == True:
        await asyncio.sleep(1)

    await task.close()

    logging.info(f'已停止監聽直播間 {room}')

    del listenMap[room]

    await send_live_room_status(room, "stopped")
    

def stopListen(room: int):
    listenMap[room] = False

async def launch_server(max_channels: int = 500):

    global redis, started, excepted

    redis = await initRedis()
    started = set() #防止重複
    excepted = set()

    logging.info(f'bili-redis-server {VERSION} 成功啟動，正在監聽指令...')

    try:
        # Using thread pool
        with ThreadPoolExecutor(max_workers=max_channels, thread_name_prefix="blibili-live") as pool:

            while True:

                time.sleep(1)

                channels = redis.pubsub_channels("blive:*")
                subscibing = set({})

                for room in channels:
                    room_str = room.decode('utf-8').replace("blive:", "")
                    if room_str in excepted:
                        continue
                    try:
                        room_id = int(room_str)
                        subscibing.add(room_id)
                    except ValueError:
                        logging.warning(f'房間號格式錯誤: {room_str}')
                        excepted.add(room_str) # 過濾掉
                    
                listening = set(listenMap.keys())

                for to_listen in subscibing - listening:

                    if to_listen in started:
                        continue

                    pool.submit(asyncio.run, start_listen(to_listen))

                    started.add(to_listen)

                for to_stop in listening - subscibing:
                    stopListen(to_stop)
                    started.discard(to_stop)

    except RedisError as e:
        logging.warning(f'連接到 Redis 時出現錯誤: {e}')
        logging.warning(f'等待五秒後重連...')
        asyncio.sleep(5)
        await launch_server()


def hookSpider(listen: List[str]):
    Spider.TO_LISTEN = listen
    for cmd in Spider.TO_LISTEN:
        Spider._COMMAND_HANDLERS[cmd] = lambda client, command, t=cmd: client.on_recevie_command(t, command) 
    

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info(f'正在啟動 blive-redis-server 版本 {VERSION}')
    f = open('./settings/config.json')
    data = json.load(f)
    listen = data['listens']
    max_channels = data['max_channels']
    hookSpider(listen)
    logging.info(f'將會監控的指令: {Spider.TO_LISTEN}')
    asyncio.run(launch_server(max_channels))

    
    