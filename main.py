import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import time
from fastapi import FastAPI
import uvicorn
import threading
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "vk1.a.NJgDVnKsv7inayrlqMXqJmevAVJBX0jAWCD33RC4w27CYWekHlXCvHFFsXNHp5447AHdmZboM2-SVBuyCk5Up1BqIxGOmkwwZ3pRjlizFJ8ogcMygQSMGxto-kzEm6lNBGqQjTifcD_MY4kLVejoqG_JcstMe3JXBuLc2wW_mWux-3gH2DVGckYcgr_oKKq5lV_c3vaMxvrGMTBYufPWgg"
GROUP_ID = 236517090

print("🟢 Запускаю тестового бота...")
print(f"🟢 Токен: {TOKEN[:15]}...")
print(f"🟢 Группа ID: {GROUP_ID}")

try:
    # Создаем сессию VK
    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    
    # Проверяем соединение
    group_info = vk.groups.getById()
    print(f"✅ Подключение к группе успешно: {group_info[0]['name']}")
    
    longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)
    print("✅ LongPoll инициализирован")
    
except Exception as e:
    print(f"❌ Ошибка при подключении к VK: {e}")
    print("❌ Токен недействителен или группа недоступна")

def send_msg(peer_id, message):
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=get_random_id()
        )
        print(f"✅ Отправлено сообщение в {peer_id}")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

def bot_worker():
    print("🚀 Бот запущен и слушает сообщения...")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    msg = event.obj.message
                    peer_id = msg['peer_id']
                    text = msg['text'].strip()
                    
                    print(f"📩 Получено сообщение: {text} от {msg['from_id']}")
                    
                    if text == "/пинг":
                        send_msg(peer_id, "🏓 Понг! Бот работает!")
                    elif text == "/тест":
                        send_msg(peer_id, "✅ Тест пройден!")
                    elif text == "/помощь":
                        send_msg(peer_id, "📋 Доступные команды: /пинг, /тест")
                        
        except Exception as e:
            print(f"❌ Ошибка в цикле: {e}")
            time.sleep(5)

# FastAPI заглушка для Railway
app = FastAPI()

@app.get("/")
def root():
    return {"status": "Бот работает", "time": time.time()}

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=bot_worker, daemon=True)
    bot_thread.start()
    
    # Запускаем FastAPI сервер
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 FastAPI сервер запущен на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
