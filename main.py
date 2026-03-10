# ============================================
# ARES: ТЕСТОВАЯ ВЕРСИЯ С ЯРКИМИ ЛОГАМИ
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
TOKEN = "vk1.a.UNxYimCDso61gjA8nJ1tkq-Mqe5PEpym6qli4sMSeqiHmYr4ST80kbGA3bDGLL1sxsTsPqHHxoI8UlSzMu75RcGcEkUrM3cgYQ3WCbnxk_nrA6tafME59-Z_O2V6oI7saA5WoYZlGLsIv-REhzlu0JyVlejwF_IlVE1AdNQgyB0Yh-0yVez0zXTp2lTk4XAxSWBsVnL2oyr4BF00xB6hsg"
GROUP_ID = 236517090

print("🔥🔥🔥 СКРИПТ ЗАПУЩЕН 🔥🔥🔥")
print(f"🔑 Токен: {TOKEN[:20]}...")
print(f"📦 Группа ID: {GROUP_ID}")

# Пытаемся подключиться к VK
try:
    print("⏳ Подключаюсь к VK API...")
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    print("✅ VK API подключен")

    print("⏳ Инициализирую LongPoll...")
    longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
    print("✅ LongPoll готов")
except Exception as e:
    print(f"❌ ОШИБКА ПОДКЛЮЧЕНИЯ К VK: {e}")
    # Не выходим, чтобы FastAPI всё равно запустился

def send_msg(peer_id, message):
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=get_random_id()
        )
        print(f"✅ Отправлено: {message}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

def bot_worker():
    print("🚀🚀🚀 БОТ ЗАПУЩЕН В ПОТОКЕ 🚀🚀🚀")
    print("👂 Слушаю сообщения...")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    peer_id = msg['peer_id']
                    text = msg['text'].strip()
                    print(f"💬 ПОЛУЧЕНО СООБЩЕНИЕ: {text}")
                    
                    if text == "/пинг":
                        send_msg(peer_id, "🏓 Понг!")
                    elif text == "/тест":
                        send_msg(peer_id, "✅ Тест пройден!")
        except Exception as e:
            print(f"❌ ОШИБКА В ЦИКЛЕ: {e}")
            time.sleep(5)

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "message": "ARES bot is running"}

if __name__ == "__main__":
    print("⏳ Запускаю поток бота...")
    thread = threading.Thread(target=bot_worker, daemon=True)
    thread.start()
    print("✅ Поток запущен")

    print("⏳ Запускаю FastAPI сервер...")
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
