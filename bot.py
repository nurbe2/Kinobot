import telebot
from telebot import types
import sqlite3
import time
import os
from flask import Flask

# TOKENINGIZNI SHU YERGA YOZING!
BOT_TOKEN = '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE'
ADMIN_ID = 8306639956
CHANNEL_USERNAME = '@Vexron_stars'
PORT = int(os.environ.get('PORT', 10000))

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlamoqda!"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS kinolar (kod INT, nomi TEXT, tavsif TEXT, reyting REAL, tip TEXT, fayl TEXT, qism INT, janr TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS qismlar (kod INT, qism_no INT, video TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS pro (uid INT)")
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

@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    states.pop(uid, None)
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
    p = "PRO" if is_pro(uid) else "Oddiy"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 Kod orqali qidirish", callback_data="code"),
        types.InlineKeyboardButton("📂 Janr orqali qidirish", callback_data="genre"),
        types.InlineKeyboardButton("🎬 NexMovie Pro", callback_data="pro")
    )
    bot.send_message(uid, "Xush kelibsiz! Holat: " + p, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.send_message(msg.from_user.id, "❌ Admin emassiz!")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Kino qoshish", "Qism qoshish")
    markup.add("Oddiy menyu")
    bot.send_message(msg.from_user.id, "Admin Panel", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Kino qoshish" and m.from_user.id == ADMIN_ID)
def add_kino(msg):
    states[msg.from_user.id] = {'step': 1, 'data': {}}
    bot.send_message(msg.from_user.id, "Kino kodini kiriting:")

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
    c.execute("INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (d['kod'], d['nomi'], d['tavsif'], d['reyting'], d['tip'], d['fayl'], d['qism'], msg.text))
    conn.commit()
    bot.send_message(msg.from_user.id, "✅ Qoshildi!")
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
    bot.send_message(msg.from_user.id, "✅ Qoshildi!")
    states.pop(msg.from_user.id, None)
    admin(msg)

@bot.callback_query_handler(func=lambda c: c.data == "code")
def search_code(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    states[call.from_user.id] = {'step': 'search'}
    bot.send_message(call.from_user.id, "Kod:")

@bot.message_handler(func=lambda m: states.get(m.from_user.id, {}).get('step') == 'search')
def show(msg):
    uid = msg.from_user.id
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam!"); return
    c.execute("SELECT * FROM kinolar WHERE kod=?", (int(msg.text),))
    k = c.fetchone()
    if not k:
        bot.send_message(uid, "Topilmadi!"); states.pop(uid, None); return
    states.pop(uid, None)
    cap = k[1] + "\n" + k[2] + "\n⭐" + str(k[3]) + "\nJanr: " + k[7]
    markup = types.InlineKeyboardMarkup()
    if k[6] > 0:
        c.execute("SELECT qism_no FROM qismlar WHERE kod=?", (k[0],))
        for q in c.fetchall():
            markup.add(types.InlineKeyboardButton(str(q[0]) + "-qism", callback_data="w_" + str(k[0]) + "_" + str(q[0])))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    if k[4] == 'photo':
        bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
    else:
        bot.send_video(uid, k[5], caption=cap, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('w_'))
def watch(call):
    _, kod, qism = call.data.split('_')
    c.execute("SELECT video FROM qismlar WHERE kod=? AND qism_no=?", (int(kod), int(qism)))
    r = c.fetchone()
    if r:
        bot.send_video(call.from_user.id, r[0], caption=qism + "-qism")
        bot.answer_callback_query(call.id, "✅")

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
        markup.add(types.InlineKeyboardButton(k[1] + " ⭐" + str(k[3]), callback_data="v_" + str(k[0])))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="genre"))
    bot.edit_message_text(janr + ":", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "pro")
def pro(call):
    if not check_sub(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    if is_pro(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ PRO!", show_alert=True); return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 Tolov qildim", callback_data="pay"))
    markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
    bot.edit_message_text("NexMovie Pro\n\n💰 14.000 som\n💳 4916 9903 1619 3280\n\nChekni yuboring!", call.from_user.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "pay")
def pay(call):
    states[call.from_user.id] = {'step': 'check'}
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, "Chek rasmi:")

@bot.message_handler(func=lambda m: states.get(m.from_user.id, {}).get('step') == 'check', content_types=['photo'])
def check_msg(msg):
    file_id = msg.photo[-1].file_id
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="ok_" + str(msg.from_user.id)),
        types.InlineKeyboardButton("❌ Bekor", callback_data="no_" + str(msg.from_user.id))
    )
    bot.send_photo(ADMIN_ID, file_id, caption="Chek! ID: " + str(msg.from_user.id), reply_markup=markup)
    bot.send_message(msg.from_user.id, "✅ Yuborildi!")
    states.pop(msg.from_user.id, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('ok_'))
def ok_pro(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin emassiz!", show_alert=True); return
    uid = int(call.data[3:])
    c.execute("INSERT OR REPLACE INTO pro VALUES (?)", (uid,))
    conn.commit()
    bot.edit_message_caption(caption=call.message.caption + "\n\n✅ TASDIQLANDI!", chat_id=ADMIN_ID, message_id=call.message.message_id)
    bot.answer_callback_query(call.id, "✅ PRO!")
    try:
        bot.send_message(uid, "🎉 PRO aktiv!")
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith('no_'))
def no_pro(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin emassiz!", show_alert=True); return
    uid = int(call.data[3:])
    bot.edit_message_caption(caption=call.message.caption + "\n\n❌ BEKOR!", chat_id=ADMIN_ID, message_id=call.message.message_id)
    bot.answer_callback_query(call.id, "❌ Bekor!")

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(call):
    states.pop(call.from_user.id, None)
    bot.delete_message(call.from_user.id, call.message.message_id)
    menu(call.from_user.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith('v_'))
def view_kino(call):
    kod = int(call.data[2:])
    c.execute("SELECT * FROM kinolar WHERE kod=?", (kod,))
    k = c.fetchone()
    if k:
        bot.delete_message(call.from_user.id, call.message.message_id)
        cap = k[1] + "\n" + k[2] + "\n⭐" + str(k[3])
        markup = types.InlineKeyboardMarkup()
        if k[6] > 0:
            c.execute("SELECT qism_no FROM qismlar WHERE kod=?", (k[0],))
            for q in c.fetchall():
                markup.add(types.InlineKeyboardButton(str(q[0]) + "-qism", callback_data="w_" + str(k[0]) + "_" + str(q[0])))
        markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
        if k[4] == 'photo':
            bot.send_photo(call.from_user.id, k[5], caption=cap, reply_markup=markup)
        else:
            bot.send_video(call.from_user.id, k[5], caption=cap, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "Oddiy menyu" and m.from_user.id == ADMIN_ID)
def normal(msg):
    bot.send_message(msg.from_user.id, "✅", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: True)
def auto(msg):
    if msg.from_user.id not in states and msg.text and msg.text.isdigit():
        c.execute("SELECT * FROM kinolar WHERE kod=?", (int(msg.text),))
        k = c.fetchone()
        if k:
            cap = k[1] + "\n" + k[2] + "\n⭐" + str(k[3])
            markup = types.InlineKeyboardMarkup()
            if k[6] > 0:
                c.execute("SELECT qism_no FROM qismlar WHERE kod=?", (k[0],))
                for q in c.fetchall():
                    markup.add(types.InlineKeyboardButton(str(q[0]) + "-qism", callback_data="w_" + str(k[0]) + "_" + str(q[0])))
            markup.add(types.InlineKeyboardButton("Orqaga", callback_data="back"))
            if k[4] == 'photo':
                bot.send_photo(msg.from_user.id, k[5], caption=cap, reply_markup=markup)
            else:
                bot.send_video(msg.from_user.id, k[5], caption=cap, reply_markup=markup)

import threading

def run_bot():
    print("Bot ishga tushdi!")
    bot.remove_webhook()
    time.sleep(1)
    bot.polling(none_stop=True)

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=PORT)
