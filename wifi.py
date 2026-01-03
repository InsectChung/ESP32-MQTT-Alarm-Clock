"""
communication/wifi.py - WiFi 連線管理（修正版）
基於 ns_tools.py 與 aiot_tools.py
"""

import config
import time


async def connect_wifi():
    """
    連線到已知 WiFi 網路
    使用 ns_tools 的 connect_to_known_wifi() 函數
    
    返回: (ssid, password) 元組
    """
    print("[WiFi] 嘗試連線到已知 WiFi 網路...")
    
    try:
        from ns_tools import connect_to_known_wifi
        ssid, password = connect_to_known_wifi(config.WIFI_PROFILES, try_time=10)
        
        if ssid and password:
            print(f"[WiFi] 已連線到: {ssid}")
            return ssid, password
        else:
            print("[WiFi] 未找到已知 WiFi 或連線失敗")
            # 使用第一個預設配置作為備選
            ssid = list(config.WIFI_PROFILES.keys())[0]
            password = config.WIFI_PROFILES[ssid]
            return ssid, password
    
    except ImportError:
        print("[WiFi] 缺少 ns_tools 模組，使用預設配置")
        ssid = list(config.WIFI_PROFILES.keys())[0]
        password = config.WIFI_PROFILES[ssid]
        return ssid, password


async def sync_time():
    """
    同步系統時間到本地時區（UTC+8）
    使用 ns_tools 或 aiot_tools 的時間同步函數
    """
    print("[Time] 同步系統時間...")
    
    try:
        # 嘗試優先使用 ns_tools 的 mySetTime()（功能更完善）
        from ns_tools import mySetTime
        result = mySetTime(timezone=8, max_retries=3)
        if result:
            print("[Time] 時間已同步 (ns_tools)")
            return True
    except (ImportError, Exception) as e:
        print(f"[Time] ns_tools 時間同步失敗: {e}")
    
    try:
        # 備選：使用 aiot_tools 的 set_time()
        from aiot_tools import set_time
        set_time(timezone=8)
        print("[Time] 時間已同步 (aiot_tools)")
        return True
    except (ImportError, Exception) as e:
        print(f"[Time] aiot_tools 時間同步失敗: {e}")
    
    print("[Time] 時間同步失敗，使用系統預設時間")
    return False


def get_current_time():
    """
    取得格式化的本地當前日期、星期、時間
    使用 ns_tools 或 aiot_tools 的時間取得函數
    
    返回: (date_str, weekday_str, time_str) 元組
    """
    try:
        # 優先使用 ns_tools 的 myGetTime()
        from ns_tools import myGetTime
        return myGetTime()
    except ImportError:
        pass
    
    try:
        # 備選：使用 aiot_tools 的 get_time()
        from aiot_tools import get_time
        return get_time()
    except ImportError:
        pass
    
    # 若兩個庫都不可用，使用內建時間函數
    import time
    now = time.localtime()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    
    date_str = '{:04d}/{:02d}/{:02d}'.format(now[0], now[1], now[2])
    time_str = '{:02d}:{:02d}:{:02d}'.format(now[3], now[4], now[5])
    weekday_str = weekdays[now[6]]
    
    return date_str, weekday_str, time_str

