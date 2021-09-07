from asyncio.events import AbstractEventLoop, get_event_loop
from asyncio.tasks import Task
from os import close, error
import threading
from spider import Spider;
import asyncio;
import json;
import redis;
from typing import Any, Dict;
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
        

def on_receive_command(message):
    print(f'收到指令 {message}')
    if message['type'] != 'message':
        return
    data = json.loads(message['data'].decode('utf-8'))
    room_id = data['id']
    cmd = data['cmd']
    if cmd == 'listen':
        t = threading.Thread(target=runRoom, args=(room_id, ))
        t.start()
    elif cmd == 'terminate':
        stopListen(room=room_id)

def runRoom(room: int):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(startListen(room))
    loop.close()
    #asyncio.run(startListen(room=room_id))

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
        p.close()
        r.close()
    except redis.exceptions.ConnectionError as e:
        print(f'關閉 Redis 時出現錯誤: {e}')
    except RuntimeError as e:
        print(f'關閉程序時出現錯誤: {e}')
    finally:
        exit

def initRedis(data: Any) -> bool:
    global r, p
    try:
        r = redis.Redis(host= data['host'], port= int(data['port']), db=0)
        p = r.pubsub()
        p.subscribe("command")
        print(f'bili-redis-server 成功啟動，正在監聽指令...')
        send_live_room_status(-1, "server-started")
        atexit.register(on_program_terminate)
        while True:
            time.sleep(0.1)
            msg = p.get_message()
            if msg:
                try:
                    on_receive_command(msg)
                except Exception as e:
                    print(f'處理指令時出現錯誤 {msg}: {e}')
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
        
    

if __name__ == '__main__':
    f = open('./settings/config.json')
    data = json.load(f)
    initRedis(data)

    
    