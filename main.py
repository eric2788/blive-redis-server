from asyncio.events import AbstractEventLoop
import threading
from spider import Spider;
import asyncio;
import json;
import redis;
from typing import Dict, List;
import time;
import signal;
import sys;



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
    r.lpush("live_room_listening", room)
    send_live_room_status(room, "started")
    while listenMap[room] == True:
        await asyncio.sleep(1)
    await task.close()
    print(f'已停止監聽直播間 {room}')
    r.lrem("live_room_listening", 0, room)
    send_live_room_status(room, "stopped")

def stopListen(room: int):
    listenMap[room] = False
        

def on_receive_command(message):
    print(f'收到指令 {message}')
    if message['type'] != 'message':
        return
    data = json.loads(message['data'].decode('utf-8'))
    cmd = data['cmd']
    if cmd == 'listen':
        room_id = data['id']
        t = threading.Thread(target=runRoom, args=(room_id, ))
        t.start()
    elif cmd == 'terminate':
        room_id = data['id']
        stopListen(room=room_id)
    elif cmd == 'list':
        print(f'現在運行的直播間列表:')
        arr = r.lrange("live_room_listening", 0, -1)
        print("[", end="")
        for listening in arr:
            print(listening.decode('utf-8'), end=", ")
        print("]", end="\n")

        
loops = []
    
def runRoom(room: int):
    loop = asyncio.new_event_loop()
    loop.run_until_complete(startListen(room))
    loops.append(loop)
    #asyncio.run(startListen(room=room_id))

def send_live_room_status(room: int, status: str):
    info = {
        'id': room, 
        'status': status
    }
    data = json.dumps(info)
    r.publish("live-room-status", data)

def on_program_terminate(signalnum, frame):
    print(f'程序正在關閉...')
    for loop in loops:
        if loop.is_running():
            loop.close()

    r.delete("live_room_listening")
    p.close()
    r.close()
    sys.exit()

if __name__ == '__main__':
    f = open('./settings/config.json')
    data = json.load(f)
    global r, p
    r = redis.Redis(host= data['host'], port= int(data['port']), db=0)
    p = r.pubsub()
    """
    p.subscribe(**{"command": on_receive_command})
    thread = p.run_in_thread(sleep_time=0.1)
    """
    p.subscribe("command")
    print(f'bili-redis-server 成功啟動，正在監聽指令...')
    signal.signal(signal.SIGBREAK, on_program_terminate)
    signal.signal(signal.SIGINT, on_program_terminate)
    while True:
        time.sleep(0.1)
        msg = p.get_message()
        if msg:
            try:
                on_receive_command(msg)
            except Exception as e:
                print(f'Error while handling command {msg}: {e}')
    
    