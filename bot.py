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
    return "OK"

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

def add_user(uid, name, username):
    c.execute("SELECT uid FROM users WHERE uid=?", (uid,))
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (uid, name, username, datetime.now().strftime("%Y-%m-%d")))
        conn.commit()

@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    states.pop(uid, None)
    add_user(uid, msg.from_user.first_name, msg.from_user.username)
    if not check_sub(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Obuna bolish", url="https://t.me/" + CHANNEL_USERNAME[1:]))
        markup.add(types.InlineKeyboardButton("Tekshirish", callback_data="check"))
        bot.send_message(uid, "Salom! " + CHANNEL_USERNAME + " ga obuna boling.", reply_markup=markup)
        return
    menu(uid)

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_cb(call):
    uid = call.from_user.id
    if check_sub(uid):
        bot.delete_message(uid, call.message.message_id)
        bot.answer_callback_query(call.id, "OK")
        menu(uid)
    else:
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True)

def menu(uid):
    p = "PRO" if is_pro(uid) else "Oddiy"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Kod orqali", callback_data="code"),
        types.InlineKeyboardButton("Nomi orqali", callback_data="search_name"),
        types.InlineKeyboardButton("Janr orqali", callback_data="genre"),
        types.InlineKeyboardButton("TOP Reyting", callback_data="top_rating"),
        types.InlineKeyboardButton("TOP Korilgan", callback_data="top_views"),
        types.InlineKeyboardButton("NexMovie Pro", callback_data="pro"),
        types.InlineKeyboardButton("Statistika", callback_data="stats")
    )
    bot.send_message(uid, "Xush kelibsiz! " + p, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.from_user.id, "Admin emassiz!")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("Kino qoshish", "Qism qoshish")
    markup.add("Kinolar royxati", "Toliq statistika")
    markup.add("Oddiy menyu")
    bot.send_message(msg.from_user.id, "Admin Panel", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Kino qoshish" and m.from_user.id == ADMIN_ID)
def add_kino(msg):
    states[msg.from_user.id] = {'step': 1, 'data': {}}
    bot.send_message(msg.from_user.id, "Kod:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 1)
def s1(msg):
    if not msg.text.isdigit():
        bot.send_message(msg.from_user.id, "Raqam!"); return
    states[msg.from_user.id]['data']['kod'] = int(msg.text)
    states[msg.from_user.id]['step'] = 2
    bot.send_message(msg.from_user.id, "Nomi:")

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
    bot.send_message(msg.from_user.id, "Rasm/video:")

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
    bot.send_message(msg.from_user.id, "Qismlar soni:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 6)
def s6(msg):
    if not msg.text.isdigit():
        bot.send_message(msg.from_user.id, "Raqam!"); return
    states[msg.from_user.id]['data']['qism'] = int(msg.text)
    states[msg.from_user.id]['step'] = 7
    bot.send_message(msg.from_user.id, "Janr:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 7)
def s7(msg):
    d = states[msg.from_user.id]['data']
    sana = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)", (d['kod'], d['nomi'], d['tavsif'], d['reyting'], d['tip'], d['fayl'], d['qism'], msg.text, sana))
    conn.commit()
    try:
        if d['tip'] == 'photo':
            bot.send_photo(KINO_CHANNEL, d['fayl'], caption="Yangi: " + d['nomi'])
        else:
            bot.send_video(KINO_CHANNEL, d['fayl'], caption="Yangi: " + d['nomi'])
    except:
        pass
    bot.send_message(msg.from_user.id, "OK qoshildi!")
    states.pop(msg.from_user.id, None)
    admin(msg)

@bot.message_handler(func=lambda m: m.text == "Qism qoshish" and m.from_user.id == ADMIN_ID)
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
    states[msg.from_user.id]['data'] = {'kod': kod, 'max': k[6]}
    states[msg.from_user.id]['step'] = 'q2'
    bot.send_message(msg.from_user.id, "Qism (1-" + str(k[6]) + "):")

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

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and states.get(m.from_user.id, {}).get('step') == 'q3', content_types=['video'])
def q3(msg):
    d = states[msg.from_user.id]['data']
    c.execute("INSERT INTO qismlar VALUES (?, ?, ?)", (d['kod'], d['qism'], msg.video.file_id))
    conn.commit()
    bot.send_message(msg.from_user.id, "OK qoshildi!")
    states.pop(msg.from_user.id, None)
    admin(msg)

@bot.callback_query_handler(func=lambda c: c.data == "code")
def search_code(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True); return
    states[call.from_user.id] = {'step': 'search'}
    bot.send_message(call.from_user.id, "Kod:")

@bot.callback_query_handler(func=lambda c: c.data == "search_name")
def search_name(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True); return
    states[call.from_user.id] = {'step': 'search_name'}
    bot.send_message(call.from_user.id, "Nomi:")

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
        send_kino(uid, kinolar[0])
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for k in kinolar:
            markup.add(types.InlineKeyboardButton(k[1], callback_data="v_" + str(k[0])))
        markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
        bot.send_message(uid, "Topildi:", reply_markup=markup)

def send_kino(uid, k, view=True):
    if view:
        c.execute("UPDATE kinolar SET korishlar = korishlar + 1 WHERE kod=?", (k[0],))
        conn.commit()
    cap = k[1] + "\n\n" + k[2] + "\n⭐" + str(k[3]) + "/10\n" + k[7] + "\nKod: " + str(k[0]) + "\nQism: " + str(k[6]) + "\nKorildi: " + str(k[9])
    markup = types.InlineKeyboardMarkup(row_width=5)
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton(str(i), callback_data="rate_" + str(k[0]) + "_" + str(i)))
    if k[6] > 0:
        c.execute("SELECT qism_no FROM qismlar WHERE kod=?", (k[0],))
        for q in c.fetchall():
            markup.add(types.InlineKeyboardButton(str(q[0]) + "-qism", callback_data="w_" + str(k[0]) + "_" + str(q[0])))
    markup.add(types.InlineKeyboardButton("Fikr", callback_data="review_" + str(k[0])), types.InlineKeyboardButton("Fikrlar", callback_data="reviews_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    if k[4] == 'photo':
        bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
    else:
        bot.send_video(uid, k[5], caption=cap, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('rate_'))
def rate_kino(call):
    _, kod, rating = call.data.split('_')
    kod = int(kod); rating = int(rating); uid = call.from_user.id
    c.execute("SELECT id FROM ratings WHERE kod=? AND uid=?", (kod, uid))
    if c.fetchone():
        c.execute("UPDATE ratings SET rating=? WHERE kod=? AND uid=?", (rating, kod, uid))
    else:
        c.execute("INSERT INTO ratings (kod, uid, rating) VALUES (?, ?, ?)", (kod, uid, rating))
    conn.commit()
    c.execute("SELECT AVG(rating) FROM ratings WHERE kod=?", (kod,))
    c.execute("UPDATE kinolar SET reyting=? WHERE kod=?", (round(c.fetchone()[0], 1), kod))
    conn.commit()
    bot.answer_callback_query(call.id, "OK")

@bot.callback_query_handler(func=lambda c: c.data.startswith('review_') and not c.data.startswith('reviews_'))
def review_start(call):
    kod = int(call.data.split('_')[1])
    states[call.from_user.id] = {'step': 'review', 'kod': kod}
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "Fikr:")

@bot.message_handler(func=lambda m: states.get(m.from_user.id, {}).get('step') == 'review')
def save_review(msg):
    uid = msg.from_user.id; kod = states[uid]['kod']
    name = "@" + msg.from_user.username if msg.from_user.username else msg.from_user.first_name
    c.execute("INSERT INTO reviews (kod, uid, username, matn, sana) VALUES (?, ?, ?, ?, ?)", (kod, uid, name, msg.text, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    bot.send_message(uid, "OK")
    states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('reviews_'))
def show_reviews(call):
    kod = int(call.data.split('_')[1])
    c.execute("SELECT * FROM reviews WHERE kod=? ORDER BY id DESC LIMIT 10", (kod,))
    revs = c.fetchall()
    if not revs:
        bot.answer_callback_query(call.id, "Yoq!", show_alert=True); return
    text = "Fikrlar:\n\n"
    for r in revs:
        text += r[3] + ": " + r[4] + "\n---\n"
    bot.send_message(call.from_user.id, text)

@bot.callback_query_handler(func=lambda c: c.data.startswith('w_'))
def watch(call):
    _, kod, qism = call.data.split('_')
    c.execute("SELECT video FROM qismlar WHERE kod=? AND qism_no=?", (int(kod), int(qism)))
    r = c.fetchone()
    if r:
        bot.send_video(call.from_user.id, r[0], caption=qism + "-qism")
        bot.answer_callback_query(call.id, "OK")

@bot.callback_query_handler(func=lambda c: c.data == "genre")
def genre(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True); return
    c.execute("SELECT DISTINCT janr FROM kinolar")
    janrlar = set()
    for row in c.fetchall():
        for j in row[0].split(','):
            if j.strip():
                janrlar.add(j.strip())
    if not janrlar:
        bot.answer_callback_query(call.id, "Yoq!", show_alert=True); return
    markup = types.InlineKeyboardMarkup(row_width=2)
    for j in sorted(janrlar):
        markup.add(types.InlineKeyboardButton(j, callback_data="g_" + j))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    bot.edit_message_text("Janr:", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('g_'))
def show_genre(call):
    janr = call.data[2:]
    c.execute("SELECT * FROM kinolar WHERE janr LIKE ?", ('%' + janr + '%',))
    kinolar = c.fetchall()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k in kinolar:
        markup.add(types.InlineKeyboardButton(k[1], callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="genre"))
    bot.edit_message_text(janr + ":", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "top_rating")
def top_rating(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True); return
    c.execute("SELECT * FROM kinolar ORDER BY reyting DESC LIMIT 10")
    kinolar = c.fetchall()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, k in enumerate(kinolar, 1):
        markup.add(types.InlineKeyboardButton(str(i) + ". " + k[1] + " ⭐" + str(k[3]), callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    bot.edit_message_text("TOP Reyting:", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "top_views")
def top_views(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True); return
    c.execute("SELECT * FROM kinolar ORDER BY korishlar DESC LIMIT 10")
    kinolar = c.fetchall()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, k in enumerate(kinolar, 1):
        markup.add(types.InlineKeyboardButton(str(i) + ". " + k[1] + " " + str(k[9]), callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    bot.edit_message_text("TOP Korilgan:", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(call):
    c.execute("SELECT COUNT(*) FROM users")
    u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM kinolar")
    k = c.fetchone()[0]
    c.execute("SELECT SUM(korishlar) FROM kinolar")
    v = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM pro")
    p = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM reviews")
    r = c.fetchone()[0]
    text = "Foydalanuvchilar: " + str(u)
    text += "\nKinolar: " + str(k)
    text += "\nKorishlar: " + str(v)
    text += "\nPRO: " + str(p)
    text += "\nFikrlar: " + str(r)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    bot.edit_message_text(text, call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Toliq statistika" and m.from_user.id == ADMIN_ID)
def full_stats(msg):
    c.execute("SELECT COUNT(*) FROM users")
    u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM kinolar")
    k = c.fetchone()[0]
    c.execute("SELECT SUM(korishlar) FROM kinolar")
    v = c.fetchone()[0] or 0
    c.execute("SELECT COUNT(*) FROM pro")
    p = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM reviews")
    r = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ratings")
    rt = c.fetchone()[0]
    text = "Foydalanuvchilar: " + str(u)
    text += "\nKinolar: " + str(k)
    text += "\nKorishlar: " + str(v)
    text += "\nPRO: " + str(p)
    text += "\nFikrlar: " + str(r)
    text += "\nBaholar: " + str(rt)
    bot.send_message(msg.from_user.id, text)

@bot.callback_query_handler(func=lambda c: c.data == "pro")
def pro(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "Obuna boling!", show_alert=True); return
    if is_pro(call.from_user.id):
        bot.answer_callback_query(call.id, "PRO!", show_alert=True); return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Tolov qildim", callback_data="pay"))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    bot.edit_message_text("NexMovie Pro\n\n14.000 som\n4916 9903 1619 3280", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "pay")
def pay(call):
    states[call.from_user.id] = {'step': 'check'}
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "Chek rasmi:")

@bot.message_handler(func=lambda m: states.get(m.from_user.id, {}).get('step') == 'check', content_types=['photo'])
def check_msg(msg):
    uid = msg.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("Tasdiqlash", callback_data="ok_" + str(uid)))
    markup.add(types.InlineKeyboardButton("Bekor", callback_data="no_" + str(uid)))
    bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption="Chek! ID: " + str(uid), reply_markup=markup)
    bot.send_message(uid, "Yuborildi!")
    states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('ok_'))
def ok_pro(call):
    if call.from_user.id != ADMIN_ID: return
    uid = int(call.data[3:])
    
