import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from fastapi import FastAPI
import uvicorn
import threading
import os

TOKEN = "vk1.a.NJgDVnKsv7inayrlqMXqJmevAVJBX0jAWCD33RC4w27CYWekHlXCvHFFsXNHp5447AHdmZboM2-SVBuyCk5Up1BqIxGOmkwwZ3pRjlizFJ8ogcMygQSMGxto-kzEm6lNBGqQjTifcD_MY4kLVejoqG_JcstMe3JXBuLc2wW_mWux-3gH2DVGckYcgr_oKKq5lV_c3vaMxvrGMTBYufPWgg"
GROUP_ID = 236517090

vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, group_id=GROUP_ID)

def send_msg(peer_id, msg):
    vk.messages.send(peer_id=peer_id, message=msg, random_id=get_random_id())

def bot_worker():
    print("✅ ТЕСТОВЫЙ БОТ ЗАПУЩЕН")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            msg = event.obj.message
            if msg['text'] == "/пинг":
                send_msg(msg['peer_id'], "🏓 Понг!")

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

if __name__ == "__main__":
    threading.Thread(target=bot_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
