# ============================================
# ARES: ЧАТ-МЕНЕДЖЕР (ПРЕМИУМ-ВЕРСИЯ)
# Полная копия Grand (кроме рабов)
# Команды через /, стиль, смайлики, роли, системные админы
# КОМПАКТНАЯ ВЕРСИЯ (ВСЕ КОМАНДЫ СОХРАНЕНЫ)
# ============================================

import vk_api, time, random, sqlite3, threading, os
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from datetime import datetime
from fastapi import FastAPI
import uvicorn

TOKEN = "vk1.a.NJgDVnKsv7inayrlqMXqJmevAVJBX0jAWCD33RC4w27CYWekHlXCvHFFsXNHp5447AHdmZboM2-SVBuyCk5Up1BqIxGOmkwwZ3pRjlizFJ8ogcMygQSMGxto-kzEm6lNBGqQjTifcD_MY4kLVejoqG_JcstMe3JXBuLc2wW_mWux-3gH2DVGckYcgr_oKKq5lV_c3vaMxvrGMTBYufPWgg"
GROUP_ID = 236517090
OWNER_ID = 853348780
BOT_NAME = "ARES"
PREFIX = "/"

conn = sqlite3.connect('ares.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, nick TEXT, warns INTEGER DEFAULT 0, muted INTEGER DEFAULT 0, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0, coins INTEGER DEFAULT 1000, bank INTEGER DEFAULT 0, daily INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, title TEXT, welcome TEXT, rules TEXT, silence INTEGER DEFAULT 0, games INTEGER DEFAULT 1)''')
c.execute('''CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, priority INTEGER, name TEXT, color TEXT, permissions TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_roles (user_id INTEGER, chat_id INTEGER, priority INTEGER, PRIMARY KEY (user_id, chat_id))''')
c.execute('''CREATE TABLE IF NOT EXISTS sysadmins (user_id INTEGER PRIMARY KEY, added_by INTEGER, date INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS bans (user_id INTEGER, chat_id INTEGER, reason TEXT, admin_id INTEGER, date INTEGER, expires INTEGER, PRIMARY KEY (user_id, chat_id))''')
c.execute('''CREATE TABLE IF NOT EXISTS stats (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, messages INTEGER DEFAULT 0, commands INTEGER DEFAULT 0, last_active INTEGER)''')
conn.commit()

DEFAULT_ROLES = [(100,"👑 Владелец","gold","all"), (80,"💎 Главный администратор","red","all"), (60,"🔴 Администратор","red","admin,mod,helper"), (40,"🟠 Модератор","orange","mod,helper,kick,mute,warn"), (20,"🟡 Помощник","yellow","helper,mute,warn"), (10,"🟢 Агент","green","custom"), (0,"⚪ Пользователь","gray","none")]

def uid(arg):
    if not arg: return None
    arg=arg.strip()
    if arg.startswith('[id') and '|' in arg:
        try: return int(arg.split('|')[0].replace('[id',''))
        except: return None
    if arg.isdigit(): return int(arg)
    return None

def fmt(sec):
    if sec<60: return f"{sec} сек"
    if sec<3600: return f"{sec//60} мин"
    if sec<86400: return f"{sec//3600} ч"
    return f"{sec//86400} дн"

def get_name(vk, uid):
    try: u=vk.users.get(user_ids=uid)[0]; return f"{u['first_name']} {u['last_name']}"
    except: return f"id{uid}"

class AresBot:
    def __init__(self):
        self.vk=vk_api.VkApi(token=TOKEN).get_api()
        self.lp=VkBotLongPoll(vk_api.VkApi(token=TOKEN), group_id=GROUP_ID)
        self.start=time.time()
        print(f"✅ {BOT_NAME} запущен! Владелец: id{OWNER_ID}")
        print(f"🚀 Команды: {PREFIX}помощь")
        
    def send(self, peer, msg):
        try: self.vk.messages.send(peer_id=peer, message=msg, random_id=get_random_id())
        except: pass
        
    def name(self, uid): return get_name(self.vk, uid)
    
    def is_sys(self, uid): return uid==OWNER_ID or c.execute("SELECT 1 FROM sysadmins WHERE user_id=?",(uid,)).fetchone()
    
    def prio(self, uid, chat):
        if self.is_sys(uid): return 1000
        r=c.execute("SELECT priority FROM user_roles WHERE user_id=? AND chat_id=?",(uid,chat)).fetchone()
        return r[0] if r else 0
        
    def can(self, uid, chat, perm):
        if self.is_sys(uid): return True
        p=self.prio(uid,chat)
        if perm in('kick','mute','warn','unmute','unwarn'): return p>=20
        if perm in('ban','unban','banlist'): return p>=40
        if perm in('admin','role','newrole','delrole'): return p>=60
        if perm in('owner','settings','sysadmin'): return p>=100
        return False
        
    def kick(self, chat, user):
        try: self.vk.messages.removeChatUser(chat_id=chat, user_id=user); return True
        except: return False
        
    def init_roles(self, chat):
        if c.execute("SELECT COUNT(*) FROM roles WHERE chat_id=?",(chat,)).fetchone()[0]==0:
            for p,n,col,perm in DEFAULT_ROLES:
                c.execute("INSERT INTO roles (chat_id,priority,name,color,permissions) VALUES (?,?,?,?,?)",(chat,p,n,col,perm))
            conn.commit()
            
    def run(self):
        print("🚀 Бот слушает события...")
        while True:
            try:
                for e in self.lp.listen():
                    if e.type==VkBotEventType.MESSAGE_NEW: self.msg(e)
                    elif e.type==VkBotEventType.CHAT_INVITE_USER: self.inv(e)
            except Exception as ex: print(f"Ошибка: {ex}"); time.sleep(5)
                
    def msg(self, e):
        m=e.obj.message; peer=m['peer_id']; frm=m['from_id']; txt=m['text'].strip()
        if frm==-GROUP_ID: return
        chat=peer-2000000000 if peer>2000000000 else None
        if c.execute("SELECT 1 FROM bans WHERE user_id=? AND chat_id=0 AND (expires>? OR expires=0)",(frm,int(time.time()))).fetchone(): return
        muted=c.execute("SELECT muted FROM users WHERE user_id=?",(frm,)).fetchone()
        if muted and muted[0] and muted[0]>time.time(): return
        c.execute("INSERT INTO stats (user_id,chat_id,messages,last_active) VALUES (?,?,1,?)",(frm,chat,int(time.time())))
        c.execute("UPDATE users SET messages=COALESCE(messages,0)+1 WHERE user_id=?",(frm,)); conn.commit()
        if txt.startswith(PREFIX): self.cmd(txt[1:], peer, frm, chat)
        
    def inv(self, e):
        chat=e.chat_id; peer=2000000000+chat; inv_id=e.obj['action']['member_id']
        if inv_id==-GROUP_ID:
            self.init_roles(chat)
            self.send(peer, f"👋 Всем привет! Я {BOT_NAME} — чат-менеджер.\n{PREFIX}помощь — список команд.")
        elif inv_id>0:
            w=c.execute("SELECT welcome FROM chats WHERE chat_id=?",(chat,)).fetchone()
            wt=w[0] if w and w[0] else "👋 Добро пожаловать, {name}!"
            self.send(peer, wt.replace("{name}", self.name(inv_id)))
            
    def cmd(self, t, peer, frm, chat):
        p=t.split(); cmd=p[0].lower(); a=p[1:] if len(p)>1 else []
        if cmd in ['помощь','help','команды']: self.c_help(peer)
        elif cmd in ['пинг','ping']: self.c_ping(peer)
        elif cmd in ['правила','rules']: self.c_rules(peer,chat)
        elif cmd in ['админы','admins','staff']: self.c_admins(peer,chat)
        elif cmd in ['онлайн','online']: self.c_online(peer,chat)
        elif cmd in ['стата','stats','статистика']: self.c_stats(a,peer,frm,chat)
        elif cmd in ['профиль']: self.c_profile(peer,frm)
        elif cmd in ['топ']: self.c_top(peer,chat)
        elif cmd in ['кик','kick']: self.c_kick(a,peer,frm,chat)
        elif cmd in ['варн','warn']: self.c_warn(a,peer,frm,chat)
        elif cmd in ['снятьварн','unwarn']: self.c_unwarn(a,peer,frm,chat)
        elif cmd in ['мут','mute']: self.c_mute(a,peer,frm,chat)
        elif cmd in ['унмут','unmute']: self.c_unmute(a,peer,frm,chat)
        elif cmd in ['бан','ban']: self.c_ban(a,peer,frm,chat)
        elif cmd in ['унбан','unban']: self.c_unban(a,peer,frm,chat)
        elif cmd in ['банлист','banlist']: self.c_banlist(peer,chat)
        elif cmd in ['роль','role','giverole']: self.c_role(a,peer,frm,chat)
        elif cmd in ['снятьроль','removerole']: self.c_removerole(a,peer,frm,chat)
        elif cmd in ['new','newrole']: self.c_newrole(a,peer,frm,chat)
        elif cmd in ['delrole','deleterole']: self.c_delrole(a,peer,frm,chat)
        elif cmd in ['sysadmin']: self.c_sysadmin(a,peer,frm,chat)
        elif cmd in ['sysrole']: self.c_sysrole(a,peer,frm,chat)
        elif cmd in ['givemoney']: self.c_givemoney(a,peer,frm,chat)
        elif cmd in ['sysban']: self.c_sysban(a,peer,frm,chat)
        elif cmd in ['казино','casino']: self.c_casino(a,peer,frm,chat)
        elif cmd in ['перевод','pay','give']: self.c_pay(a,peer,frm,chat)
        elif cmd in ['бонус','daily']: self.c_daily(peer,frm)
        elif cmd in ['анекдот','joke']: self.c_joke(peer)
        elif cmd in ['факт','fact']: self.c_fact(peer)
        elif cmd in ['шар','ball']: self.c_ball(a,peer)
        else: self.send(peer, f"❌ Неизвестная команда. Введите {PREFIX}помощь")
        
    def c_help(self, peer):
        self.send(peer, f"🔔 **{BOT_NAME}** удобный и простой бот.\n\n📜 Отображена малая часть необходимых команд:\n{PREFIX}кик — исключить пользователя\n{PREFIX}бан — заблокировать пользователя\n{PREFIX}унбан — разблокировать участника\n{PREFIX}мут — запретить писать в чат\n{PREFIX}унмут — разрешить писать в чат\n{PREFIX}варн — выдать предупреждение\n{PREFIX}снятьварн — снять предупреждение\n{PREFIX}админы — отобразить список участников с ролью\n{PREFIX}роль — выдать роль участнику\n{PREFIX}профиль — ваш профиль и баланс\n{PREFIX}казино — сыграть в казино\n{PREFIX}перевод — перевести монеты\n{PREFIX}топ — топ богачей\n{PREFIX}помощь — это сообщение")
        
    def c_ping(self, peer): self.send(peer, f"🏓 Понг! Время работы: {fmt(int(time.time()-self.start))}")
        
    def c_rules(self, peer, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        r=c.execute("SELECT rules FROM chats WHERE chat_id=?",(chat,)).fetchone()
        self.send(peer, f"📜 **Правила чата:**\n{r[0]}" if r and r[0] else "📜 Правила не установлены.")
        
    def c_admins(self, peer, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        a=c.execute("SELECT user_id,priority FROM user_roles WHERE chat_id=? AND priority>=20",(chat,)).fetchall()
        if not a: self.send(peer, "👥 В чате нет администраторов."); return
        t="👥 **Администрация чата:**\n"
        for uid,p in a:
            name=self.name(uid); rn=c.execute("SELECT name FROM roles WHERE chat_id=? AND priority=?",(chat,p)).fetchone()
            t+=f"• {name} — {rn[0] if rn else f'приоритет {p}'}\n"
        self.send(peer, t)
        
    def c_online(self, peer, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        try:
            m=self.vk.messages.getConversationMembers(peer_id=2000000000+chat)['items']
            o=[x for x in m if x.get('online') and x['member_id']>0]
            if not o: self.send(peer, "🟢 Сейчас нет онлайн."); return
            t="🟢 **Онлайн:**\n"+"".join(f"• {self.name(x['member_id'])}\n" for x in o)
            self.send(peer, t)
        except: self.send(peer, "❌ Ошибка.")
            
    def c_stats(self, a, peer, frm, chat):
        t=frm
        if a and (u:=uid(a[0])): t=u
        name=self.name(t); d=c.execute("SELECT warns,level,exp,coins FROM users WHERE user_id=?",(t,)).fetchone()
        w,l,e,co=d if d else (0,1,0,1000); nx=l*100; fl=int((e/nx)*10) if nx else 0; bar="█"*fl+"░"*(10-fl)
        self.send(peer, f"📊 **Статистика {name}**\n⚠️ Предупреждений: {w}/3\n📈 Уровень: {l} | Опыт: {e}/{nx}\n📊 [{bar}]\n💰 Монет: {co} 🪙")
        
    def c_profile(self, peer, frm): self.c_stats([], peer, frm, None)
        
    def c_top(self, peer, chat):
        t=c.execute("SELECT user_id,coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
        if not t: self.send(peer, "🏆 Топ пуст."); return
        txt="🏆 **Топ богачей:**\n"
        for i,(uid,co) in enumerate(t,1):
            m="🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
            txt+=f"{m} {self.name(uid)} — {co} 🪙\n"
        self.send(peer, txt)
        
    def c_kick(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'kick'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}кик @id [причина]"); return
        t=uid(a[0]); r=" ".join(a[1:]) if len(a)>1 else "Не указана"
        if not t or t==frm: self.send(peer, "❌ Некорректный пользователь."); return
        if self.prio(t,chat)>=self.prio(frm,chat) and not self.is_sys(frm): self.send(peer, "⛔ Выше приоритет."); return
        if self.kick(chat,t): self.send(peer, f"👢 {self.name(t)} исключён.\nПричина: {r}")
        else: self.send(peer, "❌ Не удалось.")
        
    def c_warn(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'warn'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}варн @id [причина]"); return
        t=uid(a[0]); r=" ".join(a[1:]) if len(a)>1 else "Не указана"
        if not t or t==frm: self.send(peer, "❌ Некорректный пользователь."); return
        if self.prio(t,chat)>=self.prio(frm,chat) and not self.is_sys(frm): self.send(peer, "⛔ Выше приоритет."); return
        c.execute("UPDATE users SET warns=COALESCE(warns,0)+1 WHERE user_id=?",(t,)); conn.commit()
        self.send(peer, f"⚠️ {self.name(t)} получил предупреждение.\nПричина: {r}")
        
    def c_unwarn(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'warn'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}снятьварн @id"); return
        t=uid(a[0]); 
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        c.execute("UPDATE users SET warns=MAX(0,COALESCE(warns,0)-1) WHERE user_id=?",(t,)); conn.commit()
        self.send(peer, f"✅ Предупреждение снято с {self.name(t)}.")
        
    def c_mute(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'mute'): self.send(peer, "⛔ Нет прав."); return
        if len(a)<2: self.send(peer, f"❌ Использование: {PREFIX}мут @id время [причина]"); return
        t=uid(a[0]); 
        if not t or t==frm: self.send(peer, "❌ Некорректный пользователь."); return
        try: m=int(a[1])
        except: self.send(peer, "❌ Время должно быть числом."); return
        if m<=0: self.send(peer, "❌ Положительное время."); return
        r=" ".join(a[2:]) if len(a)>2 else "Не указана"
        if self.prio(t,chat)>=self.prio(frm,chat) and not self.is_sys(frm): self.send(peer, "⛔ Выше приоритет."); return
        c.execute("UPDATE users SET muted=? WHERE user_id=?",(int(time.time())+m*60,t)); conn.commit()
        self.send(peer, f"🔇 {self.name(t)} замучен на {m} мин.\nПричина: {r}")
        
    def c_unmute(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'mute'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}унмут @id"); return
        t=uid(a[0])
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        c.execute("UPDATE users SET muted=0 WHERE user_id=?",(t,)); conn.commit()
        self.send(peer, f"🔊 {self.name(t)} размучен.")
        
    def c_ban(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'ban'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}бан @id [дни] [причина]"); return
        t=uid(a[0]); d=0; r="Не указана"
        if not t or t==frm: self.send(peer, "❌ Некорректный пользователь."); return
        if len(a)>1 and a[1].isdigit(): d=int(a[1]); r=" ".join(a[2:]) if len(a)>2 else "Не указана"
        else: r=" ".join(a[1:]) if len(a)>1 else "Не указана"
        e=0 if d==0 else int(time.time())+d*86400
        if self.prio(t,chat)>=self.prio(frm,chat) and not self.is_sys(frm): self.send(peer, "⛔ Выше приоритет."); return
        c.execute("INSERT OR REPLACE INTO bans (user_id,chat_id,reason,admin_id,date,expires) VALUES (?,?,?,?,?,?)",(t,chat,r,frm,int(time.time()),e)); conn.commit()
        self.kick(chat,t); bt="навсегда" if d==0 else f"на {d} дн."
        self.send(peer, f"🔨 {self.name(t)} забанен {bt}.\nПричина: {r}")
        
    def c_unban(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'ban'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}унбан @id"); return
        t=uid(a[0])
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        c.execute("DELETE FROM bans WHERE user_id=? AND chat_id=?",(t,chat)); conn.commit()
        self.send(peer, f"✅ {self.name(t)} разбанен.")
        
    def c_banlist(self, peer, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        b=c.execute("SELECT user_id,reason,date,expires FROM bans WHERE chat_id=?",(chat,)).fetchall()
        if not b: self.send(peer, "📋 Список пуст."); return
        t="📋 **Забаненные:**\n"
        for uid,rs,d,e in b:
            es="навсегда" if e==0 else f"до {datetime.fromtimestamp(e).strftime('%d.%m.%Y')}"
            t+=f"• {self.name(uid)} — {rs} ({es})\n"
        self.send(peer, t)
        
    def c_role(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'role'): self.send(peer, "⛔ Нет прав."); return
        if len(a)<2: self.send(peer, f"❌ Использование: {PREFIX}роль @id приоритет"); return
        t=uid(a[0]); 
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        try: p=int(a[1])
        except: self.send(peer, "❌ Приоритет должен быть числом."); return
        r=c.execute("SELECT name FROM roles WHERE chat_id=? AND priority=?",(chat,p)).fetchone()
        if not r: self.send(peer, "❌ Роль не существует."); return
        c.execute("INSERT OR REPLACE INTO user_roles (user_id,chat_id,priority) VALUES (?,?,?)",(t,chat,p)); conn.commit()
        self.send(peer, f"✅ {self.name(t)} получил роль «{r[0]}».")
        
    def c_removerole(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'role'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}снятьроль @id"); return
        t=uid(a[0])
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        c.execute("DELETE FROM user_roles WHERE user_id=? AND chat_id=?",(t,chat)); conn.commit()
        self.send(peer, f"✅ С {self.name(t)} сняты все роли.")
        
    def c_newrole(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'role'): self.send(peer, "⛔ Нет прав."); return
        if len(a)<2: self.send(peer, f"❌ Использование: {PREFIX}new приоритет название"); return
        try: p=int(a[0])
        except: self.send(peer, "❌ Приоритет должен быть числом."); return
        n=" ".join(a[1:]); 
        if not n: self.send(peer, "❌ Укажите название."); return
        e=c.execute("SELECT id FROM roles WHERE chat_id=? AND priority=?",(chat,p)).fetchone()
        if e: c.execute("UPDATE roles SET name=? WHERE chat_id=? AND priority=?",(n,chat,p)); self.send(peer, f"✅ Роль {p} обновлена: {n}")
        else: c.execute("INSERT INTO roles (chat_id,priority,name,color,permissions) VALUES (?,?,?,?,?)",(chat,p,n,"default","custom")); self.send(peer, f"✅ Создана роль: {n} (приоритет {p})")
        conn.commit()
        
    def c_delrole(self, a, peer, frm, chat):
        if not chat: self.send(peer, "❌ Только в беседах."); return
        if not self.can(frm,chat,'role'): self.send(peer, "⛔ Нет прав."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}delrole приоритет"); return
        try: p=int(a[0])
        except: self.send(peer, "❌ Приоритет должен быть числом."); return
        c.execute("DELETE FROM roles WHERE chat_id=? AND priority=?",(chat,p)); conn.commit()
        self.send(peer, f"✅ Роль {p} удалена.")
        
    def c_sysadmin(self, a, peer, frm, chat):
        if frm!=OWNER_ID: self.send(peer, "⛔ Только владелец."); return
        if not a: self.send(peer, f"❌ Использование: {PREFIX}sysadmin add/remove @id"); return
        sub=a[0].lower()
        if sub=="add" and len(a)>=2:
            t=uid(a[1]); 
            if not t: self.send(peer, "❌ Некорректный пользователь."); return
            c.execute("INSERT OR IGNORE INTO sysadmins (user_id,added_by,date) VALUES (?,?,?)",(t,frm,int(time.time()))); conn.commit()
            self.send(peer, f"✅ {self.name(t)} теперь системный администратор.")
        elif sub=="remove" and len(a)>=2:
            t=uid(a[1]); 
            if not t: self.send(peer, "❌ Некорректный пользователь."); return
            c.execute("DELETE FROM sysadmins WHERE user_id=?",(t,)); conn.commit()
            self.send(peer, f"✅ {self.name(t)} больше не системный администратор.")
        else: self.send(peer, f"❌ Использование: {PREFIX}sysadmin add @id или remove @id")
            
    def c_sysrole(self, a, peer, frm, chat):
        if not self.is_sys(frm): self.send(peer, "⛔ Только для системных админов."); return
        if len(a)<2: self.send(peer, f"❌ Использование: {PREFIX}sysrole @id приоритет"); return
        t=uid(a[0]); 
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        try: p=int(a[1])
        except: self.send(peer, "❌ Приоритет должен быть числом."); return
        if not chat: self.send(peer, "❌ Только в беседах."); return
        r=c.execute("SELECT name FROM roles WHERE chat_id=? AND priority=?",(chat,p)).fetchone()
        if not r: self.send(peer, "❌ Роль не существует."); return
        c.execute("INSERT OR REPLACE INTO user_roles (user_id,chat_id,priority) VALUES (?,?,?)",(t,chat,p)); conn.commit()
        self.send(peer, f"✅ (Sys) {self.name(t)} получил роль «{r[0]}».")
        
    def c_givemoney(self, a, peer, frm, chat):
        if not self.is_sys(frm): self.send(peer, "⛔ Только для системных админов."); return
        if len(a)<2: self.send(peer, f"❌ Использование: {PREFIX}givemoney @id сумма"); return
        t=uid(a[0]); 
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        try: am=int(a[1])
        except: self.send(peer, "❌ Сумма должна быть числом."); return
        if am<=0: self.send(peer, "❌ Положительная сумма."); return
        c.execute("UPDATE users SET coins=COALESCE(coins,1000)+? WHERE user_id=?",(am,t)); conn.commit()
        self.send(peer, f"💰 {self.name(t)} получил {am} 🪙 от системного администратора.")
        
    def c_sysban(self, a, peer, frm, chat):
        if not self.is_sys(frm): self.send(peer, "⛔ Только для системных админов."); return
        if len(a)<1: self.send(peer, f"❌ Использование: {PREFIX}sysban @id [дни] [причина]"); return
        t=uid(a[0]); d=0; r="Системный бан"
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        if len(a)>1 and a[1].isdigit(): d=int(a[1]); r=" ".join(a[2:]) if len(a)>2 else "Системный бан"
        else: r=" ".join(a[1:]) if len(a)>1 else "Системный бан"
        e=0 if d==0 else int(time.time())+d*86400
        c.execute("INSERT OR REPLACE INTO bans (user_id,chat_id,reason,admin_id,date,expires) VALUES (?,0,?,?,?,?)",(t,r,frm,int(time.time()),e)); conn.commit()
        bt="навсегда" if d==0 else f"на {d} дн."
        self.send(peer, f"🔨 (Sys) {self.name(t)} забанен глобально {bt}.\nПричина: {r}")
        
    def c_casino(self, a, peer, frm, chat):
        if chat:
            g=c.execute("SELECT games FROM chats WHERE chat_id=?",(chat,)).fetchone()
            if g and g[0]==0: self.send(peer, "🎮 Игры отключены."); return
        if not a or not a[0].isdigit(): self.send(peer, f"❌ Использование: {PREFIX}казино сумма"); return
        bet=int(a[0]); cur=c.execute("SELECT coins FROM users WHERE user_id=?",(frm,)).fetchone()
        coins=cur[0] if cur else 1000
        if coins<bet: self.send(peer, f"❌ Недостаточно. У вас {coins} 🪙"); return
        r=random.random()
        if r<0.45: win=0; res="❌ Проигрыш"; new=coins-bet
        elif r<0.75: win=bet; res="🤝 Ничья"; new=coins
        elif r<0.92: win=bet*2; res="✅ Выигрыш x2"; new=coins+bet
        else: win=bet*5; res="🎉 ДЖЕКПОТ x5!"; new=coins+bet*4
        c.execute("UPDATE users SET coins=? WHERE user_id=?",(new,frm)); conn.commit()
        self.send(peer, f"🎰 **Казино**\nСтавка: {bet} 🪙\nРезультат: {res}\nВыигрыш: {win} 🪙\nБаланс: {new} 🪙")
        
    def c_pay(self, a, peer, frm, chat):
        if len(a)<2: self.send(peer, f"❌ Использование: {PREFIX}перевод @id сумма"); return
        t=uid(a[0]); 
        if not t: self.send(peer, "❌ Некорректный пользователь."); return
        try: am=int(a[1])
        except: self.send(peer, "❌ Сумма должна быть числом."); return
        if am<=0: self.send(peer, "❌ Положительная сумма."); return
        cur=c.execute("SELECT coins FROM users WHERE user_id=?",(frm,)).fetchone()
        sc=cur[0] if cur else 1000
        if sc<am: self.send(peer, f"❌ Недостаточно. У вас {sc} 🪙"); return
        cur2=c.execute("SELECT coins FROM users WHERE user_id=?",(t,)).fetchone()
        rc=cur2[0] if cur2 else 1000
        c.execute("UPDATE users SET coins=? WHERE user_id=?",(sc-am,frm))
        c.execute("UPDATE users SET coins=? WHERE user_id=?",(rc+am,t)); conn.commit()
        self.send(peer, f"💸 {self.name(frm)} перевёл {am} 🪙 пользователю {self.name(t)}.")
        
    def c_daily(self, peer, frm):
        now=int(time.time()); cur=c.execute("SELECT coins,daily FROM users WHERE user_id=?",(frm,)).fetchone()
        coins=cur[0] if cur else 1000; last=cur[1] if cur and cur[1] else 0
        if now-last<86400: self.send(peer, f"⏳ Следующий бонус через {fmt(86400-(now-last))}."); return
        bonus=random.randint(100,500); new=coins+bonus
        c.execute("UPDATE users SET coins=?, daily=? WHERE user_id=?",(new,now,frm)); conn.commit()
        self.send(peer, f"🎁 Ежедневный бонус: +{bonus} 🪙. Баланс: {new} 🪙")
        
    def c_joke(self, peer):
        j=["Идёт ёжик по лесу, видит — машина горит. Сел и сгорел.","— Вовочка, почему ты опоздал в школу? — Снился сон, что я уже на уроке, вот я и не пошёл.","Программист просыпается и говорит жене: — Сегодня суббота или воскресенье? Жена: — Ещё не знаю, я не включала компьютер.","В зоопарке медведь спрашивает у волка: — Слышал, ты в цирк уходишь? — Да, надоело тут сидеть. — Ну как знаешь, а я отсюда ни ногой. — Это почему? — Да видишь ли, из цирка ещё никто не возвращался..."]
        self.send(peer, f"😄 {random.choice(j)}")
        
    def c_fact(self, peer):
        f=["Страусы бегают быстрее лошадей.","У тигров не только полосатая шерсть, но и кожа.","Клубника — не ягода, а многоорешек.","В Антарктиде есть реки и озёра.","Самый большой орган человека — кожа."]
        self.send(peer, f"📌 {random.choice(f)}")
        
    def c_ball(self, a, peer):
        if not a: self.send(peer, "🎱 Задай вопрос, например: /шар я сегодня выиграю?"); return
        ans=["Бесспорно","Предрешено","Никаких сомнений","Определённо да","Можешь быть уверен в этом","Мне кажется — да","Вероятнее всего","Хорошие перспективы","Знаки говорят — да","Да","Пока не ясно","Спроси позже","Лучше не рассказывать","Сейчас нельзя предсказать","Сконцентрируйся и спроси опять","Даже не думай","Мой ответ — нет","По моим данным — нет","Перспективы не очень","Весьма сомнительно"]
        self.send(peer, f"🎱 {random.choice(ans)}")

app=FastAPI()
@app.get("/")
def root(): return {"status": f"{BOT_NAME} is running"}

def run_bot():
    try: AresBot().run()
    except Exception as e: print(f"❌ Ошибка: {e}")

if __name__=="__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT",8000)))
