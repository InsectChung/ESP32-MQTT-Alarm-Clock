from machine import Pin
import utime as time

class DebouncedButton:
    def __init__(self, pin_no, id=0, on_click=None, on_long=None, on_double=None, double_ms=400):
        # === 初始化輸入腳位 ===
        # 使用 PULL_UP 表示預設為高電位，按下時會變成低電位
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_UP)

        # === 使用者參數 ===
        self.id = id
        self.on_click = on_click
        self.on_long = on_long
        self.on_double = on_double
        self.double_ms = double_ms  # 雙擊間隔時間 (ms)

        # === 內部固定參數 ===
        self._LONG_THRESHOLD = 800   # 長按判斷閾值 (ms)

        # === 狀態變數 ===
        self._last_state = self.pin.value()  # 上次讀取的腳位狀態
        self._pressed_time = 0               # 記錄按下的時間點
        self._last_click_time = 0            # 上次放開按鈕的時間
        self._click_pending = False          # 是否有等待確認的點擊事件
        self._click_count = 0                # 點擊次數計數器
        self._is_pressed = False             # 是否目前處於按下狀態

    # -------------------------------------------------------------------------
    def wait_pin_stable(self):
        """
        等待腳位電位穩定，作為硬體去彈跳處理。
        原理：連續 10ms 內狀態不變才視為穩定。
        """
        cur = self.pin.value()  # 目前腳位電位 (0=按下, 1=放開)
        counter = 0
        while counter < 10:
            if self.pin.value() != cur:
                # 狀態變化 → 計數歸零，重新計算
                counter = 0
                cur = self.pin.value()
            else:
                # 狀態穩定 → 增加計數
                counter += 1
            time.sleep_ms(1)  # 每次間隔 1ms，總計約 10ms
        return cur  # 回傳最終穩定狀態

    # -------------------------------------------------------------------------
    def update(self):
        """
        更新按鈕狀態，並在需要時觸發對應回呼函數。
        建議在主程式或 asyncio 迴圈中以 5~20ms 間隔呼叫一次。
        """
        state = self.pin.value()  # 讀取目前按鈕狀態

        # 若與上次狀態不同 → 代表有變化（可能是按下或放開）
        if state != self._last_state:
            # 進行去彈跳處理，確保狀態穩定
            state = self.wait_pin_stable()
            self._last_state = state  # 更新狀態紀錄

            # =============================
            # 按下事件 (狀態由高→低)
            # =============================
            if state == 0:
                self._pressed_time = time.ticks_ms()  # 記錄按下的時間
                self._is_pressed = True               # 標記為「按下中」

            # =============================
            # 放開事件 (狀態由低→高)
            # =============================
            elif state == 1 and self._is_pressed:
                self._is_pressed = False
                # 計算按下的持續時間
                press_dur = time.ticks_diff(time.ticks_ms(), self._pressed_time)

                # ---- 長按判斷 ----
                if press_dur >= self._LONG_THRESHOLD:
                    # 若長按時間超過閾值 → 觸發長按回呼
                    if self.on_long:
                        self.on_long(self.id, self.pin)
                    # 長按後清除點擊狀態，避免被誤認為單擊
                    self._click_pending = False
                    self._click_count = 0

                # ---- 短按（單擊或雙擊） ----
                else:
                    now = time.ticks_ms()
                    diff = time.ticks_diff(now, self._last_click_time)

                    if diff < self.double_ms:
                        # 若與上次放開時間間隔小於 double_ms → 判定為雙擊
                        self._click_count += 1
                    else:
                        # 超過時間 → 視為新的一次點擊
                        self._click_count = 1

                    # 更新時間與等待標記
                    self._last_click_time = now
                    self._click_pending = True

        # -----------------------------------------------------------------
        # 若有「尚未確認」的點擊事件 → 檢查是否該觸發單擊或雙擊
        # -----------------------------------------------------------------
        if self._click_pending:
            diff = time.ticks_diff(time.ticks_ms(), self._last_click_time)

            # 超過雙擊等待時間 → 確認為單擊或雙擊事件
            if diff > self.double_ms:
                if self._click_count == 1:
                    # 只點了一次 → 單擊
                    if self.on_click:
                        self.on_click(self.id, self.pin)
                elif self._click_count >= 2:
                    # 點擊兩次以上 → 雙擊
                    if self.on_double:
                        self.on_double(self.id, self.pin)

                # 事件完成 → 重置狀態
                self._click_pending = False
                self._click_count = 0
