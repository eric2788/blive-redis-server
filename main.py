import threading
from spider import Spider;
import asyncio;
import json;
import redis;
from typing import Any, Dict, List;
import time;
import atexit;

listenMap: Dict[int, bool] = dict()

async def startListen(room: int, name: str = None):
    if (room in listenMap and listenMap[room] == True):
        print(f'直播間 {room} 已經被初始化了')
        send_live_room_status(room, "existed")
        return
    print(f'正在初始化直播間 {room}')
    task = Spider(room, r, name)
    await task.init_room()
    task.start()
    listenMap[room] = True
    print(f'{room} 直播間初始化完成。')
    r.sadd("live_room_listening", room)
    send_live_room_status(room, "started")
    while listenMap[room] == True:
        await asyncio.sleep(1)
    await task.close()
    print(f'已停止監聽直播間 {room}')
    del listenMap[room]
    r.srem("live_room_listening", room)
    send_live_room_status(room, "stopped")

def stopListen(room: int):
    listenMap[room] = False

def runRoom(room: int):
    #loop = asyncio.new_event_loop()
    #loop.run_until_complete(startListen(room))
    asyncio.run(startListen(room))

def send_live_room_status(room: int, status: str):
    info = {
        'id': room, 
        'status': status
    }
    data = json.dumps(info)
    r.publish("live-room-status", data)

def on_program_terminate():
    print(f'程序正在關閉...')
    try:
        send_live_room_status(-1, "server-closed")
        r.delete("live_room_listening")
        r.close()
    except redis.exceptions.ConnectionError as e:
        print(f'關閉 Redis 時出現錯誤: {e}')
    except RuntimeError as e:
        print(f'關閉程序時出現錯誤: {e}')

def initRedis(host: str = "127.0.0.1", port: int = 6379, db: int = 0) -> bool:
    global r
    try:
        r = redis.Redis(host, port, db)
        send_live_room_status(-1, "server-started")
        atexit.register(on_program_terminate)
        print(f'bili-redis-server 成功啟動，正在監聽指令...')
        while True:
            time.sleep(1)
            channels = r.pubsub_channels("blive:*")
            subscibing = set({})
            for room in channels:
                try:
                    room_id = int(str.replace(room.decode('utf-8'), "blive:", ""))
                    subscibing.add(room_id)
                except ValueError:
                    print(f'位置房間號: {room}')
            listening = set(listenMap.keys())
            for to_listen in subscibing - listening:
                t = threading.Thread(target=runRoom, args=(to_listen, ))
                t.start()
            for to_stop in listening - subscibing:
                stopListen(to_stop)
    except redis.exceptions.ConnectionError as e:
        print(f'連接到 Redis 時出現錯誤: {e}')
        print(f'等待五秒後重連...')
        try:
            time.sleep(5)
            return initRedis(data)
        except KeyboardInterrupt:
            print(f'程序在等待重啟時被中止')
            exit()
    except KeyboardInterrupt:
        print(f'程序被手動中止')
        if len(listenMap) > 0:
            for room in listenMap.keys():
                listenMap[room] = False
            print(f'正在等待所有WebSocket關閉...')
            while len(listenMap) > 0:
                time.sleep(1)
        print(f'所有 Websocket 程序已經關閉。')
        exit()

def hookSpider(listen: List[str]):
    Spider.TO_LISTEN = listen
    for cmd in Spider.TO_LISTEN:
        Spider._COMMAND_HANDLERS[cmd] = lambda client, command, t=cmd: client.on_recevie_command(t, command) 

def showSubscribers():
    # show subscribers
    subscribers = r.pubsub_numsub("blive:*")
    for sub in subscribers:
        (channel, num) = sub
        room = channel.decode('utf-8')
        print(f'目前有 {num} 位訂閱者正在監控 {room}')
    

if __name__ == '__main__':
    f = open('./settings/config.json')
    data = json.load(f)
    listen = data['listens']
    hookSpider(listen)
    print(f'將會監控的指令: {Spider.TO_LISTEN}')
    initRedis(data['host'], data['port'], data['database'])

    
    