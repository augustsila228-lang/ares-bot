# app.py
# Минимальный безопасный чат-менеджер для ВКонтакте (vk_api, LongPoll).
# Требования: Python 3.10+, pip install vk_api
# Вставьте VK_TOKEN и OWNER_ID перед запуском.

import time
import re
from typing import Dict
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType

# ====== Настройки: вставьте свои данные ======
VK_TOKEN = "vk1.a.mjjuX0_S2Zx-ra-sSHYRNM22uoabRZiXCWoyCU7Kq_e0Bpho5mRRD7CE9wKd96lLSiwNxl1YkLgyCafmIG78pZGzyQD0B131Pvq6Bg57uLpuP_WUWt_jXqkFaWhCAWVzJC-F5-sPyzMIdQ26XFQK52lesM-J5dKYuKHNfD5NnlJ8TapES2zo5azgGepPg0i8mMxL6edbZURWx4aatdp7BA"
OWNER_ID = 853348780  # Ваш VK id (число)
COMMAND_PREFIX = ("/", "!",)
# ============================================

vk_session = VkApi(token=VK_TOKEN)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# Простое хранилище в памяти. Для длительной работы замените на БД/файл.
CHAT_DATA: Dict[int, Dict] = {}  # peer_id -> {"roles": {user_id: role}, "warns": {user_id: int}, "settings": {...}}

def ensure_chat(peer_id: int):
    if peer_id not in CHAT_DATA:
        CHAT_DATA[peer_id] = {"roles": {}, "warns": {}, "settings": {"games": False}}

def send(peer_id: int, text: str):
    vk.messages.send(peer_id=peer_id, message=text, random_id=int(time.time() * 1000) % (2**31))

def parse_command(text: str):
    text = text.strip()
    if not text:
        return None, ""
    if text[0] in COMMAND_PREFIX:
        parts = text[1:].split(None, 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        return cmd, args
    return None, ""

def is_owner(user_id: int) -> bool:
    return int(user_id) == int(OWNER_ID)

# Команды
def cmd_ping(peer_id, from_id, args):
    send(peer_id, "pong")

def cmd_start(peer_id, from_id, args):
    ensure_chat(peer_id)
    send(peer_id, "Бот инициализирован в беседе.")

def cmd_help(peer_id, from_id, args):
    send(peer_id,
         "/ping — проверить отклик\n"
         "/start — инициализировать бота\n"
         "/stats [id] — показать ID\n"
         "/warn [id] — выдать предупреждение (владелец/админ)\n"
         "/unwarn [id] — снять предупреждение (владелец/админ)\n"
         "/setrole [id] [role] — установить роль (владелец)\n"
         "/getroles — показать роли в чате")

def cmd_stats(peer_id, from_id, args):
    target = args.strip()
    if not target:
        send(peer_id, f"Ваш ID: {from_id}")
        return
    m = re.search(r"\d+", target)
    if not m:
        send(peer_id, "Не удалось найти ID в аргументах.")
        return
    send(peer_id, f"ID: {m.group(0)}")

def cmd_warn(peer_id, from_id, args):
    ensure_chat(peer_id)
    # разрешение: владелец или роль "admin"
    if not (is_owner(from_id) or CHAT_DATA[peer_id]["roles"].get(from_id) == "admin"):
        send(peer_id, "Нет прав.")
        return
    m = re.search(r"\d+", args or "")
    if not m:
        send(peer_id, "Укажите ID для предупреждения.")
        return
    uid = int(m.group(0))
    warns = CHAT_DATA[peer_id]["warns"].setdefault(uid, 0) + 1
    CHAT_DATA[peer_id]["warns"][uid] = warns
    send(peer_id, f"Пользователю {uid} выдано предупреждение. Всего: {warns}")

def cmd_unwarn(peer_id, from_id, args):
    ensure_chat(peer_id)
    if not (is_owner(from_id) or CHAT_DATA[peer_id]["roles"].get(from_id) == "admin"):
        send(peer_id, "Нет прав.")
        return
    m = re.search(r"\d+", args or "")
    if not m:
        send(peer_id, "Укажите ID.")
        return
    uid = int(m.group(0))
    current = CHAT_DATA[peer_id]["warns"].get(uid, 0)
    if current <= 0:
        send(peer_id, "У пользователя нет предупреждений.")
        return
    CHAT_DATA[peer_id]["warns"][uid] = current - 1
    send(peer_id, f"Снято предупреждение у {uid}. Осталось: {CHAT_DATA[peer_id]['warns'][uid]}")

def cmd_setrole(peer_id, from_id, args):
    ensure_chat(peer_id)
    if not is_owner(from_id):
        send(peer_id, "Только владелец может назначать роли.")
        return
    parts = args.split(None, 1)
    if len(parts) < 2:
        send(peer_id, "Использование: /setrole [id] [role]")
        return
    m = re.search(r"\d+", parts[0])
    if not m:
        send(peer_id, "Не найден ID.")
        return
    uid = int(m.group(0))
    role = parts[1].strip().lower()
    CHAT_DATA[peer_id]["roles"][uid] = role
    send(peer_id, f"Роль пользователя {uid} установлена: {role}")

def cmd_getroles(peer_id, from_id, args):
    ensure_chat(peer_id)
    roles = CHAT_DATA[peer_id]["roles"]
    if not roles:
        send(peer_id, "Роли не заданы.")
        return
    lines = [f"{uid}: {r}" for uid, r in roles.items()]
    send(peer_id, "\n".join(lines))

COMMANDS = {
    "ping": cmd_ping,
    "start": cmd_start,
    "help": cmd_help,
    "stats": cmd_stats,
    "warn": cmd_warn,
    "unwarn": cmd_unwarn,
    "setrole": cmd_setrole,
    "getroles": cmd_getroles,
}

def handle_message(event):
    peer_id = event.peer_id
    from_id = event.user_id or event.from_user
    text = (event.text or "").strip()
    cmd, args = parse_command(text)
    if not cmd:
        return
    func = COMMANDS.get(cmd)
    if func:
        func(peer_id, from_id, args)
    else:
        send(peer_id, "Неизвестная команда. /help")

def main():
    print("Бот запущен.")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
            try:
                handle_message(event)
            except Exception as e:
                try:
                    send(event.peer_id, f"Ошибка: {e}")
                except:
                    pass

if __name__ == "__main__":
    main()
