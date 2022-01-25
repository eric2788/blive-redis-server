**已棄用，詳見 [PlatformsCrawler](https://github.com/eric2788/platformscrawler)**


本 python 程序 為一個 按需打開WS的監控伺服器，透過監聽 pubsub channels 中含 blive:<房間號> 格式的 channel 來打開所需的B站直播間WS監控。
當監測到目前正在監控的 直播間號 不在 pubsub channels 內的列表時，它將自動關閉該房間號的WS監控。

## 使用方式
1. 在 settings/config.json 中輸入正確的 redis server 資料和需要監控的指令
2. 打開 redis server 後 運行此 python 程序
3. 在其他連入該 redis sever 的程序中 / 使用 redis-client 訂閱格式為 blive:<房間號> 的 channel
4. 開始接收 直播間 websocket 資料
5. 如要停止監控，則取消訂閱，如程序發現該頻道沒有任何訂閱，將會自動關閉WS監控

## 其他
- redis 內有 live_room_listening 的 set，含目前正在監控的直播房間號
- 可以透過訂閱 live-room-status 來監控 每個房間號的狀態更改
    - 格式為 ``{ "id": <房間號>, "status": <狀態> }``
    - 狀態: stopped 關閉, started 開啟, 有 server 前綴則為本 python 程序
    - 房間號: -1 則為本 python 程序

## 鳴謝

blivedm 作者 (詳見 forked from)
