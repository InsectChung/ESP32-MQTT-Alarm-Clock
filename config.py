"""
config.py - 全域配置文件
集中管理所有硬體腳位、MQTT 設定、WiFi 設定等
"""

# ==================== 硬體腳位配置 ====================

# LED 腳位配置（GPIO）
LED_RED_PIN = 39
LED_GREEN_PIN = 38
LED_BLUE_PIN = 3

# 按鈕腳位配置（GPIO）
BUTTON1_PIN = 16
BUTTON2_PIN = 21

# 感測器腳位配置
DHT11_PIN = 18
# TEMT_ADC_PIN = 8

# I2C 配置（OLED）
I2C_ID = 0
I2C_SCL_PIN = 7
I2C_SDA_PIN = 5
OLED_WIDTH = 128
OLED_HEIGHT = 64

# SPI 配置（RFID）
# RFID_SCK_PIN = 12
# RFID_MOSI_PIN = 11
# RFID_MISO_PIN = 10
# RFID_RST_PIN = 9
# RFID_CS_PIN = 13

# ==================== 感測器參數 ====================

# 光感測器閾值
# LIGHT_THRESHOLD_ON = 1000      # 亮度低於此值，點亮 LED
# LIGHT_THRESHOLD_OFF = 1100     # 亮度高於此值，熄滅 LED
# LIGHT_POLL_INTERVAL_MS = 50    # 光感測輪詢間隔

# DHT11 量測間隔
DHT11_POLL_INTERVAL_SEC = 2

# OLED 更新間隔
OLED_UPDATE_INTERVAL_SEC = 1

# RFID 讀卡間隔（避免反應過快）
# RFID_POLL_INTERVAL_MS = 500

# 按鈕去彈跳時間
BUTTON_DEBOUNCE_MS = 20         # 按鈕穩定判定時間
BUTTON_POLL_INTERVAL_MS = 30    # 按鈕輪詢間隔

# ==================== WiFi 配置 ====================

# 已知 WiFi 網路清單（SSID: 密碼）
WIFI_PROFILES = {
    'Your_WiFi_SSID': 'Your_WiFi_Password',
    'School_WiFi': '12345678'
}

# 時區設定（UTC+8 for Taiwan）
TIMEZONE_OFFSET_SEC = 8 * 3600

# ==================== MQTT 配置 ====================

# MQTT Broker 設定
MQTT_BROKER = 'broker.emqx.io'
# MQTT_BROKER = 'test.mosquitto.org'
MQTT_PORT = 1883

# MQTT Topic 配置
MQTT_TOPICS = {
    'cmd': b'nuu/csie/iot1133/cmd01',           # 接收指令
    'temp_humi': b'nuu/csie/iot1133/TempHumi',  # 發佈溫濕度
    'subscribe': b'nuu/csie/iot1133/#',         # 訂閱所有
}

# MQTT 重連設定
MQTT_RECONNECT_INITIAL_DELAY_SEC = 2     # 初始重連延遲
MQTT_RECONNECT_MAX_DELAY_SEC = 60        # 最大重連延遲
MQTT_RECONNECT_BACKOFF_FACTOR = 1.5      # 指數退避因子

# ==================== 字體配置 ====================

FONT_PATH = './lib/fonts/fusion_bdf.12'

# ==================== 顏色對應 ====================

# RGB LED 8 色對應 (3-bit: RGB)
COLOR_MAP = {
    0: ('黑', 0b000),
    1: ('藍', 0b001),
    2: ('綠', 0b010),
    3: ('青', 0b011),
    4: ('紅', 0b100),
    5: ('紫', 0b101),
    6: ('黃', 0b110),
    7: ('白', 0b111),
}

# ==================== 裝置識別 ====================

DEVICE_NAME = '蟲蟲的 IoT 裝置'
DEVICE_ID = 'iot001'

