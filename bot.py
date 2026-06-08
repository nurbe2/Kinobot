import telebot
from telebot import types
import sqlite3
import time
import os
from datetime import datetime
from flask import Flask

BOT_TOKEN = '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE'
ADMIN_ID = 8306639956
CHANNEL_USERNAME = '@Vexron_stars'
KINO_CHANNEL = '@Vexron_stars'
PORT = int(os.environ.get('PORT', 10000))

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlamoqda!"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS kinolar (kod INT, nomi TEXT, tavsif TEXT, reyting REAL, tip TEXT, fayl TEXT, qism INT, janr TEXT, sana TEXT, korishlar INT DEFAULT 0)")
c.execute("CREATE TABLE IF NOT EXISTS qismlar (kod INT, qism_no INT, video TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS pro (uid INT)")
c.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, kod INT, uid INT, username TEXT, matn TEXT, sana TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS users (uid INT PRIMARY KEY, first_name TEXT, username TEXT, sana TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS ratings (id INTEGER PRIMARY KEY AUTOINCREMENT, kod INT, uid INT, rating INT)")
conn.commit()

states = {}

def check_sub(uid):
    try:
        s = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return s.status not in ['left', 'kicked']
    except:
        return False

def is_pro(uid):
    c.execute("SELECT uid FROM pro WHERE uid=?", (uid,))
    return c.fetchone() is not None

def add_user(uid, first_name, username):
    c.execute("SELECT uid FROM users WHERE uid=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (uid, first_name, username, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()

def send_to_channel(kino):
    try:
        caption = "🎬 YANGI KINO!\n\n" + str(kino[1]) + "\n⭐ " + str(kino[3]) + "/10\n📂 " + str(kino[7]) + "\n🔢 Kod: " + str(kino[0])
        if kino[4] == 'photo':
            bot.send_photo(KINO_CHANNEL, kino[5], caption=caption)
        else:
            bot.send_video(KINO_CHANNEL, kino[5], caption=caption)
    except:
        pass

@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    states.pop(uid, None)
    add_user(uid, msg.from_user.first_name, msg.from_user.username)
    if not check_sub(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Obuna bo'lish", url="https://t.me/" + CHANNEL_USERNAME[1:]))
        markup.add(types.InlineKeyboardButton("✅ Tekshirish", callback_data="check"))
        bot.send_message(uid, "Salom! " + CHANNEL_USERNAME + " ga obuna bo'ling.", reply_markup=markup)
        return
    menu(uid)

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_cb(call):
    uid = call.from_user.id
    if check_sub(uid):
        bot.delete_message(uid, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ OK!")
        menu(uid)
    else:
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True)

def menu(uid):
    p = "✅ PRO" if is_pro(uid) else "❌ Oddiy"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 Kod orqali qidirish", callback_data="code"),
        types.InlineKeyboardButton("🔎 Nomi orqali qidirish", callback_data="search_name"),
        types.InlineKeyboardButton("📂 Janr orqali qidirish", callback_data="genre"),
        types.InlineKeyboardButton("⭐ TOP Reyting", callback_data="top_rating"),
        types.InlineKeyboardButton("🔥 Eng ko'p ko'rilgan", callback_data="top_views"),
        types.InlineKeyboardButton("🎬 NexMovie Pro", callback_data="pro"),
        types.InlineKeyboardButton("📊 Statistika", callback_data="stats")
    )
    bot.send_message(uid, "🎬 Xush kelibsiz!\n👤 Holat: " + p, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.from_user.id, "❌ Admin emassiz!")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎬 Kino qo'shish", "📹 Qism qo'shish")
    markup.add("📋 Kinolar ro'yxati", "📊 To'liq statistika")
    markup.add("⬅️ Oddiy menyu")
    bot.send_message(msg.from_user.id, "👑 Admin Panel", reply_markup=markup)

# KINO QO'SHISH
@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and m.from_user.id == ADMIN_ID)
def add_kino(msg):
    states[msg.from_user.id] = {'step': 1, 'data': {}}
    bot.send_message(msg.from_user.id, "Kino kodini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 1)
def s1(msg):
    if not msg.text.isdigit():
        bot.send_message(msg.from_user.id, "Raqam!"); return
    states[msg.from_user.id]['data']['kod'] = int(msg.text)
    states[msg.from_user.id]['step'] = 2
    bot.send_message(msg.from_user.id, "Kino nomini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 2)
def s2(msg):
    states[msg.from_user.id]['data']['nomi'] = msg.text
    states[msg.from_user.id]['step'] = 3
    bot.send_message(msg.from_user.id, "Tavsif:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 3)
def s3(msg):
    states[msg.from_user.id]['data']['tavsif'] = msg.text
    states[msg.from_user.id]['step'] = 4
    bot.send_message(msg.from_user.id, "Reyting (1-10):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 4)
def s4(msg):
    try:
        r = float(msg.text)
        if r < 1 or r > 10:
            bot.send_message(msg.from_user.id, "1-10!"); return
    except:
        bot.send_message(msg.from_user.id, "Raqam!"); return
    states[msg.from_user.id]['data']['reyting'] = r
    states[msg.from_user.id]['step'] = 5
    bot.send_message(msg.from_user.id, "Rasm yoki video:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 5, content_types=['photo', 'video', 'text'])
def s5(msg):
    if msg.photo:
        states[msg.from_user.id]['data']['tip'] = 'photo'
        states[msg.from_user.id]['data']['fayl'] = msg.photo[-1].file_id
    elif msg.video:
        states[msg.from_user.id]['data']['tip'] = 'video'
        states[msg.from_user.id]['data']['fayl'] = msg.video.file_id
    else:
        bot.send_message(msg.from_user.id, "Rasm/video!"); return
    states[msg.from_user.id]['step'] = 6
    bot.send_message(msg.from_user.id, "Qismlar soni (0 ham mumkin):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 6)
def s6(msg):
    if not msg.text.isdigit():
        bot.send_message(msg.from_user.id, "Raqam!"); return
    states[msg.from_user.id]['data']['qism'] = int(msg.text)
    states[msg.from_user.id]['step'] = 7
    bot.send_message(msg.from_user.id, "Janrlar (vergul bilan):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 7)
def s7(msg):
    d = states[msg.from_user.id]['data']
    sana = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)", (d['kod'], d['nomi'], d['tavsif'], d['reyting'], d['tip'], d['fayl'], d['qism'], msg.text, sana))
    conn.commit()
    kino = (d['kod'], d['nomi'], d['tavsif'], d['reyting'], d['tip'], d['fayl'], d['qism'], msg.text)
    send_to_channel(kino)
    bot.send_message(msg.from_user.id, "✅ " + d['nomi'] + " qo'shildi va kanalga yuborildi!")
    states.pop(msg.from_user.id, None)
    admin(msg)

# QISM QO'SHISH
@bot.message_handler(func=lambda m: m.text == "📹 Qism qo'shish" and m.from_user.id == ADMIN_ID)
def add_qism(msg):
    states[msg.from_user.id] = {'step': 'q1', 'data': {}}
    bot.send_message(msg.from_user.id, "Kino kodi:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 'q1')
def q1(msg):
    if not msg.text.isdigit():
        bot.send_message(msg.from_user.id, "Raqam!"); return
    kod = int(msg.text)
    c.execute("SELECT * FROM kinolar WHERE kod=?", (kod,))
    k = c.fetchone()
    if not k:
        bot.send_message(msg.from_user.id, "Topilmadi!"); return
    states[msg.from_user.id]['data'] = {'kod': kod, 'max': k[6], 'nomi': k[1]}
    states[msg.from_user.id]['step'] = 'q2'
    bot.send_message(msg.from_user.id, "Qism raqami (1-" + str(k[6]) + "):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 'q2')
def q2(msg):
    if not msg.text.isdigit():
        bot.send_message(msg.from_user.id, "Raqam!"); return
    q = int(msg.text)
    if q < 1 or q > states[msg.from_user.id]['data']['max']:
        bot.send_message(msg.from_user.id, "Notogri!"); return
    states[msg.from_user.id]['data']['qism'] = q
    states[msg.from_user.id]['step'] = 'q3'
    bot.send_message(msg.from_user.id, "Video:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 'q3', content_types=['video', 'text'])
def q3(msg):
    if not msg.video:
        bot.send_message(msg.from_user.id, "Video!"); return
    d = states[msg.from_user.id]['data']
    c.execute("INSERT INTO qismlar VALUES (?, ?, ?)", (d['kod'], d['qism'], msg.video.file_id))
    conn.commit()
    bot.send_message(msg.from_user.id, "✅ " + str(d['qism']) + "-qism qo'shildi!")
    states.pop(msg.from_user.id, None)
    admin(msg)

# KOD ORQALI QIDIRISH
@bot.callback_query_handler(func=lambda c: c.data == "code")
def search_code(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    states[call.from_user.id] = {'step': 'search'}
    bot.send_message(call.from_user.id, "Kino kodini kiriting:")

# NOMI ORQALI QIDIRISH
@bot.callback_query_handler(func=lambda c: c.data == "search_name")
def search_name(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    states[call.from_user.id] = {'step': 'search_name'}
    bot.send_message(call.from_user.id, "Kino nomini kiriting:")

@bot.message_handler(func=lambda m: states.get(m.from_user.id, {}).get('step') == 'search_name')
def show_kino_name(msg):
    uid = msg.from_user.id
    nomi = msg.text.strip()
    c.execute("SELECT * FROM kinolar WHERE nomi LIKE ?", ('%' + nomi + '%',))
    kinolar = c.fetchall()
    if not kinolar:
        bot.send_message(uid, "Topilmadi!"); states.pop(uid, None); return
    states.pop(uid, None)
    if len(kinolar) == 1:
        send_kino_info(uid, kinolar[0])
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for k in kinolar:
            markup.add(types.InlineKeyboardButton("🎬 " + k[1] + " (⭐" + str(k[3]) + ")", callback_data="v_" + str(k[0])))
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
        bot.send_message(uid, "'" + nomi + "' bo'yicha topildi:", reply_markup=markup)

def send_kino_info(uid, k, increase_view=True):
    if increase_view:
        c.execute("UPDATE kinolar SET korishlar = korishlar + 1 WHERE kod=?", (k[0],))
        conn.commit()
    
    cap = "🎬 " + str(k[1]) + "\n\n📝 " + str(k[2]) + "\n⭐ " + str(k[3]) + "/10\n📂 " + str(k[7]) + "\n🔢 Kod: " + str(k[0]) + "\n📹 Qismlar: " + str(k[6]) + "\n👁 Ko'rilgan: " + str(k[9]) + "\n📅 " + str(k[8])
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    markup.add(
        types.InlineKeyboardButton("⭐1", callback_data="rate_" + str(k[0]) + "_1"),
        types.InlineKeyboardButton("⭐2", callback_data="rate_" + str(k[0]) + "_2"),
        types.InlineKeyboardButton("⭐3", callback_data="rate_" + str(k[0]) + "_3"),
        types.InlineKeyboardButton("⭐4", callback_data="rate_" + str(k[0]) + "_4"),
        types.InlineKeyboardButton("⭐5", callback_data="rate_" + str(k[0]) + "_5")
    )
    
    if k[6] > 0:
        c.execute("SELECT qism_no FROM qismlar WHERE kod=? ORDER BY qism_no", (k[0],))
        for q in c.fetchall():
            markup.add(types.InlineKeyboardButton("📹 " + str(q[0]) + "-qism", callback_data="w_" + str(k[0]) + "_" + str(q[0])))
    
    markup.add(
        types.InlineKeyboardButton("💬 Fikr bildirish", callback_data="review_" + str(k[0])),
        types.InlineKeyboardButton("📋 Fikrlar", callback_data="reviews_" + str(k[0]))
    )
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    
    if k[4] == 'photo':
        bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
    else:
        bot.send_video(uid, k[5], caption=cap, reply_markup=markup)

# REYTING
@bot.callback_query_handler(func=lambda c: c.data.startswith('rate_'))
def rate_kino(call):
    uid = call.from_user.id
    parts = call.data.split('_')
    kod = int(parts[1])
    rating = int(parts[2])
    c.execute("SELECT id FROM ratings WHERE kod=? AND uid=?", (kod, uid))
    if c.fetchone():
        c.execute("UPDATE ratings SET rating=? WHERE kod=? AND uid=?", (rating, kod, uid))
    else:
        c.execute("INSERT INTO ratings (kod, uid, rating) VALUES (?, ?, ?)", (kod, uid, rating))
    conn.commit()
    c.execute("SELECT AVG(rating) FROM ratings WHERE kod=?", (kod,))
    avg = c.fetchone()[0]
    c.execute("UPDATE kinolar SET reyting=? WHERE kod=?", (round(avg, 1), kod))
    conn.commit()
    bot.answer_callback_query(call.id, "⭐ " + str(rating) + " baholandingiz!")

# FIKR
@bot.callback_query_handler(func=lambda c: c.data.startswith('review_') and not c.data.startswith('reviews_'))
def review_start(call):
    uid = call.from_user.id
    kod = int(call.data.split('_')[1])
    states[uid] = {'step': 'review', 'kod': kod}
    bot.answer_callback_query(call.id)
    bot.send_message(uid, "💬 Fikringizni yozing:")

@bot.message_handler(func=lambda m: states.get(m.from_user.id, {}).get('step') == 'review')
def save_review(msg):
    uid = msg.from_user.id
    kod = states[uid]['kod']
    username = "@" + msg.from_user.username if msg.from_user.username else msg.from_user.first_name
    c.execute("INSERT INTO reviews (kod, uid, username, matn, sana) VALUES (?, ?, ?, ?, ?)", (kod, uid, username, msg.text, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    bot.send_message(uid, "✅ Fikringiz qabul qilindi!")
    states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('reviews_'))
def show_reviews(call):
    uid = call.from_user.id
    kod = int(call.data.split('_')[1])
    c.execute("SELECT * FROM reviews WHERE kod=? ORDER BY id DESC LIMIT 10", (kod,))
    reviews = c.fetchall()
    if not reviews:
        bot.answer_callback_query(call.id, "❌ Fikrlar yo'q!", show_alert=True); return
    text = "💬 Fikrlar:\n\n"
    for r in reviews:
        text += "👤 " + str(r[3]) + ": " + str(r[4]) + "\n📅 " + str(r[5]) + "\n➖➖➖➖➖\n"
    bot.send_message(uid, text)

@bot.callback_query_handler(func=lambda c: c.data.startswith('w_'))
def watch(call):
    _, kod, qism = call.data.split('_')
    c.execute("SELECT video FROM qismlar WHERE kod=? AND qism_no=?", (int(kod), int(qism)))
    r = c.fetchone()
    if r:
        bot.send_video(call.from_user.id, r[0], caption="📹 " + qism + "-qism")
        bot.answer_callback_query(call.id, "✅ Yuborildi!")

# JANR
@bot.callback_query_handler(func=lambda c: c.data == "genre")
def genre(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    c.execute("SELECT DISTINCT janr FROM kinolar")
    janrlar = set()
    for row in c.fetchall():
        for j in row[0].split(','):
            if j.strip():
                janrlar.add(j.strip())
    if not janrlar:
        bot.answer_callback_query(call.id, "Kinolar yoq!", show_alert=True); return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for j in sorted(janrlar):
        markup.add(types.InlineKeyboardButton("📂 " + j, callback_data="g_" + j))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    bot.edit_message_text("Janrni tanlang:", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('g_'))
def show_genre(call):
    janr = call.data[2:]
    c.execute("SELECT * FROM kinolar WHERE janr LIKE ?", ('%' + janr + '%',))
    kinolar = c.fetchall()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k in kinolar:
        markup.add(types.InlineKeyboardButton("🎬 " + k[1] + " (⭐" + str(k[3]) + ")", callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="genre"))
    bot.edit_message_text("'" + janr + "' janridagi kinolar:", call.from_user.id, call.message.message_id, reply_markup=markup)

# TOP REYTING
@bot.callback_query_handler(func=lambda c: c.data == "top_rating")
def top_rating(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    c.execute("SELECT * FROM kinolar ORDER BY reyting DESC LIMIT 10")
    kinolar = c.fetchall()
    if not kinolar:
        bot.answer_callback_query(call.id, "Kinolar yoq!", show_alert=True); return
    text = "⭐ TOP 10 Reyting:\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, k in enumerate(kinolar, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i) + "."
        text += emoji + " " + k[1] + " - ⭐" + str(k[3]) + "\n"
        markup.add(types.InlineKeyboardButton(str(i) + ". " + k[1] + " (⭐" + str(k[3]) + ")", callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)

# TOP KO'RILGAN
@bot.callback_query_handler(func=lambda c: c.data == "top_views")
def top_views(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    c.execute("SELECT * FROM kinolar ORDER BY korishlar DESC LIMIT 10")
    kinolar = c.fetchall()
    if not kinolar:
        bot.answer_callback_query(call.id, "Kinolar yoq!", show_alert=True); return
    text = "🔥 Eng ko'p ko'rilgan:\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, k in enumerate(kinolar, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else str(i) + "."
        text += emoji + " " + k[1] + " - 👁" + str(k[9]) + "\n"
        markup.add(types.InlineKeyboardButton(str(i) + ". " + k[1] + " (👁" + str(k[9]) + ")", callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)

# STATISTIKA
@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(call):
    uid = call.from_user.id
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM kinolar")
    kino_count = c.fetchone()[0]
    c.execute("SELECT SUM(korishlar) FROM kinolar")
    total_views = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM pro")
    pro_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM reviews")
    reviews_count = c.fetchone()[0]
    text = "📊 Statistika:\n\n👥 Foydalanuvchilar: " + str(users_count) + "\n🎬 Kinolar: " + str(kino_count) + "\n👁 Ko'rishlar: " + str(total_views) + "\n👑 PRO: " + str(pro_count) + "\n💬 Fikrlar: " + str(reviews_count)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    bot.edit_message_text(text, uid, call.message.message_id, reply_mark
