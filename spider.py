from redis import Redis
import requests
from blivedm import BLiveClient
import json

class Spider(BLiveClient):

    def __init__(self, room_id: int, redis: Redis, name: str = None): # name can make custom
        super().__init__(room_id)
        self.nick_id = room_id
        self.title = None
        self.bilibili_uid = 0
        self.user_cover = None
        self.name = name
        self.redis = redis

    def to_redis_message(self, command, data):
        info = {
            'command': command,
            'data': {
                'uid': self.bilibili_uid,
                'title': self.title,
                'name': self.name,
                'room': self.nick_id,
                'real_room': self.room_id,
                'content': data
            }
        }
        return json.dumps(info)

    def get_live_info(self):
        r = requests.get('https://api.live.bilibili.com/room/v1/Room/get_info?room_id=%s' % self.room_id,
                         headers={
                             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'})

        if r.status_code == 200:
            data = r.json()['data']
            self.title = data['title']
            self.bilibili_uid = data['uid']
            self.user_cover = data['user_cover']
            return data

    def get_user_info(self):
        r = requests.get('https://api.bilibili.com/x/space/acc/info?mid=%s&jsonp=jsonp' % self.bilibili_uid,
                           headers={
                             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'})
        if r.status_code == 200:
            data = r.json()['data']
            self.name = data['name']


    _COMMAND_HANDLERS = BLiveClient._COMMAND_HANDLERS.copy()

    async def on_recevie_command(self, t, command):
         print(f'received command {t} from {self.nick_id} ({self.room_id})')
         data = self.to_redis_message(t, command)
         self.redis.publish(str(self.nick_id), data)

    async def _on_live(self, command):
        if self.live_status:
            return
        self.get_live_info()
        if not self.name:
            self.get_user_info()
        self.live_status = True
        data = self.to_redis_message('LIVE', command)
        self.redis.publish(str(self.nick_id), data)
        

    async def _on_prepare(self, command):
        _ = command
        self.live_status = False
        print(f'{self.nick_id} ({self.room_id}) 准备中')

    _COMMAND_HANDLERS['LIVE'] = _on_live

    _COMMAND_HANDLERS['PREPARING'] = _on_prepare

    for cmd in ('DANMU_MSG', 'SEND_GIFT', 'GUARD_BUY', 'SUPER_CHAT_MESSAGE'):
        _COMMAND_HANDLERS[cmd] = lambda client, command, t=cmd: client.on_recevie_command(t, command)


