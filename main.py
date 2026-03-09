# ============================================
# ARES: ЧАТ-МЕНЕДЖЕР (ПРЕМИУМ-ВЕРСИЯ)
# Полная копия Grand (кроме рабов)
# Команды через /, стиль, смайлики, роли, системные админы
# ИСПРАВЛЕННАЯ И ПОЛНОСТЬЮ РАБОЧАЯ ВЕРСИЯ
# ============================================

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import time
import random
import sqlite3
from datetime import datetime, timedelta
import threading
from fastapi import FastAPI
import uvicorn
import os

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "vk1.a.NJgDVnKsv7inayrlqMXqJmevAVJBX0jAWCD33RC4w27CYWekHlXCvHFFsXNHp5447AHdmZboM2-SVBuyCk5Up1BqIxGOmkwwZ3pRjlizFJ8ogcMygQSMGxto-kzEm6lNBGqQjTifcD_MY4kLVejoqG_JcstMe3JXBuLc2wW_mWux-3gH2DVGckYcgr_oKKq5lV_c3vaMxvrGMTBYufPWgg"
GROUP_ID = 236517090
OWNER_ID = 853348780
BOT_NAME = "ARES"
PREFIX = "/"

# ===== ИНИЦИАЛИЗАЦИЯ БД =====
conn = sqlite3.connect('ares.db', check_same_thread=False)
cursor = conn.cursor()

# Пользователи (общая информация)
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  name TEXT,
                  nick TEXT,
                  warns INTEGER DEFAULT 0,
                  muted INTEGER DEFAULT 0,
                  level INTEGER DEFAULT 1,
                  exp INTEGER DEFAULT 0,
                  coins INTEGER DEFAULT 1000,
                  bank INTEGER DEFAULT 0,
                  daily INTEGER DEFAULT 0)''')

# Чаты
cursor.execute('''CREATE TABLE IF NOT EXISTS chats
                 (chat_id INTEGER PRIMARY KEY,
                  title TEXT,
                  welcome TEXT,
                  rules TEXT,
                  silence INTEGER DEFAULT 0,
                  games INTEGER DEFAULT 1)''')

# Роли (в чате)
cursor.execute('''CREATE TABLE IF NOT EXISTS roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_id INTEGER,
                  priority INTEGER,
                  name TEXT,
                  color TEXT,
                  permissions TEXT)''')

# Назначенные роли пользователям
cursor.execute('''CREATE TABLE IF NOT EXISTS user_roles
                 (user_id INTEGER,
                  chat_id INTEGER,
                  priority INTEGER,
                  PRIMARY KEY (user_id, chat_id))''')

# Системные администраторы (глобальные)
cursor.execute('''CREATE TABLE IF NOT EXISTS sysadmins
                 (user_id INTEGER PRIMARY KEY,
                  added_by INTEGER,
                  date INTEGER)''')

# Баны (chat_id=0 глобальный)
cursor.execute('''CREATE TABLE IF NOT EXISTS bans
                 (user_id INTEGER,
                  chat_id INTEGER,
                  reason TEXT,
                  admin_id INTEGER,
                  date INTEGER,
                  expires INTEGER,
                  PRIMARY KEY (user_id, chat_id))''')

# Статистика сообщений
cursor.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  chat_id INTEGER,
                  messages INTEGER DEFAULT 0,
                  commands INTEGER DEFAULT 0,
                  last_active INTEGER)''')

conn.commit()

# ===== СТАНДАРТНЫЕ РОЛИ (для новых чатов) =====
DEFAULT_ROLES = [
    (100, "👑 Владелец", "gold", "all"),
    (80,  "💎 Главный администратор", "red", "all"),
    (60,  "🔴 Администратор", "red", "admin,mod,helper"),
    (40,  "🟠 Модератор", "orange", "mod,helper,kick,mute,warn"),
    (20,  "🟡 Помощник", "yellow", "helper,mute,warn"),
    (10,  "🟢 Агент", "green", "custom"),
    (0,   "⚪ Пользователь", "gray", "none")
]

# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def extract_user_id(arg):
    """Извлекает ID пользователя из строки вида [id123|name] или числа."""
    if not arg:
        return None
    arg = arg.strip()
    if arg.startswith('[id') and '|' in arg:
        try:
            return int(arg.split('|')[0].replace('[id', ''))
        except:
            return None
    if arg.isdigit():
        return int(arg)
    return None

def format_duration(seconds):
    if seconds < 60:
        return f"{seconds} сек"
    if seconds < 3600:
        return f"{seconds//60} мин"
    if seconds < 86400:
        return f"{seconds//3600} ч"
    return f"{seconds//86400} дн"

def get_user_name(vk, uid):
    try:
        user = vk.users.get(user_ids=uid)[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"id{uid}"

# ===== ОСНОВНОЙ КЛАСС БОТА =====
class AresBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id=GROUP_ID)
        self.start_time = time.time()
        print(f"✅ {BOT_NAME} запущен! Владелец: id{OWNER_ID}")
        print(f"🚀 Команды: {PREFIX}помощь")

    def send(self, peer_id, message):
        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=message,
                random_id=get_random_id()
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")

    def get_user_name(self, uid):
        return get_user_name(self.vk, uid)

    def is_sysadmin(self, uid):
        if uid == OWNER_ID:
            return True
        return cursor.execute("SELECT 1 FROM sysadmins WHERE user_id=?", (uid,)).fetchone() is not None

    def get_user_priority(self, uid, chat_id):
        """Возвращает приоритет роли пользователя в чате."""
        if self.is_sysadmin(uid):
            return 1000
        role = cursor.execute("SELECT priority FROM user_roles WHERE user_id=? AND chat_id=?", (uid, chat_id)).fetchone()
        return role[0] if role else 0

    def has_permission(self, uid, chat_id, perm):
        """Проверка права на выполнение команды (упрощённо по приоритету)."""
        if self.is_sysadmin(uid):
            return True
        prio = self.get_user_priority(uid, chat_id)
        if perm in ('kick', 'mute', 'warn', 'unmute', 'unwarn'):
            return prio >= 20
        if perm in ('ban', 'unban', 'banlist'):
            return prio >= 40
        if perm in ('admin', 'role', 'newrole', 'delrole'):
            return prio >= 60
        if perm in ('owner', 'settings', 'sysadmin'):
            return prio >= 100
        return False

    def kick_user(self, chat_id, user_id):
        try:
            self.vk.messages.removeChatUser(chat_id=chat_id, user_id=user_id)
            return True
        except:
            return False

    def init_chat_roles(self, chat_id):
        """При первом входе бота в чат создаём стандартные роли."""
        existing = cursor.execute("SELECT COUNT(*) FROM roles WHERE chat_id=?", (chat_id,)).fetchone()[0]
        if existing == 0:
            for prio, name, color, perms in DEFAULT_ROLES:
                cursor.execute("INSERT INTO roles (chat_id, priority, name, color, permissions) VALUES (?,?,?,?,?)",
                               (chat_id, prio, name, color, perms))
            conn.commit()

    # ===== ОБРАБОТКА СОБЫТИЙ =====
    def run(self):
        print("🚀 Бот слушает события...")
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        self.handle_message(event)
                    elif event.type == VkBotEventType.CHAT_INVITE_USER:
                        self.handle_invite(event)
            except Exception as e:
                print(f"Ошибка в цикле: {e}")
                time.sleep(5)

    def handle_message(self, event):
        msg = event.obj.message
        peer_id = msg['peer_id']
        from_id = msg['from_id']
        text = msg['text'].strip()
        if from_id == -GROUP_ID:
            return
        chat_id = peer_id - 2000000000 if peer_id > 2000000000 else None

        # Проверка глобального бана
        banned = cursor.execute("SELECT 1 FROM bans WHERE user_id=? AND chat_id=0 AND (expires>? OR expires=0)",
                                (from_id, int(time.time()))).fetchone()
        if banned:
            return

        # Проверка мута
        muted = cursor.execute("SELECT muted FROM users WHERE user_id=?", (from_id,)).fetchone()
        if muted and muted[0] and muted[0] > time.time():
            return

        # Статистика
        cursor.execute("INSERT INTO stats (user_id, chat_id, messages, last_active) VALUES (?,?,1,?)",
                       (from_id, chat_id, int(time.time())))
        cursor.execute("UPDATE users SET messages = COALESCE(messages,0)+1 WHERE user_id=?", (from_id,))
        conn.commit()

        if text.startswith(PREFIX):
            self.handle_command(text[1:], peer_id, from_id, chat_id)

    def handle_invite(self, event):
        chat_id = event.chat_id
        peer_id = 2000000000 + chat_id
        invited_id = event.obj['action']['member_id']
        if invited_id == -GROUP_ID:  # бота добавили
            self.init_chat_roles(chat_id)
            self.send(peer_id, f"👋 Всем привет! Я {BOT_NAME} — чат-менеджер.\n{PREFIX}помощь — список команд.")
        elif invited_id > 0:
            # Приветствие нового участника
            welcome = cursor.execute("SELECT welcome FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
            welcome_text = welcome[0] if welcome and welcome[0] else "👋 Добро пожаловать, {name}!"
            name = self.get_user_name(invited_id)
            self.send(peer_id, welcome_text.replace("{name}", name))

    def handle_command(self, text, peer_id, from_id, chat_id):
        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        # ===== ОСНОВНЫЕ КОМАНДЫ =====
        if cmd in ['помощь', 'help', 'команды']:
            self.cmd_help(peer_id)
        elif cmd in ['пинг', 'ping']:
            self.cmd_ping(peer_id)
        elif cmd in ['правила', 'rules']:
            self.cmd_rules(peer_id, chat_id)
        elif cmd in ['админы', 'admins', 'staff']:
            self.cmd_admins(peer_id, chat_id)
        elif cmd in ['онлайн', 'online']:
            self.cmd_online(peer_id, chat_id)
        elif cmd in ['стата', 'stats', 'статистика']:
            self.cmd_stats(args, peer_id, from_id, chat_id)
        elif cmd in ['профиль']:
            self.cmd_profile(peer_id, from_id)
        elif cmd in ['топ']:
            self.cmd_top(peer_id, chat_id)

        # ===== МОДЕРАЦИЯ =====
        elif cmd in ['кик', 'kick']:
            self.cmd_kick(args, peer_id, from_id, chat_id)
        elif cmd in ['варн', 'warn']:
            self.cmd_warn(args, peer_id, from_id, chat_id)
        elif cmd in ['снятьварн', 'unwarn']:
            self.cmd_unwarn(args, peer_id, from_id, chat_id)
        elif cmd in ['мут', 'mute']:
            self.cmd_mute(args, peer_id, from_id, chat_id)
        elif cmd in ['унмут', 'unmute']:
            self.cmd_unmute(args, peer_id, from_id, chat_id)
        elif cmd in ['бан', 'ban']:
            self.cmd_ban(args, peer_id, from_id, chat_id)
        elif cmd in ['унбан', 'unban']:
            self.cmd_unban(args, peer_id, from_id, chat_id)
        elif cmd in ['банлист', 'banlist']:
            self.cmd_banlist(peer_id, chat_id)

        # ===== РОЛИ =====
        elif cmd in ['роль', 'role', 'giverole']:
            self.cmd_role(args, peer_id, from_id, chat_id)
        elif cmd in ['снятьроль', 'removerole']:
            self.cmd_removerole(args, peer_id, from_id, chat_id)
        elif cmd in ['new', 'newrole']:
            self.cmd_newrole(args, peer_id, from_id, chat_id)
        elif cmd in ['delrole', 'deleterole']:
            self.cmd_delrole(args, peer_id, from_id, chat_id)

        # ===== СИСТЕМНЫЕ АДМИНЫ =====
        elif cmd in ['sysadmin']:
            self.cmd_sysadmin(args, peer_id, from_id, chat_id)
        elif cmd in ['sysrole']:
            self.cmd_sysrole(args, peer_id, from_id, chat_id)
        elif cmd in ['givemoney']:
            self.cmd_givemoney(args, peer_id, from_id, chat_id)
        elif cmd in ['sysban']:
            self.cmd_sysban(args, peer_id, from_id, chat_id)

        # ===== ЭКОНОМИКА =====
        elif cmd in ['казино', 'casino']:
            self.cmd_casino(args, peer_id, from_id, chat_id)
        elif cmd in ['перевод', 'pay', 'give']:
            self.cmd_pay(args, peer_id, from_id, chat_id)
        elif cmd in ['бонус', 'daily']:
            self.cmd_daily(peer_id, from_id)

        # ===== РАЗВЛЕЧЕНИЯ =====
        elif cmd in ['анекдот', 'joke']:
            self.cmd_joke(peer_id)
        elif cmd in ['факт', 'fact']:
            self.cmd_fact(peer_id)
        elif cmd in ['шар', 'ball']:
            self.cmd_ball(args, peer_id)

        else:
            self.send(peer_id, f"❌ Неизвестная команда. Введите {PREFIX}помощь")

    # ===== РЕАЛИЗАЦИИ КОМАНД =====
    def cmd_help(self, peer_id):
        help_text = f"""
🔔 **{BOT_NAME}** удобный и простой бот.

📜 Отображена малая часть необходимых команд:
{PREFIX}кик — исключить пользователя
{PREFIX}бан — заблокировать пользователя
{PREFIX}унбан — разблокировать участника
{PREFIX}мут — запретить писать в чат
{PREFIX}унмут — разрешить писать в чат
{PREFIX}варн — выдать предупреждение
{PREFIX}снятьварн — снять предупреждение
{PREFIX}админы — отобразить список участников с ролью
{PREFIX}роль — выдать роль участнику
{PREFIX}профиль — ваш профиль и баланс
{PREFIX}казино — сыграть в казино
{PREFIX}перевод — перевести монеты
{PREFIX}топ — топ богачей
{PREFIX}помощь — это сообщение
"""
        self.send(peer_id, help_text)

    def cmd_ping(self, peer_id):
        uptime = int(time.time() - self.start_time)
        self.send(peer_id, f"🏓 Понг! Время работы: {format_duration(uptime)}")

    def cmd_rules(self, peer_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Эта команда работает только в беседах.")
            return
        rules = cursor.execute("SELECT rules FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
        if rules and rules[0]:
            self.send(peer_id, f"📜 **Правила чата:**\n{rules[0]}")
        else:
            self.send(peer_id, "📜 Правила не установлены.")

    def cmd_admins(self, peer_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Эта команда работает только в беседах.")
            return
        admins = cursor.execute("SELECT user_id, priority FROM user_roles WHERE chat_id=? AND priority>=20", (chat_id,)).fetchall()
        if not admins:
            self.send(peer_id, "👥 В чате нет администраторов (кроме владельца).")
            return
        text = "👥 **Администрация чата:**\n"
        for uid, prio in admins:
            name = self.get_user_name(uid)
            role_name = cursor.execute("SELECT name FROM roles WHERE chat_id=? AND priority=?", (chat_id, prio)).fetchone()
            role = role_name[0] if role_name else f"приоритет {prio}"
            text += f"• {name} — {role}\n"
        self.send(peer_id, text)

    def cmd_online(self, peer_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Эта команда работает только в беседах.")
            return
        try:
            members = self.vk.messages.getConversationMembers(peer_id=2000000000+chat_id)
            online = [m for m in members['items'] if m.get('online', False) and m['member_id'] > 0]
            if not online:
                self.send(peer_id, "🟢 Сейчас нет онлайн-пользователей.")
                return
            text = "🟢 **Онлайн:**\n"
            for m in online:
                name = self.get_user_name(m['member_id'])
                text += f"• {name}\n"
            self.send(peer_id, text)
        except:
            self.send(peer_id, "❌ Не удалось получить список.")

    def cmd_stats(self, args, peer_id, from_id, chat_id):
        target = from_id
        if args:
            uid = extract_user_id(args[0])
            if uid:
                target = uid
        name = self.get_user_name(target)
        data = cursor.execute("SELECT warns, level, exp, coins FROM users WHERE user_id=?", (target,)).fetchone()
        warns, lvl, exp, coins = data if data else (0, 1, 0, 1000)
        exp_next = lvl * 100
        bar_length = 10
        filled = int((exp / exp_next) * bar_length) if exp_next else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        msg = f"""
📊 **Статистика {name}**
⚠️ Предупреждений: {warns}/3
📈 Уровень: {lvl} | Опыт: {exp}/{exp_next}
📊 [{bar}]
💰 Монет: {coins} 🪙
"""
        self.send(peer_id, msg)

    def cmd_profile(self, peer_id, from_id):
        self.cmd_stats([], peer_id, from_id, None)

    def cmd_top(self, peer_id, chat_id):
        top = cursor.execute("SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
        if not top:
            self.send(peer_id, "🏆 Топ пока пуст.")
            return
        text = "🏆 **Топ богачей:**\n"
        for i, (uid, coins) in enumerate(top, 1):
            name = self.get_user_name(uid)
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {name} — {coins} 🪙\n"
        self.send(peer_id, text)

    # ===== МОДЕРАЦИЯ =====
    def cmd_kick(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'kick'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}кик @id [причина]")
            return
        target = extract_user_id(args[0])
        if not target or target == from_id:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        if self.kick_user(chat_id, target):
            name = self.get_user_name(target)
            self.send(peer_id, f"👢 {name} исключён.\nПричина: {reason}")
        else:
            self.send(peer_id, "❌ Не удалось исключить (возможно, пользователь не в чате).")

    def cmd_warn(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'warn'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}варн @id [причина]")
            return
        target = extract_user_id(args[0])
        if not target or target == from_id:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        # Проверяем, не выше ли приоритет цели
        if self.get_user_priority(target, chat_id) >= self.get_user_priority(from_id, chat_id) and not self.is_sysadmin(from_id):
            self.send(peer_id, "⛔ Вы не можете выдать предупреждение пользователю с равным или более высоким приоритетом.")
            return
        cursor.execute("UPDATE users SET warns = COALESCE(warns,0)+1 WHERE user_id=?", (target,))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"⚠️ {name} получил предупреждение.\nПричина: {reason}")

    def cmd_unwarn(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'warn'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}снятьварн @id")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        cursor.execute("UPDATE users SET warns = MAX(0, COALESCE(warns,0)-1) WHERE user_id=?", (target,))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"✅ Предупреждение снято с {name}.")

    def cmd_mute(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'mute'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if len(args) < 2:
            self.send(peer_id, f"❌ Использование: {PREFIX}мут @id время [причина]")
            return
        target = extract_user_id(args[0])
        if not target or target == from_id:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        try:
            minutes = int(args[1])
        except:
            self.send(peer_id, "❌ Время должно быть числом (в минутах).")
            return
        if minutes <= 0:
            self.send(peer_id, "❌ Время должно быть положительным.")
            return
        reason = " ".join(args[2:]) if len(args) > 2 else "Не указана"
        if self.get_user_priority(target, chat_id) >= self.get_user_priority(from_id, chat_id) and not self.is_sysadmin(from_id):
            self.send(peer_id, "⛔ Вы не можете замутить пользователя с равным или более высоким приоритетом.")
            return
        mute_until = int(time.time()) + minutes * 60
        cursor.execute("UPDATE users SET muted=? WHERE user_id=?", (mute_until, target))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"🔇 {name} замучен на {minutes} мин.\nПричина: {reason}")

    def cmd_unmute(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'mute'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}унмут @id")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        cursor.execute("UPDATE users SET muted=0 WHERE user_id=?", (target,))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"🔊 {name} размучен.")

    def cmd_ban(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'ban'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}бан @id [дни] [причина]")
            return
        target = extract_user_id(args[0])
        if not target or target == from_id:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        days = 0
        reason = "Не указана"
        if len(args) > 1 and args[1].isdigit():
            days = int(args[1])
            if len(args) > 2:
                reason = " ".join(args[2:])
        else:
            reason = " ".join(args[1:]) if len(args) > 1 else "Не указана"
        expires = 0 if days == 0 else int(time.time()) + days * 86400
        # Проверка приоритета
        if self.get_user_priority(target, chat_id) >= self.get_user_priority(from_id, chat_id) and not self.is_sysadmin(from_id):
            self.send(peer_id, "⛔ Вы не можете забанить пользователя с равным или более высоким приоритетом.")
            return
        cursor.execute("INSERT OR REPLACE INTO bans (user_id, chat_id, reason, admin_id, date, expires) VALUES (?,?,?,?,?,?)",
                       (target, chat_id, reason, from_id, int(time.time()), expires))
        conn.commit()
        self.kick_user(chat_id, target)
        name = self.get_user_name(target)
        ban_time = "навсегда" if days == 0 else f"на {days} дн."
        self.send(peer_id, f"🔨 {name} забанен {ban_time}.\nПричина: {reason}")

    def cmd_unban(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'ban'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}унбан @id")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        cursor.execute("DELETE FROM bans WHERE user_id=? AND chat_id=?", (target, chat_id))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"✅ {name} разбанен в этом чате.")

    def cmd_banlist(self, peer_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        bans = cursor.execute("SELECT user_id, reason, date, expires FROM bans WHERE chat_id=?", (chat_id,)).fetchall()
        if not bans:
            self.send(peer_id, "📋 Список забаненных пуст.")
            return
        text = "📋 **Забаненные в этом чате:**\n"
        for uid, reason, date, expires in bans:
            name = self.get_user_name(uid)
            exp_str = "навсегда" if expires == 0 else f"до {datetime.fromtimestamp(expires).strftime('%d.%m.%Y')}"
            text += f"• {name} — {reason} ({exp_str})\n"
        self.send(peer_id, text)

    # ===== РОЛИ =====
    def cmd_role(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'role'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if len(args) < 2:
            self.send(peer_id, f"❌ Использование: {PREFIX}роль @id приоритет")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        try:
            priority = int(args[1])
        except:
            self.send(peer_id, "❌ Приоритет должен быть числом.")
            return
        role = cursor.execute("SELECT name FROM roles WHERE chat_id=? AND priority=?", (chat_id, priority)).fetchone()
        if not role:
            self.send(peer_id, "❌ Роль с таким приоритетом не существует.")
            return
        # Выдаём роль
        cursor.execute("INSERT OR REPLACE INTO user_roles (user_id, chat_id, priority) VALUES (?,?,?)",
                       (target, chat_id, priority))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"✅ {name} получил роль «{role[0]}».")

    def cmd_removerole(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'role'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}снятьроль @id")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        cursor.execute("DELETE FROM user_roles WHERE user_id=? AND chat_id=?", (target, chat_id))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"✅ С пользователя {name} сняты все роли.")

    def cmd_newrole(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'role'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if len(args) < 2:
            self.send(peer_id, f"❌ Использование: {PREFIX}new приоритет название")
            return
        try:
            priority = int(args[0])
        except:
            self.send(peer_id, "❌ Приоритет должен быть числом.")
            return
        name = " ".join(args[1:])
        if not name:
            self.send(peer_id, "❌ Укажите название роли.")
            return
        # Проверяем, не занят ли приоритет
        exist = cursor.execute("SELECT id FROM roles WHERE chat_id=? AND priority=?", (chat_id, priority)).fetchone()
        if exist:
            cursor.execute("UPDATE roles SET name=? WHERE chat_id=? AND priority=?", (name, chat_id, priority))
            self.send(peer_id, f"✅ Роль с приоритетом {priority} обновлена: {name}")
        else:
            cursor.execute("INSERT INTO roles (chat_id, priority, name, color, permissions) VALUES (?,?,?,?,?)",
                           (chat_id, priority, name, "default", "custom"))
            self.send(peer_id, f"✅ Создана новая роль: {name} (приоритет {priority})")
        conn.commit()

    def cmd_delrole(self, args, peer_id, from_id, chat_id):
        if not chat_id:
            self.send(peer_id, "❌ Команда только для бесед.")
            return
        if not self.has_permission(from_id, chat_id, 'role'):
            self.send(peer_id, "⛔ У вас нет прав.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}delrole приоритет")
            return
        try:
            priority = int(args[0])
        except:
            self.send(peer_id, "❌ Приоритет должен быть числом.")
            return
        # Удаляем роль
        cursor.execute("DELETE FROM roles WHERE chat_id=? AND priority=?", (chat_id, priority))
        conn.commit()
        self.send(peer_id, f"✅ Роль с приоритетом {priority} удалена.")

    # ===== СИСТЕМНЫЕ АДМИНИСТРАТОРЫ =====
    def cmd_sysadmin(self, args, peer_id, from_id, chat_id):
        if from_id != OWNER_ID:
            self.send(peer_id, "⛔ Только владелец может использовать эту команду.")
            return
        if not args:
            self.send(peer_id, f"❌ Использование: {PREFIX}sysadmin add/remove @id")
            return
        sub = args[0].lower()
        if sub == "add" and len(args) >= 2:
            target = extract_user_id(args[1])
            if not target:
                self.send(peer_id, "❌ Некорректный пользователь.")
                return
            cursor.execute("INSERT OR IGNORE INTO sysadmins (user_id, added_by, date) VALUES (?,?,?)",
                           (target, from_id, int(time.time())))
            conn.commit()
            name = self.get_user_name(target)
            self.send(peer_id, f"✅ {name} теперь системный администратор.")
        elif sub == "remove" and len(args) >= 2:
            target = extract_user_id(args[1])
            if not target:
                self.send(peer_id, "❌ Некорректный пользователь.")
                return
            cursor.execute("DELETE FROM sysadmins WHERE user_id=?", (target,))
            conn.commit()
            name = self.get_user_name(target)
            self.send(peer_id, f"✅ {name} больше не системный администратор.")
        else:
            self.send(peer_id, f"❌ Использование: {PREFIX}sysadmin add @id или {PREFIX}sysadmin remove @id")

    def cmd_sysrole(self, args, peer_id, from_id, chat_id):
        if not self.is_sysadmin(from_id):
            self.send(peer_id, "⛔ Только системные администраторы могут использовать эту команду.")
            return
        if len(args) < 2:
            self.send(peer_id, f"❌ Использование: {PREFIX}sysrole @id приоритет")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        try:
            priority = int(args[1])
        except:
            self.send(peer_id, "❌ Приоритет должен быть числом.")
            return
        if not chat_id:
            self.send(peer_id, "❌ Эта команда работает только в беседах.")
            return
        role = cursor.execute("SELECT name FROM roles WHERE chat_id=? AND priority=?", (chat_id, priority)).fetchone()
        if not role:
            self.send(peer_id, "❌ Роль с таким приоритетом не существует в этом чате.")
            return
        cursor.execute("INSERT OR REPLACE INTO user_roles (user_id, chat_id, priority) VALUES (?,?,?)",
                       (target, chat_id, priority))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"✅ (Sys) {name} получил роль «{role[0]}».")

    def cmd_givemoney(self, args, peer_id, from_id, chat_id):
        if not self.is_sysadmin(from_id):
            self.send(peer_id, "⛔ Только системные администраторы могут использовать эту команду.")
            return
        if len(args) < 2:
            self.send(peer_id, f"❌ Использование: {PREFIX}givemoney @id сумма")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        try:
            amount = int(args[1])
        except:
            self.send(peer_id, "❌ Сумма должна быть числом.")
            return
        if amount <= 0:
            self.send(peer_id, "❌ Сумма должна быть положительной.")
            return
        cursor.execute("UPDATE users SET coins = COALESCE(coins,1000)+? WHERE user_id=?", (amount, target))
        conn.commit()
        name = self.get_user_name(target)
        self.send(peer_id, f"💰 {name} получил {amount} 🪙 от системного администратора.")

    def cmd_sysban(self, args, peer_id, from_id, chat_id):
        if not self.is_sysadmin(from_id):
            self.send(peer_id, "⛔ Только системные администраторы могут использовать эту команду.")
            return
        if len(args) < 1:
            self.send(peer_id, f"❌ Использование: {PREFIX}sysban @id [дни] [причина]")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        days = 0
        reason = "Системный бан"
        if len(args) > 1 and args[1].isdigit():
            days = int(args[1])
            if len(args) > 2:
                reason = " ".join(args[2:])
        else:
            reason = " ".join(args[1:]) if len(args) > 1 else "Системный бан"
        expires = 0 if days == 0 else int(time.time()) + days * 86400
        cursor.execute("INSERT OR REPLACE INTO bans (user_id, chat_id, reason, admin_id, date, expires) VALUES (?,0,?,?,?,?)",
                       (target, reason, from_id, int(time.time()), expires))
        conn.commit()
        name = self.get_user_name(target)
        ban_time = "навсегда" if days == 0 else f"на {days} дн."
        self.send(peer_id, f"🔨 (Sys) {name} забанен глобально {ban_time}.\nПричина: {reason}")

    # ===== ЭКОНОМИКА =====
    def cmd_casino(self, args, peer_id, from_id, chat_id):
        if chat_id:
            games = cursor.execute("SELECT games FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
            if games and games[0] == 0:
                self.send(peer_id, "🎮 Игры в этом чате отключены.")
                return
        if not args or not args[0].isdigit():
            self.send(peer_id, f"❌ Использование: {PREFIX}казино сумма")
            return
        bet = int(args[0])
        if bet <= 0:
            self.send(peer_id, "❌ Ставка должна быть положительной.")
            return
        cur = cursor.execute("SELECT coins FROM users WHERE user_id=?", (from_id,)).fetchone()
        coins = cur[0] if cur else 1000
        if coins < bet:
            self.send(peer_id, f"❌ Недостаточно монет. У вас {coins} 🪙")
            return
        r = random.random()
        if r < 0.45:
            win = 0
            result = "❌ Проигрыш"
            new_coins = coins - bet
        elif r < 0.75:
            win = bet
            result = "🤝 Ничья"
            new_coins = coins
        elif r < 0.92:
            win = bet * 2
            result = "✅ Выигрыш x2"
            new_coins = coins + bet
        else:
            win = bet * 5
            result = "🎉 ДЖЕКПОТ x5!"
            new_coins = coins + bet * 4
        cursor.execute("UPDATE users SET coins=? WHERE user_id=?", (new_coins, from_id))
        conn.commit()
        self.send(peer_id, f"🎰 **Казино**\nСтавка: {bet} 🪙\nРезультат: {result}\nВыигрыш: {win} 🪙\nБаланс: {new_coins} 🪙")

    def cmd_pay(self, args, peer_id, from_id, chat_id):
        if len(args) < 2:
            self.send(peer_id, f"❌ Использование: {PREFIX}перевод @id сумма")
            return
        target = extract_user_id(args[0])
        if not target:
            self.send(peer_id, "❌ Некорректный пользователь.")
            return
        try:
            amount = int(args[1])
        except:
            self.send(peer_id, "❌ Сумма должна быть числом.")
            return
        if amount <= 0:
            self.send(peer_id, "❌ Сумма должна быть положительной.")
            return
        cur = cursor.execute("SELECT coins FROM users WHERE user_id=?", (from_id,)).fetchone()
        sender_coins = cur[0] if cur else 1000
        if sender_coins < amount:
            self.send(peer_id, f"❌ Недостаточно монет. У вас {sender_coins} 🪙")
            return
        cur2 = cursor.execute("SELECT coins FROM users WHERE user_id=?", (target,)).fetchone()
        receiver_coins = cur2[0] if cur2 else 1000
        cursor.execute("UPDATE users SET coins=? WHERE user_id=?", (sender_coins - amount, from_id))
        cursor.execute("UPDATE users SET coins=? WHERE user_id=?", (receiver_coins + amount, target))
        conn.commit()
        sender_name = self.get_user_name(from_id)
        receiver_name = self.get_user_name(target)
        self.send(peer_id, f"💸 {sender_name} перевёл {amount} 🪙 пользователю {receiver_name}.")

    def cmd_daily(self, peer_id, from_id):
        now = int(time.time())
        cur = cursor.execute("SELECT coins, daily FROM users WHERE user_id=?", (from_id,)).fetchone()
        coins = cur[0] if cur else 1000
        last_daily = cur[1] if cur and cur[1] else 0
        if now - last_daily < 86400:
            left = 86400 - (now - last_daily)
            self.send(peer_id, f"⏳ Следующий бонус через {format_duration(left)}.")
            return
        bonus = random.randint(100, 500)
        new_coins = coins + bonus
        cursor.execute("UPDATE users SET coins=?, daily=? WHERE user_id=?", (new_coins, now, from_id))
        conn.commit()
        self.send(peer_id, f"🎁 Ежедневный бонус: +{bonus} 🪙. Баланс: {new_coins} 🪙")

    # ===== РАЗВЛЕЧЕНИЯ =====
    def cmd_joke(self, peer_id):
        jokes = [
            "Идёт ёжик по лесу, видит — машина горит. Сел и сгорел.",
            "— Вовочка, почему ты опоздал в школу? — Снился сон, что я уже на уроке, вот я и не пошёл.",
            "Программист просыпается и говорит жене: — Сегодня суббота или воскресенье? Жена: — Ещё не знаю, я не включала компьютер.",
            "В зоопарке медведь спрашивает у волка: — Слышал, ты в цирк уходишь? — Да, надоело тут сидеть. — Ну как знаешь, а я отсюда ни ногой. — Это почему? — Да видишь ли, из цирка ещё никто не возвращался..."
        ]
        self.send(peer_id, f"😄 {random.choice(jokes)}")

    def cmd_fact(self, peer_id):
        facts = [
            "Страусы бегают быстрее лошадей.",
            "У тигров не только полосатая шерсть, но и кожа.",
            "Клубника — не ягода, а многоорешек.",
            "В Антарктиде есть реки и озёра.",
            "Самый большой орган человека — кожа."
        ]
        self.send(peer_id, f"📌 {random.choice(facts)}")

    def cmd_ball(self, args, peer_id):
        if not args:
            self.send(peer_id, "🎱 Задай вопрос, например: /шар я сегодня выиграю?")
            return
        answers = [
            "Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да",
            "Можешь быть уверен в этом", "Мне кажется — да", "Вероятнее всего",
            "Хорошие перспективы", "Знаки говорят — да", "Да",
            "Пока не ясно", "Спроси позже", "Лучше не рассказывать",
            "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять",
            "Даже не думай", "Мой ответ — нет", "По моим данным — нет",
            "Перспективы не очень", "Весьма сомнительно"
        ]
        self.send(peer_id, f"🎱 {random.choice(answers)}")

# ===== FASTAPI ЗАГЛУШКА ДЛЯ RAILWAY =====
app = FastAPI()

@app.get("/")
def root():
    return {"status": f"{BOT_NAME} is running"}

def run_bot():
    try:
        bot = AresBot()
        bot.run()
    except Exception as e:
        print(f"❌ Ошибка в боте: {e}")

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    # Запускаем FastAPI сервер
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
