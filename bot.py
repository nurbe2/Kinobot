import telebot
from telebot import types
import sqlite3
import time
import os
from datetime import datetime

# Sozlamalar
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8306639956'))
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@Vexron_stars')
KINO_CHANNEL = os.environ.get('KINO_CHANNEL', '@Vexron_stars')

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
    janr TEXT,
    qoshilgan_sana TEXT,
    korishlar INTEGER DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS qismlar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kino_kod INTEGER,
    qism_raqami INTEGER,
    video_file_id TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS pro_users (
    user_id INTEGER PRIMARY KEY,
    pro_until TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kino_kod INTEGER,
    user_id INTEGER,
    username TEXT,
    matn TEXT,
    sana TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    joined_date TEXT
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kino_kod INTEGER,
    user_id INTEGER,
    rating INTEGER
)''')
conn.commit()

user_states = {}

# ========== OBUNA ==========
def check_sub(uid):
    try:
        s = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return s.status not in ['left', 'kicked']
    except:
        return False

def is_pro(uid):
    cursor.execute("SELECT user_id FROM pro_users WHERE user_id=?", (uid,))
    return cursor.fetchone() is not None

def add_user(uid, first_name, username):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                      (uid, first_name, username, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()

# ========== KINO YUBORISH KANALGA ==========
def send_to_channel(kino):
    try:
        caption = (
            "🎬 <b>YANGI KINO!</b>\n\n"
            f"🎬 <b>{kino[1]}</b>\n"
            f"📝 {kino[2][:200]}...\n"
            f"⭐ {kino[3]}/10\n"
            f"📂 {kino[7]}\n"
            f"🔢 Kod: <code>{kino[0]}</code>\n"
            f"📹 Qismlar: {kino[6]}"
        )
        
        if kino[4] == 'photo':
            bot.send_photo(KINO_CHANNEL, kino[5], caption=caption)
        else:
            bot.send_video(KINO_CHANNEL, kino[5], caption=caption)
        return True
    except Exception as e:
        print(f"Kanalga yuborish xatosi: {e}")
        return False

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    user_states.pop(uid, None)
    add_user(uid, msg.from_user.first_name, msg.from_user.username)
    
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
        types.InlineKeyboardButton("🔎 Nomi orqali qidirish", callback_data="search_name"),
        types.InlineKeyboardButton("📂 Janr orqali qidirish", callback_data="search_genre"),
        types.InlineKeyboardButton("⭐ TOP Reyting", callback_data="top_rating"),
        types.InlineKeyboardButton("🔥 Eng ko'p ko'rilgan", callback_data="top_views"),
        types.InlineKeyboardButton("🎬 NexMovie Pro", callback_data="nexmovie_pro"),
        types.InlineKeyboardButton("📊 Statistika", callback_data="stats")
    )
    bot.send_message(uid, f"🎬 Xush kelibsiz!\n👤 {p}", reply_markup=markup)

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=['admin'])
def admin(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        bot.send_message(uid, "❌ Admin emassiz!")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎬 Kino qo'shish", "📹 Qism qo'shish")
    markup.add("📋 Kinolar ro'yxati", "📊 To'liq statistika")
    markup.add("⬅️ Oddiy menyu")
    bot.send_message(uid, "👑 Admin Panel", reply_markup=markup)

# ========== KINO QO'SHISH ==========
@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and m.from_user.id == ADMIN_ID)
def add_kino(msg):
    uid = msg.from_user.id
    user_states[uid] = {'step': 'kod', 'data': {}}
    bot.send_message(uid, "Kino kodini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kod')
def step_kod(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!")
        return
    
    user_states[uid]['data']['kod'] = int(msg.text)
    user_states[uid]['step'] = 'nomi'
    bot.send_message(uid, "Kino nomini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'nomi')
def step_nomi(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    user_states[uid]['data']['nomi'] = msg.text
    user_states[uid]['step'] = 'tavsif'
    bot.send_message(uid, "Tavsifni kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'tavsif')
def step_tavsif(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    user_states[uid]['data']['tavsif'] = msg.text
    user_states[uid]['step'] = 'reyting'
    bot.send_message(uid, "Reyting (1-10):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'reyting')
def step_reyting(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    try:
        r = float(msg.text)
        if r < 1 or r > 10:
            bot.send_message(uid, "1-10 gacha!")
            return
    except:
        bot.send_message(uid, "Raqam kiriting!")
        return
    
    user_states[uid]['data']['reyting'] = r
    user_states[uid]['step'] = 'media'
    bot.send_message(uid, "Rasm yoki video yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'media',
                     content_types=['photo', 'video', 'text'])
def step_media(msg):
    uid = msg.from_user.id
    if msg.text and msg.text == '/cancel':
        cancel(msg)
        return
    
    if msg.photo:
        user_states[uid]['data']['media_type'] = 'photo'
        user_states[uid]['data']['file_id'] = msg.photo[-1].file_id
    elif msg.video:
        user_states[uid]['data']['media_type'] = 'video'
        user_states[uid]['data']['file_id'] = msg.video.file_id
    else:
        bot.send_message(uid, "Rasm yoki video yuboring!")
        return
    
    user_states[uid]['step'] = 'qismlar'
    bot.send_message(uid, "Qismlar soni (0 ham mumkin):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qismlar')
def step_qismlar(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!")
        return
    
    user_states[uid]['data']['qismlar'] = int(msg.text)
    user_states[uid]['step'] = 'janr'
    bot.send_message(uid, "Janrlar (vergul bilan):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'janr')
def step_janr(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    
    d = user_states[uid]['data']
    sana = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    cursor.execute('''INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                   (d['kod'], d['nomi'], d['tavsif'], d['reyting'],
                    d['media_type'], d['file_id'], d['qismlar'], msg.text, sana, 0))
    conn.commit()
    
    # Kanalga yuborish
    kino = (d['kod'], d['nomi'], d['tavsif'], d['reyting'],
            d['media_type'], d['file_id'], d['qismlar'], msg.text)
    send_to_channel(kino)
    
    bot.send_message(uid, f"✅ {d['nomi']} qo'shildi va kanalga yuborildi!")
    user_states.pop(uid, None)
    admin(msg)

# ========== QISM QO'SHISH ==========
@bot.message_handler(func=lambda m: m.text == "📹 Qism qo'shish" and m.from_user.id == ADMIN_ID)
def add_qism(msg):
    uid = msg.from_user.id
    user_states[uid] = {'step': 'qkod', 'data': {}}
    bot.send_message(uid, "Kino kodini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qkod')
def step_qkod(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!")
        return
    
    kod = int(msg.text)
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (kod,))
    k = cursor.fetchone()
    if not k:
        bot.send_message(uid, "Topilmadi!")
        return
    
    user_states[uid]['data'] = {'kod': kod, 'max': k[6], 'nomi': k[1]}
    user_states[uid]['step'] = 'qraqam'
    bot.send_message(uid, f"Nechinchi qism? (1-{k[6]}):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qraqam')
def step_qraqam(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        cancel(msg)
        return
    if not msg.text.isdigit():
        bot.send_message(uid, "Raqam kiriting!")
        return
    
    q = int(msg.text)
    if q < 1 or q > user_states[uid]['data']['max']:
        bot.send_message(uid, f"1 dan {user_states[uid]['data']['max']} gacha!")
        return
    
    user_states[uid]['data']['qism'] = q
    user_states[uid]['step'] = 'qvideo'
    bot.send_message(uid, f"{q}-qism videosini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qvideo',
                     content_types=['video', 'text'])
def step_qvideo(msg):
    uid = msg.from_user.id
    if msg.text and msg.text == '/cancel':
        cancel(msg)
        return
    if not msg.video:
        bot.send_message(uid, "Video yuboring!")
        return
    
    d = user_states[uid]['data']
    cursor.execute("INSERT INTO qismlar (kino_kod, qism_raqami, video_file_id) VALUES (?, ?, ?)",
                   (d['kod'], d['qism'], msg.video.file_id))
    conn.commit()
    
    bot.send_message(uid, f"✅ {d['qism']}-qism qo'shildi!")
    user_states.pop(uid, None)
    admin(msg)

# ========== KOD ORQALI QIDIRISH ==========
@bot.callback_query_handler(func=lambda c: c.data == "search_code")
def search_code(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True)
        return
    
    user_states[uid] = {'step': 'search'}
    bot.send_message(uid, "Kino kodini kiriting:")

# ========== NOMI ORQALI QIDIRISH ==========
@bot.callback_query_handler(func=lambda c: c.data == "search_name")
def search_name(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True)
        return
    
    user_states[uid] = {'step': 'search_name'}
    bot.send_message(uid, "Kino nomini kiriting:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'search_name')
def show_kino_name(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        user_states.pop(uid, None)
        show_menu(uid)
        return
    
    nomi = msg.text.strip()
    cursor.execute("SELECT * FROM kinolar WHERE kino_nomi LIKE ?", (f'%{nomi}%',))
    kinolar = cursor.fetchall()
    
    if not kinolar:
        bot.send_message(uid, "❌ Topilmadi!")
        user_states.pop(uid, None)
        return
    
    user_states.pop(uid, None)
    
    if len(kinolar) == 1:
        send_kino_info(uid, kinolar[0])
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for k in kinolar:
            markup.add(types.InlineKeyboardButton(
                f"🎬 {k[1]} (⭐{k[3]})",
                callback_data=f"v_{k[0]}"
            ))
        markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
        bot.send_message(uid, f"'{nomi}' bo'yicha topildi:", reply_markup=markup)

# ========== KINO KO'RSATISH ==========
def send_kino_info(uid, k, increase_view=True):
    if increase_view:
        cursor.execute("UPDATE kinolar SET korishlar = korishlar + 1 WHERE kino_kod=?", (k[0],))
        conn.commit()
    
    cap = (
        f"🎬 <b>{k[1]}</b>\n\n"
        f"📝 {k[2]}\n"
        f"⭐ {k[3]}/10\n"
        f"📂 {k[7]}\n"
        f"🔢 Kod: <code>{k[0]}</code>\n"
        f"📹 Qismlar: {k[6]}\n"
        f"👁 Ko'rilgan: {k[9]}\n"
        f"📅 Qo'shilgan: {k[8]}"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    
    # Reyting tugmalari
    markup.add(
        types.InlineKeyboardButton("⭐1", callback_data=f"rate_{k[0]}_1"),
        types.InlineKeyboardButton("⭐2", callback_data=f"rate_{k[0]}_2"),
        types.InlineKeyboardButton("⭐3", callback_data=f"rate_{k[0]}_3"),
        types.InlineKeyboardButton("⭐4", callback_data=f"rate_{k[0]}_4"),
        types.InlineKeyboardButton("⭐5", callback_data=f"rate_{k[0]}_5")
    )
    
    if k[6] > 0:
        cursor.execute("SELECT qism_raqami FROM qismlar WHERE kino_kod=? ORDER BY qism_raqami", (k[0],))
        for q in cursor.fetchall():
            markup.add(types.InlineKeyboardButton(f"📹 {q[0]}-qism", callback_data=f"w_{k[0]}_{q[0]}"))
    
    markup.add(
        types.InlineKeyboardButton("💬 Fikr bildirish", callback_data=f"review_{k[0]}"),
        types.InlineKeyboardButton("📋 Fikrlar", callback_data=f"reviews_{k[0]}")
    )
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    
    if k[4] == 'photo':
        bot.send_photo(uid, k[5], caption=cap, reply_markup=markup)
    else:
        bot.send_video(uid, k[5], caption=cap, reply_markup=markup)

# ========== REYTING BOSISH ==========
@bot.callback_query_handler(func=lambda c: c.data.startswith('rate_'))
def rate_kino(call):
    uid = call.from_user.id
    parts = call.data.split('_')
    kod = int(parts[1])
    rating = int(parts[2])
    
    cursor.execute("SELECT id FROM ratings WHERE kino_kod=? AND user_id=?", (kod, uid))
    if cursor.fetchone():
        cursor.execute("UPDATE ratings SET rating=? WHERE kino_kod=? AND user_id=?", (rating, kod, uid))
    else:
        cursor.execute("INSERT INTO ratings (kino_kod, user_id, rating) VALUES (?, ?, ?)", (kod, uid, rating))
    conn.commit()
    
    cursor.execute("SELECT AVG(rating) FROM ratings WHERE kino_kod=?", (kod,))
    avg = cursor.fetchone()[0]
    cursor.execute("UPDATE kinolar SET reyting=? WHERE kino_kod=?", (round(avg, 1), kod))
    conn.commit()
    
    bot.answer_callback_query(call.id, f"⭐ {rating} baholandingiz!")

# ========== FIKR BILDIRISH ==========
@bot.callback_query_handler(func=lambda c: c.data.startswith('review_') and not c.data.startswith('reviews_'))
def review_start(call):
    uid = call.from_user.id
    kod = int(call.data.split('_')[1])
    user_states[uid] = {'step': 'review', 'kod': kod}
    bot.answer_callback_query(call.id)
    bot.send_message(uid, "💬 Fikringizni yozing:")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'review')
def save_review(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        user_states.pop(uid, None)
        show_menu(uid)
        return
    
    kod = user_states[uid]['kod']
    username = f"@{msg.from_user.username}" if msg.from_user.username else msg.from_user.first_name
    
    cursor.execute("INSERT INTO reviews (kino_kod, user_id, username, matn, sana) VALUES (?, ?, ?, ?, ?)",
                   (kod, uid, username, msg.text, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    
    bot.send_message(uid, "✅ Fikringiz qabul qilindi!")
    user_states.pop(uid, None)

# ========== FIKRLARNI KO'RISH ==========
@bot.callback_query_handler(func=lambda c: c.data.startswith('reviews_'))
def show_reviews(call):
    uid = call.from_user.id
    kod = int(call.data.split('_')[1])
    
    cursor.execute("SELECT * FROM reviews WHERE kino_kod=? ORDER BY id DESC LIMIT 10", (kod,))
    reviews = cursor.fetchall()
    
    if not reviews:
        bot.answer_callback_query(call.id, "❌ Fikrlar yo'q!", show_alert=True)
        return
    
    text = "<b>💬 Fikrlar:</b>\n\n"
    for r in reviews:
        text += f"👤 {r[3]}: {r[4]}\n📅 {r[5]}\n➖➖➖➖➖\n"
    
    bot.send_message(uid, text)

# ========== QISMNI KO'RISH ==========
@bot.callback_query_handler(func=lambda c: c.data.startswith('w_'))
def watch(call):
    _, kod, qism = call.data.split('_')
    cursor.execute("SELECT video_file_id FROM qismlar WHERE kino_kod=? AND qism_raqami=?", (int(kod), int(qism)))
    r = cursor.fetchone()
    if r:
        bot.send_video(call.from_user.id, r[0], caption=f"📹 {qism}-qism")
        bot.answer_callback_query(call.id, "✅ Yuborildi!")

# ========== JANR ORQALI ==========
@bot.callback_query_handler(func=lambda c: c.data == "search_genre")
def genre(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Obuna bo'ling!", show_alert=True)
        return
    
    cursor.execute("SELECT DISTINCT janr FROM kinolar")
    janrlar = set()
    for row in cursor.fetchall():
        if row[0]:
            for j in row[0].split(','):
                if j.strip():
                    janrlar.add(j.strip())
    
    if not janrlar:
        bot.answer_callback_query(call.id, "Kinolar yo'q!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for j in sorted(janrlar):
        markup.add(types.InlineKeyboardButton(f"📂 {j}", callback_data=f"g_{j}"))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back"))
    
    bot.edit_message_text("Janrni tanlang:", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('g_'))
def show_genre(call):
    uid = call.from_user.id
    ja
