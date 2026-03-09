# ============================================
# ARES: ПРОСТОЙ ТЕСТОВЫЙ БОТ
# ============================================

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import time
import threading
from fastapi import FastAPI
import uvicorn
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "vk1.a.UNxYimCDso61gjA8nJ1tkq-Mqe5PEpym6qli4sMSeqiHmYr4ST80kbGA3bDGLL1sxsTsPqHHxoI8UlSzMu75RcGcEkUrM3cgYQ3WCbnxk_nrA6tafME59-Z_O2V6oI7saA5WoYZlGLsIv-REhzlu0JyVlejwF_IlVE1AdNQgyB0Yh-0yVez0zXTp2lTk4XAxSWBsVnL2oyr4BF00xB6hsg"
GROUP_ID = 236517090

print("🟢 Запуск бота...")

try:
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
    print("✅ Бот инициализирован")
except Exception as e:
    print(f"❌ Ошибка: {e}")

def send_msg(peer_id, message):
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=get_random_id()
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def bot_worker():
    print("🚀 Бот слушает события...")  # Эту строчку ты должен увидеть в логах!
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    text = msg['text'].strip()
                    print(f"Получено сообщение: {text}")
                    if text == "/пинг":
                        send_msg(msg['peer_id'], "🏓 Понг!")
                    elif text == "/тест":
                        send_msg(msg['peer_id'], "✅ Бот работает!")
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
    uvicorn.run(app, host="0.0.0.0", port=port) # ============================================
# ARES: ПРОСТОЙ ТЕСТОВЫЙ БОТ
# ============================================

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import time
import threading
from fastapi import FastAPI
import uvicorn
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "vk1.a.UNxYimCDso61gjA8nJ1tkq-Mqe5PEpym6qli4sMSeqiHmYr4ST80kbGA3bDGLL1sxsTsPqHHxoI8UlSzMu75RcGcEkUrM3cgYQ3WCbnxk_nrA6tafME59-Z_O2V6oI7saA5WoYZlGLsIv-REhzlu0JyVlejwF_IlVE1AdNQgyB0Yh-0yVez0zXTp2lTk4XAxSWBsVnL2oyr4BF00xB6hsg"
GROUP_ID = 236517090

print("🟢 Запуск бота...")

try:
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
    print("✅ Бот инициализирован")
except Exception as e:
    print(f"❌ Ошибка: {e}")

def send_msg(peer_id, message):
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=get_random_id()
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def bot_worker():
    print("🚀 Бот слушает события...")  # Эту строчку ты должен увидеть в логах!
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    text = msg['text'].strip()
                    print(f"Получено сообщение: {text}")
                    if text == "/пинг":
                        send_msg(msg['peer_id'], "🏓 Понг!")
                    elif text == "/тест":
                        send_msg(msg['peer_id'], "✅ Бот работает!")
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
