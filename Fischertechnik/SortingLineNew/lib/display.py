import os
import time
import threading
import signal

import ftgui

display = ftgui.fttxt2_gui_connector("app")
display.open()

def display_monitoring():
    while display.is_open():
        time.sleep(1)
    os.kill(os.getpid(), signal.SIGTERM)
    exit()

threading.Thread(target=display_monitoring, daemon=True).start()
