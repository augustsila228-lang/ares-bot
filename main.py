# ============================================
# ARES: ЧАТ-МЕНЕДЖЕР (РАБОЧАЯ ВЕРСИЯ)
# ============================================

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import time
from fastapi import FastAPI
import uvicorn
import threading
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "vk1.a.mjjuX0_S2Zx-ra-sSHYRNM22uoabRZiXCWoyCU7Kq_e0Bpho5mRRD7CE9wKd96lLSiwNxl1YkLgyCafmIG78pZGzyQD0B131Pvq6Bg57uLpuP_WUWt_jXqkFaWhCAWVzJC-F5-sPyzMIdQ26XFQK52lesM-J5dKYuKHNfD5NnlJ8TapES2zo5azgGepPg0i8mMxL6edbZURWx4aatdp7BA"
GROUP_ID = 236517090
BOT_NAME = "ARES"
PREFIX = "/"

print("✅ Бот запускается...")

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

def send_msg(peer_id, message):
    vk.messages.send(peer_id=peer_id, message=message, random_id=get_random_id())

print("🚀 Бот слушает события...")

def bot_worker():
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    text = msg['text'].strip()
                    if text == "/пинг":
                        send_msg(msg['peer_id'], "🏓 Понг!")
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

if __name__ == "__main__":
    thread = threading.Thread(target=bot_worker, daemon=True)
    thread.start()
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
