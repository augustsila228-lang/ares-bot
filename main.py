# ============================================
# ARES: ЧАТ-МЕНЕДЖЕР (ПОЛНАЯ ВЕРСИЯ)
# С системой ролей, агентами и экономикой
# ============================================

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
import time
import random
import json
import sqlite3
from datetime import datetime, timedelta

# ===== ТВОИ ДАННЫЕ =====
TOKEN = "vk1.a.NJgDVnKsv7inayrlqMXqJmevAVJBX0jAWCD33RC4w27CYWekHlXCvHFFsXNHp5447AHdmZboM2-SVBuyCk5Up1BqIxGOmkwwZ3pRjlizFJ8ogcMygQSMGxto-kzEm6lNBGqQjTifcD_MY4kLVejoqG_JcstMe3JXBuLc2wW_mWux-3gH2DVGckYcgr_oKKq5lV_c3vaMxvrGMTBYufPWgg"
GROUP_ID = 236517090
OWNER_ID = 853348780
BOT_NAME = "ARES"

# ===== ИНИЦИАЛИЗАЦИЯ БД =====
conn = sqlite3.connect('ares.db', check_same_thread=False)
cursor = conn.cursor()

# Таблица пользователей
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

# Таблица ролей (как в Grand)
cursor.execute('''CREATE TABLE IF NOT EXISTS roles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_id INTEGER,
                  priority INTEGER,
                  name TEXT,
                  color TEXT,
                  permissions TEXT)''')

# Стандартные роли Grand
DEFAULT_ROLES = [
    (100, "👑 Владелец", "FFD700", "all"),
    (80, "💎 Главный администратор", "FF4500", "admin,mod,helper"),
    (60, "🔴 Администратор", "FF0000", "mod,helper"),
    (40, "🟠 Модератор", "FFA500", "helper,kick,mute,warn"),
    (20, "🟡 Помощник", "FFFF00", "mute,warn"),
    (10, "🟢 Агент", "00FF00", "custom"),
    (0, "⚪ Пользователь", "808080", "none")
]

# Таблица прав агентов
cursor.execute('''CREATE TABLE IF NOT EXISTS agents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  chat_id INTEGER,
                  user_id INTEGER,
                  permissions TEXT,
                  added_by INTEGER,
                  date INTEGER)''')

# Таблица статистики
cursor.execute('''CREATE TABLE IF NOT EXISTS stats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  chat_id INTEGER,
                  messages INTEGER DEFAULT 0,
                  commands INTEGER DEFAULT 0,
                  last_active INTEGER)''')

# Таблица банов
cursor.execute('''CREATE TABLE IF NOT EXISTS bans
                 (user_id INTEGER PRIMARY KEY,
                  chat_id INTEGER,
                  reason TEXT,
                  admin_id INTEGER,
                  date INTEGER,
                  expires INTEGER)''')

conn.commit()

# ===== ОСНОВНОЙ КЛАСС =====
class AresBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id=GROUP_ID)
        print(f"✅ {BOT_NAME} запущен!")
        print(f"👑 Владелец: id{OWNER_ID}")
        
    def send(self, peer_id, message):
        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=message,
                random_id=get_random_id()
            )
        except:
            pass
    
    def get_user(self, user_id):
        try:
            user = self.vk.users.get(user_ids=user_id)[0]
            return f"{user['first_name']} {user['last_name']}"
        except:
            return f"id{user_id}"
    
    def get_role_priority(self, user_id, chat_id):
        """Получить приоритет роли пользователя"""
        if user_id == OWNER_ID:
            return 100
            
        role = cursor.execute(
            "SELECT priority FROM roles WHERE chat_id = ? AND priority IN "
            "(SELECT priority FROM users WHERE user_id = ? AND chat_id = ?)",
            (chat_id, user_id, chat_id)
        ).fetchone()
        
        return role[0] if role else 0
    
    def has_permission(self, user_id, chat_id, required_perm):
        """Проверка прав"""
        if user_id == OWNER_ID:
            return True
            
        # Проверка роли
        role = cursor.execute(
            "SELECT permissions FROM roles WHERE chat_id = ? AND priority = "
            "(SELECT priority FROM users WHERE user_id = ? AND chat_id = ?)",
            (chat_id, user_id, chat_id)
        ).fetchone()
        
        if role and (role[0] == "all" or required_perm in role[0]):
            return True
            
        # Проверка прав агента
        agent = cursor.execute(
            "SELECT permissions FROM agents WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        
        if agent and required_perm in agent[0]:
            return True
            
        return False
    
    def run(self):
        print("🚀 Бот ожидает сообщения...")
        
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkBotEventType.MESSAGE_NEW:
                        self.handle_message(event)
            except Exception as e:
                print(f"Ошибка: {e}")
                time.sleep(5)
    
    def handle_message(self, event):
        msg = event.obj.message
        peer_id = msg['peer_id']
        from_id = msg['from_id']
        text = msg['text'].strip()
        
        if from_id == -GROUP_ID:
            return
            
        # Определяем чат
        chat_id = peer_id - 2000000000 if peer_id > 2000000000 else None
        
        # Обновляем статистику
        cursor.execute('''INSERT INTO stats (user_id, chat_id, messages, last_active) 
                         VALUES (?, ?, 1, ?) 
                         ON CONFLICT(id) DO UPDATE SET 
                         messages = messages + 1, last_active = ?''',
                      (from_id, chat_id, int(time.time()), int(time.time())))
        conn.commit()
        
        # Проверка на мута
        muted = cursor.execute("SELECT muted FROM users WHERE user_id = ?", (from_id,)).fetchone()
        if muted and muted[0] > time.time():
            return
            
        # Обработка команд
        if text.startswith('!'):
            self.handle_command(text[1:], peer_id, from_id, chat_id)
    
    def handle_command(self, text, peer_id, from_id, chat_id):
        args = text.split()
        cmd = args[0].lower()
        params = args[1:] if len(args) > 1 else []
        
        # ===== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ =====
        if cmd in ["пинг", "ping"]:
            self.send(peer_id, "🏓 Понг!")
            
        elif cmd in ["помощь", "help", "команды"]:
            help_text = f"""
╔════════════════════╗
║   🤖 {BOT_NAME}    ║
╚════════════════════╝

🔹 **ОСНОВНЫЕ:**
!пинг - проверка
!стата [@id] - статистика
!профиль - профиль
!топ - топ по монетам
!казино [сумма] - сыграть
!перевод [@id] [сумма] - перевести

🔹 **РОЛИ (как в Grand):**
👑 Владелец (100)
💎 Главный админ (80)
🔴 Администратор (60)
🟠 Модератор (40)
🟡 Помощник (20)
🟢 Агент (10)
⚪ Пользователь (0)

🔹 **АГЕНТЫ:**
!agent add [@id] [права] - добавить агента
!agent remove [@id] - удалить агента
!agent list - список агентов

🔹 **МОДЕРАЦИЯ:**
!кик [@id] (причина)
!варн [@id] (причина)
!снятьварн [@id]
!мут [@id] [мин]
!унмут [@id]
!бан [@id] (дни)
!унбан [@id]

🔹 **РОЛИ:**
!роль [@id] [приоритет] - выдать роль
!снятьроль [@id] - снять роль
!new [приоритет] [название] - создать роль
!sysrole - системные роли

🔹 **АДМИН:**
!givemoney [@id] [сумма]
!sysban [@id] (причина)
!clear [N] - очистить чат
            """
            self.send(peer_id, help_text)
            
        # ===== СТАТИСТИКА =====
        elif cmd in ["стата", "stats"]:
            target = from_id
            if params and params[0].startswith('[id'):
                target = int(params[0].split('|')[0].replace('[id', ''))
            
            name = self.get_user(target)
            stats = cursor.execute(
                "SELECT messages, warns, level, exp, coins FROM users WHERE user_id = ?",
                (target,)
            ).fetchone()
            
            if stats:
                msgs, warns, lvl, exp, coins = stats
            else:
                msgs, warns, lvl, exp, coins = 0, 0, 1, 0, 1000
            
            text = f"""
📊 **СТАТИСТИКА {name}**
┌────────────────
│ Сообщений: {msgs}
│ Предупреждений: {warns}/3
│ Уровень: {lvl}
│ Опыт: {exp}
│ Монет: {coins} 🪙
└────────────────
            """
            self.send(peer_id, text)
            
        # ===== СИСТЕМА АГЕНТОВ (как в Grand) =====
        elif cmd == "agent" and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "admin") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            subcmd = params[0].lower()
            
            if subcmd == "add" and len(params) >= 3:
                target = int(params[1].split('|')[0].replace('[id', '')) if params[1].startswith('[id') else int(params[1])
                perms = params[2]  # права через запятую: kick,mute,warn
                
                cursor.execute(
                    "INSERT INTO agents (chat_id, user_id, permissions, added_by, date) VALUES (?, ?, ?, ?, ?)",
                    (chat_id, target, perms, from_id, int(time.time()))
                )
                conn.commit()
                
                name = self.get_user(target)
                self.send(peer_id, f"✅ Агент {name} добавлен с правами: {perms}")
                
            elif subcmd == "remove" and len(params) >= 2:
                target = int(params[1].split('|')[0].replace('[id', '')) if params[1].startswith('[id') else int(params[1])
                
                cursor.execute("DELETE FROM agents WHERE chat_id = ? AND user_id = ?", (chat_id, target))
                conn.commit()
                
                name = self.get_user(target)
                self.send(peer_id, f"✅ Агент {name} удален")
                
            elif subcmd == "list":
                agents = cursor.execute(
                    "SELECT user_id, permissions, date FROM agents WHERE chat_id = ?",
                    (chat_id,)
                ).fetchall()
                
                if agents:
                    text = "📋 **АГЕНТЫ ЧАТА:**\n\n"
                    for uid, perms, date in agents:
                        name = self.get_user(uid)
                        text += f"• {name} - права: {perms}\n"
                    self.send(peer_id, text)
                else:
                    self.send(peer_id, "В чате нет агентов")
        
        # ===== КОМАНДЫ МОДЕРАЦИИ =====
        elif cmd in ["кик", "kick"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "kick") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            reason = ' '.join(params[1:]) if len(params) > 1 else "Не указана"
            
            try:
                self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target)
                name = self.get_user(target)
                self.send(peer_id, f"👢 {name} исключен\nПричина: {reason}")
            except:
                self.send(peer_id, "❌ Не удалось исключить")
        
        elif cmd in ["варн", "warn"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "warn") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            reason = ' '.join(params[1:]) if len(params) > 1 else "Не указана"
            
            warns = cursor.execute("SELECT warns FROM users WHERE user_id = ?", (target,)).fetchone()
            current = warns[0] if warns else 0
            new_warns = current + 1
            
            cursor.execute("INSERT INTO users (user_id, warns) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET warns = ?",
                          (target, new_warns, new_warns))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"⚠️ {name} получил предупреждение ({new_warns}/3)\nПричина: {reason}")
            
            if new_warns >= 3:
                mute_time = int(time.time()) + 3600
                cursor.execute("UPDATE users SET muted = ? WHERE user_id = ?", (mute_time, target))
                conn.commit()
                self.send(peer_id, f"🔇 {name} замучен на 1 час (3/3 предупреждений)")
        
        elif cmd in ["снятьварн", "unwarn"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "warn") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            
            cursor.execute("UPDATE users SET warns = warns - 1 WHERE user_id = ? AND warns > 0", (target,))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"✅ Предупреждение снято с {name}")
        
        elif cmd in ["мут", "mute"] and len(params) >= 2:
            if not self.has_permission(from_id, chat_id, "mute") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            minutes = int(params[1])
            reason = ' '.join(params[2:]) if len(params) > 2 else "Не указана"
            
            mute_time = int(time.time()) + (minutes * 60)
            cursor.execute("UPDATE users SET muted = ? WHERE user_id = ?", (mute_time, target))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"🔇 {name} замучен на {minutes} мин\nПричина: {reason}")
        
        elif cmd in ["унмут", "unmute"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "mute") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            
            cursor.execute("UPDATE users SET muted = 0 WHERE user_id = ?", (target,))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"🔊 {name} размучен")
        
        elif cmd in ["бан", "ban"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "ban") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            days = int(params[1]) if len(params) > 1 and params[1].isdigit() else 0
            reason = ' '.join(params[2:]) if len(params) > 2 else "Нарушение правил"
            
            expires = 0 if days == 0 else int(time.time()) + (days * 86400)
            
            cursor.execute(
                "INSERT INTO bans (user_id, chat_id, reason, admin_id, date, expires) VALUES (?, ?, ?, ?, ?, ?)",
                (target, chat_id, reason, from_id, int(time.time()), expires)
            )
            conn.commit()
            
            try:
                self.vk.messages.removeChatUser(chat_id=chat_id, user_id=target)
            except:
                pass
                
            name = self.get_user(target)
            ban_time = "навсегда" if days == 0 else f"на {days} дн."
            self.send(peer_id, f"🔨 {name} забанен {ban_time}\nПричина: {reason}")
        
        elif cmd in ["унбан", "unban"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "ban") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            
            cursor.execute("DELETE FROM bans WHERE user_id = ? AND chat_id = ?", (target, chat_id))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"✅ {name} разбанен")
        
        # ===== СИСТЕМА РОЛЕЙ (как в Grand) =====
        elif cmd in ["роль", "role", "giverole"] and len(params) >= 2:
            if not self.has_permission(from_id, chat_id, "admin") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            priority = int(params[1])
            
            # Проверка существования роли
            role = cursor.execute(
                "SELECT name FROM roles WHERE chat_id = ? AND priority = ?",
                (chat_id, priority)
            ).fetchone()
            
            if not role:
                self.send(peer_id, "❌ Роль с таким приоритетом не существует")
                return
                
            cursor.execute('''INSERT INTO users (user_id, name) VALUES (?, ?) 
                            ON CONFLICT(user_id) DO UPDATE SET priority = ?''',
                          (target, self.get_user(target), priority))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"✅ {name} получил роль: {role[0]}")
        
        elif cmd in ["снятьроль", "removerole"] and len(params) >= 1:
            if not self.has_permission(from_id, chat_id, "admin") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            
            cursor.execute("UPDATE users SET priority = 0 WHERE user_id = ?", (target,))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"✅ Сняты роли с {name}")
        
        elif cmd in ["new", "newrole"] and len(params) >= 2:
            if not self.has_permission(from_id, chat_id, "admin") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            priority = int(params[0])
            name = ' '.join(params[1:])
            
            # Проверка, не занят ли приоритет
            exists = cursor.execute(
                "SELECT id FROM roles WHERE chat_id = ? AND priority = ?",
                (chat_id, priority)
            ).fetchone()
            
            if exists:
                cursor.execute(
                    "UPDATE roles SET name = ? WHERE chat_id = ? AND priority = ?",
                    (name, chat_id, priority)
                )
                self.send(peer_id, f"✅ Роль обновлена: {name} (приоритет {priority})")
            else:
                cursor.execute(
                    "INSERT INTO roles (chat_id, priority, name, color, permissions) VALUES (?, ?, ?, ?, ?)",
                    (chat_id, priority, name, "808080", "custom")
                )
                self.send(peer_id, f"✅ Создана новая роль: {name} (приоритет {priority})")
            
            conn.commit()
        
        elif cmd == "sysrole":
            if from_id != OWNER_ID:
                self.send(peer_id, "⛔ Только для владельца!")
                return
                
            text = "📋 **СИСТЕМНЫЕ РОЛИ GRAND:**\n\n"
            for priority, name, color, perms in DEFAULT_ROLES:
                text += f"{name} - приоритет {priority}\n"
            
            self.send(peer_id, text)
        
        # ===== ЭКОНОМИКА =====
        elif cmd == "профиль":
            data = cursor.execute(
                "SELECT coins, bank, level, exp FROM users WHERE user_id = ?",
                (from_id,)
            ).fetchone()
            
            if not data:
                data = (1000, 0, 1, 0)
                cursor.execute("INSERT INTO users (user_id, name, coins) VALUES (?, ?, ?)",
                              (from_id, self.get_user(from_id), 1000))
                conn.commit()
            
            coins, bank, level, exp = data
            
            self.send(peer_id, f"""
👤 **ПРОФИЛЬ**
┌────────────────
│ Монет: {coins} 🪙
│ Банк: {bank} 🪙
│ Уровень: {level}
│ Опыт: {exp}
└────────────────
            """)
        
        elif cmd == "казино" and len(params) >= 1 and params[0].isdigit():
            bet = int(params[0])
            
            balance = cursor.execute("SELECT coins FROM users WHERE user_id = ?", (from_id,)).fetchone()
            coins = balance[0] if balance else 1000
            
            if bet > coins:
                self.send(peer_id, "❌ Недостаточно монет!")
                return
                
            if bet < 1:
                self.send(peer_id, "❌ Ставка должна быть больше 0")
                return
            
            # Игра
            chance = random.randint(1, 100)
            
            if chance <= 45:
                win = 0
                result = "❌ Проигрыш"
                new_coins = coins - bet
            elif chance <= 75:
                win = bet
                result = "🤝 Ничья"
                new_coins = coins
            elif chance <= 92:
                win = bet * 2
                result = "✅ Выигрыш x2"
                new_coins = coins + bet
            else:
                win = bet * 5
                result = "🎉 ДЖЕКПОТ x5!"
                new_coins = coins + (bet * 4)
            
            cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_coins, from_id))
            conn.commit()
            
            self.send(peer_id, f"""
🎰 **КАЗИНО**
┌──────────────┐
│ Ставка: {bet} 🪙
│ Результат: {result}
│ Выигрыш: {win} 🪙
│ Баланс: {new_coins} 🪙
└──────────────┘
            """)
        
        elif cmd in ["перевод", "pay", "give"] and len(params) >= 2:
            target = int(params[0].split('|')[0].replace('[id', ''))
            amount = int(params[1])
            
            if amount <= 0:
                self.send(peer_id, "❌ Сумма должна быть больше 0")
                return
                
            sender_balance = cursor.execute("SELECT coins FROM users WHERE user_id = ?", (from_id,)).fetchone()
            sender_coins = sender_balance[0] if sender_balance else 1000
            
            if sender_coins < amount:
                self.send(peer_id, f"❌ Недостаточно монет! У вас {sender_coins} 🪙")
                return
            
            receiver_balance = cursor.execute("SELECT coins FROM users WHERE user_id = ?", (target,)).fetchone()
            receiver_coins = receiver_balance[0] if receiver_balance else 1000
            
            cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (sender_coins - amount, from_id))
            cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (receiver_coins + amount, target))
            conn.commit()
            
            sender_name = self.get_user(from_id)
            receiver_name = self.get_user(target)
            
            self.send(peer_id, f"💸 {sender_name} перевел {amount} 🪙 пользователю {receiver_name}")
        
        elif cmd == "топ":
            top = cursor.execute(
                "SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 10"
            ).fetchall()
            
            if top:
                text = "🏆 **ТОП БОГАЧЕЙ:**\n\n"
                for i, (uid, coins) in enumerate(top, 1):
                    name = self.get_user(uid).split()[0]
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    text += f"{medal} {name} - {coins} 🪙\n"
                
                self.send(peer_id, text)
        
        elif cmd == "givemoney" and len(params) >= 2:
            if from_id != OWNER_ID and not self.has_permission(from_id, chat_id, "admin"):
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            amount = int(params[1])
            
            balance = cursor.execute("SELECT coins FROM users WHERE user_id = ?", (target,)).fetchone()
            current = balance[0] if balance else 1000
            
            cursor.execute("UPDATE users SET coins = ? WHERE user_id = ?", (current + amount, target))
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"💰 {name} получил {amount} 🪙 от администрации")
        
        elif cmd == "sysban" and len(params) >= 1:
            if from_id != OWNER_ID:
                self.send(peer_id, "⛔ Только для владельца!")
                return
                
            target = int(params[0].split('|')[0].replace('[id', ''))
            reason = ' '.join(params[1:]) if len(params) > 1 else "Системный бан"
            
            # Блокировка во всех чатах
            cursor.execute(
                "INSERT INTO bans (user_id, chat_id, reason, admin_id, date, expires) VALUES (?, ?, ?, ?, ?, ?)",
                (target, 0, reason, from_id, int(time.time()), 0)
            )
            conn.commit()
            
            name = self.get_user(target)
            self.send(peer_id, f"🔨 Системный бан для {name}\nПричина: {reason}")
        
        elif cmd == "clear" and len(params) >= 1 and params[0].isdigit():
            if not self.has_permission(from_id, chat_id, "admin") and from_id != OWNER_ID:
                self.send(peer_id, "⛔ Нет прав!")
                return
                
            count = int(params[0])
            if count > 100:
                count = 100
                
            try:
                history = self.vk.messages.getHistory(peer_id=peer_id, count=count)
                msg_ids = [msg['id'] for msg in history['items']]
                
                if msg_ids:
                    self.vk.messages.delete(message_ids=msg_ids, delete_for_all=1)
                    self.send(peer_id, f"✅ Удалено {len(msg_ids)} сообщений")
            except:
                self.send(peer_id, "❌ Ошибка удаления")

# ===== ЗАПУСК =====
if __name__ == "__main__":
    # Инициализация стандартных ролей для новых чатов будет при добавлении бота
    bot = AresBot()
    bot.run()
