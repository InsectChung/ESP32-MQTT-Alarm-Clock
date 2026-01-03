# ============================================================
# ESP32-S2 mini 旗艦整合版 (按鈕16/21 + 範例顯示風格)
# ============================================================

import uasyncio as asyncio
import ujson as json
import network, time, dht
from machine import I2C, Pin, PWM
from ssd1306 import SSD1306_I2C
from bitmap_font_tool import set_font_path, draw_text
from DebounceButton import DebouncedButton

# 引入自定義模組
from mqtt_client import MqttManager
from wifi import connect_wifi, sync_time

# -------- 設定 --------
set_font_path('./lib/fonts/fusion_bdf.12')
ALARM_FILE = "alarm.txt"

# 時間修正：設為 0
TZ_OFFSET = 0  
SNOOZE_MIN = 5      # 貪睡時間
RING_LIMIT_SEC = 15 # 響鈴限制秒數

# MQTT 設定
MY_ID = "M1424001"  
TOPIC_TEMP = f"{MY_ID}/bedroom/temp"
TOPIC_HUMI = f"{MY_ID}/bedroom/humi"

# -------- 硬體初始化 --------
dht_sensor = dht.DHT11(Pin(18))
i2c = I2C(0, scl=Pin(7), sda=Pin(5))
oled = SSD1306_I2C(128, 64, i2c)
speaker = PWM(Pin(6, Pin.OUT))
speaker.duty(0)

# -------- 全域狀態變數 --------
alarms = []
is_ringing = False
MODE = "CLOCK"  
view_idx = 0    
current_env = {"temp": "--", "humi": "--", "ip": "..."} 
_last_rung_key = None 

# 暫存設定值
temp_setting = {"h":0, "m":0, "repeat":0, "music":0}
cursor_pos = 0 
_preview_task = None 

# ============================================================
# 音樂定義
# ============================================================
NOTE_FREQS = {
    'C3': 131, 'C#3': 139, 'D3': 147, 'Eb3': 156, 'E3': 165, 'F3': 175, 'F#3': 185, 'G3': 196, 'Ab3': 208, 'A3': 220, 'Bb3': 233, 'B3': 247,
    'C4': 262, 'C#4': 277, 'D4': 294, 'Eb4': 311, 'E4': 330, 'F4': 349, 'F#4': 370, 'G4': 392, 'Ab4': 415, 'A4': 440, 'Bb4': 466, 'B4': 494,
    'C5': 523, 'C#5': 554, 'D5': 587, 'Eb5': 622, 'E5': 659, 'F5': 698, 'F#5': 740, 'G5': 784, 'Ab5': 831, 'A5': 880, 'Bb5': 932, 'B5': 988,
    'C6': 1047, 'REST': 0
}

MUSIC_NAME = ["生日快樂", "給愛麗絲", "小蜜蜂", "快樂頌"]

MELODY = {
    0: [('C4', 350), ('C4', 150), ('D4', 500), ('C4', 500), ('F4', 500), ('E4', 900), ('REST', 100),
        ('C4', 350), ('C4', 150), ('D4', 500), ('C4', 500), ('G4', 500), ('F4', 900), ('REST', 100)], 
    1: [('E5', 200), ('D#5', 200), ('E5', 200), ('D#5', 200), ('E5', 200), ('B4', 200), ('D5', 200), ('C5', 200), ('A4', 400)], 
    2: [('G4',300),('E4',300),('E4',300),('F4',300),('D4',300),('D4',300),
        ('C4',300),('D4',300),('E4',300),('F4',300),('G4',300),('G4',300),('G4',450)],
    3: [('E4',200),('E4',200),('F4',200),('G4',200), ('G4',200),('F4',200),('E4',200),('D4',200),
        ('C4',200),('C4',200),('D4',200),('E4',200), ('E4',400),('D4',400),('D4',400)]
}

# ============================================================
# 核心邏輯
# ============================================================
def taiwan_time(): 
    return time.localtime(time.time() + TZ_OFFSET)

def load_alarms():
    global alarms
    try:
        with open(ALARM_FILE,"r") as f: alarms = json.loads(f.read())
        for a in alarms: 
            a.setdefault("enabled", True)
            a.setdefault("music", 0)
            a.setdefault("repeat", 0)
    except: alarms = []

def save_alarms():
    with open(ALARM_FILE,"w") as f: f.write(json.dumps(alarms))

def add_alarm(h, m, repeat, music):
    alarms.append({"h":int(h), "m":int(m), "repeat":int(repeat), "music":int(music), "enabled":True})
    save_alarms()

def get_next_alarm_str():
    if not alarms: return "無"
    now = taiwan_time()
    current_minutes = now[3] * 60 + now[4]
    min_diff = 999999
    next_a = None
    
    for a in alarms:
        if not a.get("enabled"): continue
        alarm_minutes = a["h"] * 60 + a["m"]
        diff = alarm_minutes - current_minutes
        if diff <= 0: diff += 24 * 60
        if diff < min_diff:
            min_diff = diff
            next_a = a
    return f"{next_a['h']:02d}:{next_a['m']:02d}" if next_a else "無"

# ============================================================
# OLED 顯示 (採用範例檔案風格)
# ============================================================
def oled_write(lines):
    oled.fill(0)
    for text, y in lines:
        try:
            # 這裡就是範例檔案的顯示方式
            draw_text(oled, text, 0, y)
        except:
            pass # 防止字串過長當機
    oled.show()

def show_ui():
    if MODE == "CLOCK":
        t = taiwan_time()
        # 仿照範例檔案的佈局：
        # 第一行：標題
        # 第二行：日期
        # 第三行：時間
        # 第四行：狀態
        oled_write([
            ("台灣時間", 0),
            (f"{t[0]}/{t[1]:02d}/{t[2]:02d}", 16),
            (f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}", 32),
            (f"下次: {get_next_alarm_str()}", 48)
        ])
        
    elif MODE == "VIEW":
        if not alarms:
            oled_write([("查看鬧鐘", 0), ("無設定", 24), ("長按A新增", 48)])
        else:
            safe_idx = max(0, min(view_idx, len(alarms)-1))
            a = alarms[safe_idx]
            status = "開啟" if a["enabled"] else "關閉"
            repeat = "每天" if a["repeat"] else "單次"
            oled_write([
                (f"鬧鐘 {safe_idx+1}/{len(alarms)}", 0),
                (f"{a['h']:02d}:{a['m']:02d} {status}", 16),
                (f"{repeat} {MUSIC_NAME[a['music']][:3]}", 32),
                ("短A開關 長A刪除", 48)
            ])

    elif MODE == "SET_TIME":
        h_mk = "<<" if cursor_pos == 0 else "  "
        m_mk = "<<" if cursor_pos == 1 else "  "
        oled_write([
            ("1.設定時間", 0),
            (f"時: {temp_setting['h']:02d} {h_mk}", 20),
            (f"分: {temp_setting['m']:02d} {m_mk}", 36),
            ("A切換 B加 長A下", 52)
        ])

    elif MODE == "SET_REPEAT":
        rpt = "每天" if temp_setting['repeat'] else "僅一次"
        oled_write([
            ("2.設定重複", 0),
            (f"模式: {rpt}", 24),
            ("B切換  長A下一步", 48)
        ])

    elif MODE == "SET_MUSIC":
        m_name = MUSIC_NAME[temp_setting['music']]
        oled_write([
            ("3.設定音樂", 0),
            (f"{m_name}", 24),
            ("B換首  長A儲存", 48)
        ])
            
    elif MODE == "RINGING":
        oled_write([
            ("鬧鐘響鈴中!", 0),
            ("A: 貪睡 (5分)", 24),
            ("B: 關閉", 48)
        ])

# ============================================================
# 音樂功能
# ============================================================
async def play_preview(music_idx):
    global _preview_task
    try:
        melody = MELODY.get(music_idx, MELODY[0])
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 5000:
            for note, d in melody:
                if time.ticks_diff(time.ticks_ms(), start) >= 5000: break
                freq = NOTE_FREQS.get(note, 0)
                if freq > 0: speaker.freq(freq); speaker.duty(512)
                else: speaker.duty(0)
                await asyncio.sleep_ms(int(d))
                speaker.duty(0); await asyncio.sleep_ms(40)
    except asyncio.CancelledError: pass
    finally: speaker.duty(0)

def start_preview(idx):
    global _preview_task
    if _preview_task: _preview_task.cancel()
    _preview_task = asyncio.create_task(play_preview(idx))

def stop_preview():
    global _preview_task
    if _preview_task: _preview_task.cancel()
    speaker.duty(0)

# ============================================================
# 按鈕事件 (腳位 16/21)
# ============================================================
def on_btnA_click(_id, _pin):
    """按鈕A (Pin 16): 選擇/確認"""
    global MODE, view_idx, cursor_pos
    if MODE == "CLOCK":
        MODE = "VIEW"; view_idx = 0
    elif MODE == "VIEW" and alarms:
        idx = max(0, min(view_idx, len(alarms)-1))
        alarms[idx]["enabled"] = not alarms[idx]["enabled"]; save_alarms()
    elif MODE == "SET_TIME":
        cursor_pos = (cursor_pos + 1) % 2
    elif MODE == "RINGING":
        global is_ringing; is_ringing = False; do_snooze()

def on_btnA_long(_id, _pin):
    """長按A: 進入設定/刪除"""
    global MODE, temp_setting, cursor_pos, view_idx
    if MODE == "CLOCK":
        now = taiwan_time()
        temp_setting = {"h":now[3], "m":now[4], "repeat":0, "music":0}
        cursor_pos = 0; MODE = "SET_TIME"
    elif MODE == "SET_TIME": MODE = "SET_REPEAT"
    elif MODE == "SET_REPEAT":
        MODE = "SET_MUSIC"; start_preview(temp_setting["music"])
    elif MODE == "SET_MUSIC":
        stop_preview()
        add_alarm(temp_setting["h"], temp_setting["m"], temp_setting["repeat"], temp_setting["music"])
        MODE = "CLOCK"; print("[System] 鬧鐘已儲存")
    elif MODE == "VIEW" and alarms:
        idx = max(0, min(view_idx, len(alarms)-1))
        del alarms[idx]; save_alarms()
        if len(alarms) == 0: MODE = "CLOCK"
        else: view_idx = max(0, min(view_idx, len(alarms)-1))

def on_btnB_click(_id, _pin):
    """按鈕B (Pin 21): 移動/調整"""
    global MODE, view_idx
    if MODE == "VIEW" and alarms:
        view_idx = (view_idx + 1) % len(alarms)
    elif MODE == "SET_TIME":
        if cursor_pos == 0: temp_setting["h"] = (temp_setting["h"] + 1) % 24
        else: temp_setting["m"] = (temp_setting["m"] + 1) % 60
    elif MODE == "SET_REPEAT":
        temp_setting["repeat"] = 1 - temp_setting["repeat"]
    elif MODE == "SET_MUSIC":
        temp_setting["music"] = (temp_setting["music"] + 1) % len(MUSIC_NAME)
        start_preview(temp_setting["music"])
    elif MODE == "RINGING":
        global is_ringing; is_ringing = False

def on_btnB_long(_id, _pin):
    """長按B: 返回/取消"""
    global MODE
    if MODE != "RINGING":
        stop_preview(); MODE = "CLOCK"

# ============================================================
# 響鈴與背景任務
# ============================================================
async def ring_alarm(music_index, alarm_obj=None):
    global is_ringing, MODE
    if is_ringing: return
    is_ringing = True; MODE = "RINGING"
    if alarm_obj and not alarm_obj.get("repeat"):
        alarm_obj["enabled"] = False; save_alarms()
    
    melody = MELODY.get(music_index, MELODY[0])
    start_ticks = time.ticks_ms()
    timeout = False 
    try:
        while is_ringing:
            if time.ticks_diff(time.ticks_ms(), start_ticks) > (RING_LIMIT_SEC * 1000):
                timeout = True; break 
            for note, d in melody:
                if not is_ringing or time.ticks_diff(time.ticks_ms(), start_ticks) > (RING_LIMIT_SEC * 1000):
                    if is_ringing: timeout = True
                    is_ringing = False; break
                freq = NOTE_FREQS.get(note, 0)
                if freq > 0: speaker.freq(freq); speaker.duty(512) 
                else: speaker.duty(0)
                await asyncio.sleep_ms(int(d))
                speaker.duty(0); await asyncio.sleep_ms(40)
    finally:
        speaker.duty(0); is_ringing = False; MODE = "CLOCK"
        if timeout: do_snooze()

def do_snooze():
    now = taiwan_time()
    m = now[4] + SNOOZE_MIN
    h = now[3]
    if m >= 60: m -= 60; h = (h + 1) % 24
    add_alarm(h, m, 0, 0)

# 2. 修改：實作訊息處理函式，不要只是 pass
async def mqtt_msg_handler(topic, msg, retained, properties=None):
    try:
        # 將 bytes 轉為字串以便閱讀
        topic_str = topic.decode() if isinstance(topic, bytes) else topic
        msg_str = msg.decode() if isinstance(msg, bytes) else msg
        
        print(f"\n[MQTT 收到訊息] 主題: {topic_str}, 內容: {msg_str}")
        
        # (選用) 可以在這裡加入控制邏輯，例如收到 "OPEN" 就開燈
        # if msg_str == "OPEN":
        #     print("執行開燈...")
            
    except Exception as e:
        print(f"[MQTT Handler Error] {e}")

async def dht_mqtt_task(ssid, password):
    mqtt = MqttManager(ssid, password)
    mqtt.external_handler = mqtt_msg_handler
    
    # 連線
    await mqtt.connect()
    
    if mqtt.is_connected():
        # 訂閱原本的溫濕度主題 (確認自己發送的資料)
        await mqtt.subscribe(TOPIC_TEMP)
        await mqtt.subscribe(TOPIC_HUMI)
        
        # 【重要】同時訂閱 config 中設定的「指令主題」，這樣別人才傳得進來
        import config
        if 'cmd' in config.MQTT_TOPICS:
            cmd_topic = config.MQTT_TOPICS['cmd']
            await mqtt.subscribe(cmd_topic)
            print(f"[System] 已監聽指令主題: {cmd_topic}")

    while True:
        try:
            dht_sensor.measure()
            t, h = dht_sensor.temperature(), dht_sensor.humidity()
            global current_env
            current_env["temp"] = str(t); current_env["humi"] = str(h)
            
            if mqtt.is_connected():
                # 發布溫濕度
                await mqtt.publish(TOPIC_TEMP, str(t), qos=0)
                await mqtt.publish(TOPIC_HUMI, str(h), qos=0)
            else:
                print("[System] MQTT 斷線，嘗試重連...")
                await mqtt.connect()
                # 重連後重新訂閱
                if mqtt.is_connected():
                    await mqtt.subscribe(TOPIC_TEMP)
                    import config
                    if 'cmd' in config.MQTT_TOPICS:
                        await mqtt.subscribe(config.MQTT_TOPICS['cmd'])
                        
        except Exception as e:
            print(f"[DHT Task Error] {e}")
            
        await asyncio.sleep(10)

async def check_alarm_task():
    global _last_rung_key
    while True:
        if MODE == "CLOCK":
            now = taiwan_time()
            key = (now[3], now[4])
            if key != _last_rung_key:
                for a in alarms:
                    if a.get("enabled") and a["h"] == now[3] and a["m"] == now[4]:
                        _last_rung_key = key
                        asyncio.create_task(ring_alarm(a["music"], a))
                        break
        await asyncio.sleep(1)

async def ui_display_task():
    while True:
        try: show_ui()
        except: pass
        await asyncio.sleep_ms(200)

async def handle_client(reader, writer):
    try:
        raw = await asyncio.wait_for(reader.read(1024), 5)
        if not raw: return
        req = raw.decode()
        res = ""
        
        if "/env" in req: res = json.dumps(current_env)
        elif "/time" in req:
            t = taiwan_time()
            res = json.dumps({"y":t[0],"M":t[1],"d":t[2],"h":t[3],"m":t[4],"s":t[5]})
        elif "/alarms" in req: res = json.dumps({"alarms": alarms})
        elif "/add?" in req:
            try:
                q = req.split("/add?")[1].split(" ")[0]
                d = {kv.split("=")[0]: kv.split("=")[1] for kv in q.split("&")}
                add_alarm(d["h"], d["m"], d["repeat"], d["music"])
                res = "OK"
            except: res = "Error"
        elif "/switch?id=" in req:
            try:
                idx = int(req.split("id=")[1].split(" ")[0])
                if 0 <= idx < len(alarms):
                    alarms[idx]["enabled"] = not alarms[idx]["enabled"]
                    save_alarms(); res = "OK"
            except: res = "Error"
        elif "/delete?id=" in req:
            try:
                idx = int(req.split("id=")[1].split(" ")[0])
                del alarms[idx]; save_alarms(); res = "OK"
            except: res = "Error"
        else:
            try:
                with open("web/index.html") as f:
                    writer.write("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n")
                    for line in f: writer.write(line)
                    await writer.drain(); return
            except: pass
        writer.write("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n" + res)
        await writer.drain()
    except: pass
    finally: 
        try: await writer.aclose()
        except: pass

async def main():
    print("系統啟動...")
    # 蜂鳴器測試
    speaker.freq(1000); speaker.duty(512); await asyncio.sleep(0.1); speaker.duty(0)
    
    ssid, pw = await connect_wifi()
    ip = network.WLAN(network.STA_IF).ifconfig()[0]
    current_env["ip"] = ip
    print(f"IP: {ip}")
    
    # 為了避免崩潰，IP 只在開機時顯示 5 秒，之後進入正常時鐘模式
    oled_write([("IP 位址:", 0), (ip, 16), ("啟動中...", 32)])
    await asyncio.sleep(5)
    
    await sync_time()
    load_alarms()
    
    asyncio.create_task(dht_mqtt_task(ssid, pw))
    asyncio.create_task(check_alarm_task())
    asyncio.create_task(ui_display_task())
    await asyncio.start_server(handle_client, "0.0.0.0", 80)
    
    # 【關鍵修改】按鈕腳位 16, 21
    btnA = DebouncedButton(16, on_click=on_btnA_click, on_long=on_btnA_long)
    btnB = DebouncedButton(21, on_click=on_btnB_click, on_long=on_btnB_long)
    
    while True:
        btnA.update(); btnB.update(); await asyncio.sleep_ms(20)

try: asyncio.run(main())
finally: speaker.duty(0)