import telebot
from telebot import types
import sqlite3
import time
import os

# Sozlamalar
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8306639956'))
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@Vexron_stars')

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# SQLite
conn = sqlite3.connect('kino_bot.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS kinolar (
    kino_kod INTEGER PRIMARY KEY,
    kino_nomi TEXT,
    tavsif TEXT,
    reyting REAL,
    media_type TEXT,
    media_file_id TEXT,
    qismlar_soni INTEGER,
    janr TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS qismlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kino_kod INTEGER,
    qism_raqami INTEGER,
    video_file_id TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS pro_users (
    user_id INTEGER PRIMARY KEY
)''')
conn.commit()

user_states = {}

def check_sub(uid):
    try:
        s = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return s.status not in ['left', 'kicked']
    except:
        return False

def is_pro(uid):
    cursor.execute("SELECT user_id FROM pro_users WHERE user_id=?", (uid,))
    return cursor.fetchone() is not None

@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    user_states.pop(uid, None)
    
    if not check_sub(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            f"📢 Kanalga obuna bo'lish",
            url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
        ))
        markup.add(types.InlineKeyboardButton(
            "✅ Tekshirish",
            callback_data="check_sub"
        ))
        bot.send_message(uid,
            f"👋 Salom!\n\n{CHANNEL_USERNAME} kanaliga obuna bo'ling.",
            reply_markup=markup
        )
        return
    show_menu(uid)

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_cb(call):
    uid = call.from_user.id
    if check_sub(uid):
        bot.delete_message(uid, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ Tasdiqlandi!")
        show_menu(uid)
    else:
        bot.answer_callback_query(call.id, "❌ Obuna bo'lmagansiz!", show_alert=True)

def show_menu(uid):
    p = "✅ PRO" if is_pro(uid) else "❌ Oddiy"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 Kod orqali qidirish", callback_data="search_code"),
        types.InlineKeyboardButton("📂 Janr orqali qidirish", callback_data="search_genre"),
        types.InlineKeyboardButton("🎬 NexMovie Pro", callback_data="nexmovie_pro")
    )
    bot.send_message(uid, f"🎬 Xush kelibsiz!\n👤 {p}", reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, "❌ Admin emassiz!"); return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎬 Kino qo'shish", "📹 Qism qo'shish")
    markup.add("⬅️ Oddiy menyu")
    bot.send_message(uid, "👑 Admin Panel", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and m.from_user.id == ADMIN_ID)
def add_kino(msg):
    uid = msg.from_user.id
    user_states[uid] = {'step': 'kod', 'data': {}}
    bot.send_message(uid, "Kino kodini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kod')
def step_kod(msg):
    uid = msg.from_user.id
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    user_states[uid]['data']['kod'] = int(msg.text)
    user_states[uid]['step'] = 'nomi'
    bot.send_message(uid, "Kino nomini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'nomi')
def step_nomi(msg):
    uid = msg.from_user.id
    user_states[uid]['data']['nomi'] = msg.text
    user_states[uid]['step'] = 'tavsif'
    bot.send_message(uid, "Tavsifni kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'tavsif')
def step_tavsif(msg):
    uid = msg.from_user.id
    user_states[uid]['data']['tavsif'] = msg.text
    user_states[uid]['step'] = 'reyting'
    bot.send_message(uid, "Reyting (1-10):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'reyting')
def step_reyting(msg):
    uid = msg.from_user.id
    try:
        r = float(msg.text)
        if r < 1 or r > 10:
            bot.send_message(uid, "1-10 gacha!"); return
    except:
        bot.send_message(uid, "Raqam kiriting!"); return
    
    user_states[uid]['data']['reyting'] = r
    user_states[uid]['step'] = 'media'
    bot.send_message(uid, "Rasm yoki video yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'media',
                     content_types=['photo', 'video', 'text'])
def step_media(msg):
    uid = msg.from_user.id
    if msg.photo:
        user_states[uid]['data']['media_type'] = 'photo'
        user_states[uid]['data']['file_id'] = msg.photo[-1].file_id
    elif msg.video:
        user_states[uid]['data']['media_type'] = 'video'
        user_states[uid]['data']['file_id'] = msg.video.file_id
    else:
        bot.send_message(uid, "Rasm yoki video yuboring!"); return
    
    user_states[uid]['step'] = 'qismlar'
    bot.send_message(uid, "Qismlar soni (0 ham mumkin):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qismlar')
def step_qismlar(msg):
    uid = msg.from_user.id
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!"); return
    
    user_states[uid]['data']['qismlar'] = int(msg.text)
    user_states[uid]['step'] = 'janr'
    bot.send_message(uid, "Janrlar (vergul bilan):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'janr')
def step_janr(msg):
    uid = msg.from_user.id
    d = user_states[uid]['data']
    
    cursor.execute('''INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (d['kod'], d['nomi'], d['tavsif'], d['reyting'],
                    d['media_type'], d['file_id'], d['qismlar'], msg.text))
    conn.commit()
    
    bot.send_message(uid, f"✅ {d['nomi']} qo'shildi!")
    user_states.pop(uid, None)
    admin(msg)

@bot.message_handler(func=lambda m: m.text == "📹 Qism qo'shish" and m.from_user.id == ADMIN_ID)
def add_qism(msg):
    uid = msg.from_user.id
    user_states[uid] = {'step': 'qkod', 'data': {}}
    bot.send_message(uid, "Kino kodini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qkod')
def step_qkod(msg):
    uid = msg.from_user.id
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!"); return
    
    kod = int(msg.text)
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (kod,))
    k = cursor.fetchone()
    if not k:
        bot.send_message(uid, "Topilmadi!"); return
    
    user_states[uid]['data'] = {'kod': kod, 'max': k[6], 'nomi': k[1]}
    user_states[uid]['step'] = 'qraqam'
    bot.send_message(uid, f"Nechinchi qism? (1-{k[6]}):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qraqam')
def step_qraqam(msg):
    uid = msg.from_user.id
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!"); return
    
    q = int(msg.text)
    if q < 1 or q > user_states[uid]['data']['max']:
        bot.send_message(uid, f"1 dan {user_states[uid]['data']['max']} gacha!"); return
    
    user_states[uid]['data']['qism'] = q
    user_states[uid]['step'] = 'qvideo'
    bot.send_message(uid, f"{q}-qism videosini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qvideo',
                     content_types=['video', 'text'])
def step_qvideo(msg):
    uid = msg.from_user.id
    if not msg.video:
        bot.send_message(uid, "Video yuboring!"); return
    
    d = user_states[uid]['data']
    cursor.execute("INSERT INTO qismlar (kino_kod, qism_raqami, video_file_id) VALUES (?, ?, ?)",
                   (d['kod'], d['qism'], msg.video.file_id))
    conn.commit()
    
    bot.send_message(uid, f"✅ {d['qism']}-qism qo'shildi!")
    user_states.pop(uid, None)
    admin(msg)

@bot.callback_query_handler(func=lambda c: c.data == "search_code")
def search_code(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    
    user_states[uid] = {'step': 'search'}
    bot.send_message(uid, "Kino kodini kiriting:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'search')
def show_kino(msg):
    uid = msg.from_user.id
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!"); return
    
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (int(msg.text),))
    k = cursor.fetchone()
    
    if not k:
        bot.send_message(uid, "Topilmadi!")
        user_states.pop(uid, None); return
    
    user_states.pop(uid, None)
    
    cap = f"🎬 {k[1]}\n📝 {k[2]}\n⭐ {k[3]}/10\n📂 {k[7]}\n🔢 {k[0]}\n📹 {k[6]}"
    markup = types.InlineKeyboardMarkup()
    
    if k[6] > 0:
        cursor.execute("SELECT qism_raqami FROM qismlar WHERE kino_kod=? ORDER BY qism_raqami", (k[0],))
        for q in cursor.fetchall():
            markup.add(types.InlineKeyboardButton(f"📹 {q[0]}-qism", callback_data=f"w_{k[0]}_{q[0]}"))
    
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    
    if k[4] == 'photo':
        bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
    else:
        bot.send_video(uid, k[5], caption=cap, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('w_'))
def watch(call):
    _, kod, qism = call.data.split('_')
    cursor.execute("SELECT video_file_id FROM qismlar WHERE kino_kod=? AND qism_raqami=?", (int(kod), int(qism)))
    r = cursor.fetchone()
    if r:
        bot.send_video(call.from_user.id, r[0], caption=f"📹 {qism}-qism")
        bot.answer_callback_query(call.id, "✅ Yuborildi!")

@bot.callback_query_handler(func=lambda c: c.data == "search_genre")
def genre(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    
    cursor.execute("SELECT DISTINCT janr FROM kinolar")
    janrlar = set()
    for row in cursor.fetchall():
        if row[0]:
            for j in row[0].split(','):
                if j.strip():
                    janrlar.add(j.strip())
    
    if not janrlar:
        bot.answer_callback_query(call.id, "Kinolar yo'q!", show_alert=True); return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for j in sorted(janrlar):
        markup.add(types.InlineKeyboardButton(f"📂 {j}", callback_data=f"g_{j}"))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    
    bot.edit_message_text("Janrni tanlang:", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('g_'))
def show_genre(call):
    uid = call.from_user.id
    janr = call.data[2:]
    
    cursor.execute("SELECT * FROM kinolar WHERE janr LIKE ?", (f'%{janr}%',))
    kinolar = cursor.fetchall()
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k in kinolar:
        markup.add(types.InlineKeyboardButton(f"🎬 {k[1]} (⭐{k[3]})", callback_data=f"v_{k[0]}"))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="search_genre"))
    
    bot.edit_message_text(f"'{janr}' janridagi kinolar:", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('v_'))
def view_kino(call):
    uid = call.from_user.id
    kod = int(call.data[2:])
    
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (kod,))
    k = cursor.fetchone()
    
    if k:
        bot.delete_message(uid, call.message.message_id)
        cap = f"🎬 {k[1]}\n📝 {k[2]}\n⭐ {k[3]}/10\n📂 {k[7]}\n🔢 {k[0]}"
        markup = types.InlineKeyboardMarkup()
        if k[6] > 0:
            cursor.execute("SELECT qism_raqami FROM qismlar WHERE kino_kod=?", (k[0],))
            for q in cursor.fetchall():
                markup.add(types.InlineKeyboardButton(f"📹 {q[0]}-qism", callback_data=f"w_{k[0]}_{q[0]}"))
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
        
        if k[4] == 'photo':
            bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
        else:
            bot.send_video(uid, k[5], caption=cap, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "nexmovie_pro")
def pro(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True); return
    
    if is_pro(uid):
        bot.answer_callback_query(call.id, "✅ Siz PROsiz!", show_alert=True); return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 To'lov qildim", callback_data="pay"))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    
    bot.edit_message_text(
        "💎 NexMovie Pro\n\n"
        "💰 14.000 so'm\n"
        "💳 VISA: 4916 9903 1619 3280\n\n"
        "To'lov qilib, chekni yuboring!",
        uid, call.message.message_id, reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == "pay")
def pay(call):
    uid = call.from_user.id
    user_states[uid] = {'step': 'check'}
    bot.answer_callback_query(call.id)
    bot.send_message(uid, "Chek rasmini yuboring:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'check',
                     content_types=['photo'])
def get_check(msg):
    uid = msg.from_user.id
    file_id = msg.photo[-1].file_id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ok_{uid}"),
        types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"no_{uid}")
    )
    
    bot.send_photo(ADMIN_ID, file_id,
        caption=f"📩 To'lov cheki!\n👤 {msg.from_user.first_name}\n🆔 {uid}\n💰 14.000 so'm",
        reply_markup=markup
    )
    
    bot.send_message(uid, "✅ Chek yuborildi! Admin tekshiradi.")
    user_states.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith('ok_'))
def ok_pro(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin emassiz!", show_alert=True); return
    
    uid = int(call.data[3:])
    cursor.execute("INSERT OR REPLACE INTO pro_users VALUES (?)", (uid,))
    conn.commit()
    
    bot.edit_message_caption(
        caption=call.message.caption + "\n\n✅ TASDIQLANDI!",
        chat_id=ADMIN_ID, message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id, "✅ PRO berildi!")
    
    try:
        bot.send_message(uid, "🎉 Tabriklaymiz! Siz PRO foydalanuvchisiz!")
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith('no_'))
def no_pro(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin emassiz!", show_alert=True); return
    
    uid = int(call.data[3:])
    
    bot.edit_message_caption(
        caption=call.message.caption + "\n\n❌ BEKOR QILINDI!",
        chat_id=ADMIN_ID, message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id, "❌ Bekor qilindi!")
    
    try:
        bot.send_message(uid, "❌ So'rovingiz bekor qilindi!")
    except:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "back")
def back(call):
    uid = call.from_user.id
    user_states.pop(uid, None)
    bot.delete_message(uid, call.message.message_id)
    show_menu(uid)

@bot.message_handler(func=lambda m: m.text == "⬅️ Oddiy menyu" and m.from_user.id == ADMIN_ID)
def normal(msg):
    uid = msg.from_user.id
    markup = types.ReplyKeyboardRemove()
    bot.send_message(uid, "✅ Oddiy menyu", reply_markup=markup)

@bot.message_handler(commands=['cancel'])
def cancel(msg):
    uid = msg.from_user.id
    user_states.pop(uid, None)
    bot.send_message(uid, "❌ Bekor qilindi!")

@bot.message_handler(func=lambda m: True)
def auto(msg):
    uid = msg.from_user.id
    if uid not in user_states and msg.text and msg.text.isdigit():
        cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (int(msg.text),))
        k = cursor.fetchone()
        if k:
            cap = f"🎬 {k[1]}\n📝 {k[2]}\n⭐ {k[3]}/10\n📂 {k[7]}"
            markup = types.InlineKeyboardMarkup()
            if k[6] > 0:
                cursor.execute("SELECT qism_raqami FROM qismlar WHERE kino_kod=?", (k[0],))
                for q in cursor.fetchall():
                    markup.add(types.InlineKeyboardButton(f"📹 {q[0]}-qism", callback_data=f"w_{k[0]}_{q[0]}"))
            markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
            
            if k[4] == 'photo':
                bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
            else:
                bot.send_video(uid, k[5], caption=cap, reply_markup=markup)
            return

# ========== ISHGA TUSHIRISH ==========
print("🤖 Bot ishga tushdi!")
bot.remove_webhook()
time.sleep(1)
bot.polling(none_stop=True)
