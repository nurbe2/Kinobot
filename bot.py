import telebot
from telebot import types
import sqlite3
import time
import os
from flask import Flask, request

# ========== SOZLAMALAR ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '8306639956'))
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@Vexron_stars')
PORT = int(os.environ.get('PORT', 5000))
TOLOV_SUMMASI = "14.000 so'm"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')
app = Flask(__name__)

# SQLite baza
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
    user_id INTEGER PRIMARY KEY,
    pro_until TEXT
)''')
conn.commit()

user_states = {}

# ========== FLASK ROUTES ==========
@app.route('/')
def home():
    return "🤖 Bot ishlamoqda!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Bad Request', 403

# ========== OBUNA TEKSHIRISH ==========
def check_sub(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return status.status not in ['left', 'kicked']
    except:
        return False

def is_pro(user_id):
    cursor.execute("SELECT pro_until FROM pro_users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

# ========== START ==========
@bot.message_handler(commands=['start'])
def start(msg):
    uid = msg.from_user.id
    user_states.pop(uid, None)
    
    if not check_sub(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            f"📢 {CHANNEL_USERNAME} kanaliga obuna bo'lish",
            url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
        ))
        markup.add(types.InlineKeyboardButton(
            "✅ Obunani tekshirish",
            callback_data="check_sub"
        ))
        bot.send_message(uid,
            f"👋 <b>Assalomu alaykum!</b>\n\n"
            f"Botdan foydalanish uchun <b>{CHANNEL_USERNAME}</b> kanaliga obuna bo'ling.\n\n"
            "Obuna bo'lgach, <b>✅ Obunani tekshirish</b> tugmasini bosing.",
            reply_markup=markup
        )
        return
    
    show_menu(uid)

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub_callback(call):
    uid = call.from_user.id
    if check_sub(uid):
        bot.delete_message(uid, call.message.message_id)
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
        show_menu(uid)
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali obuna bo'lmadingiz!", show_alert=True)

# ========== ASOSIY MENYU ==========
def show_menu(uid):
    pro_status = "✅ PRO" if is_pro(uid) else "❌ Oddiy"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🔍 Kod orqali kino qidirish", callback_data="search_code"),
        types.InlineKeyboardButton("📂 Janr orqali qidirish", callback_data="search_genre"),
        types.InlineKeyboardButton("🎬 NexMovie Pro", callback_data="nexmovie_pro")
    )
    bot.send_message(uid,
        f"<b>🎬 Xush kelibsiz!</b>\n\n"
        f"👤 Holat: {pro_status}\n\n"
        "Kinoni qidirish usulini tanlang:",
        reply_markup=markup
    )

# ========== ADMIN PANEL ==========
@bot.message_handler(commands=['admin'])
def admin_panel(msg):
    uid = msg.from_user.id
    user_states.pop(uid, None)
    
    if uid != ADMIN_ID:
        bot.send_message(uid, "❌ Siz admin emassiz!")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎬 Kino qo'shish", "📹 Qism qo'shish")
    markup.add("📋 Kinolar ro'yxati", "🗑 Kino o'chirish")
    markup.add("👑 PRO foydalanuvchilar", "⬅️ Oddiy menyu")
    
    bot.send_message(uid,
        "<b>👑 Admin Panel</b>\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=markup
    )

# ========== KINO QO'SHISH ==========
@bot.message_handler(func=lambda m: m.text == "🎬 Kino qo'shish" and m.from_user.id == ADMIN_ID)
def add_kino_start(msg):
    uid = msg.from_user.id
    user_states[uid] = {'step': 'kino_kod', 'data': {}}
    bot.send_message(uid,
        "<b>🎬 Kino qo'shish</b>\n\n"
        "Kino kodini kiriting (raqam):\n"
        "Bekor qilish uchun /cancel"
    )

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_kod')
def kino_kod(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    kod = int(msg.text)
    cursor.execute("SELECT kino_kod FROM kinolar WHERE kino_kod=?", (kod,))
    if cursor.fetchone():
        bot.send_message(uid, "❌ Bu kod band! Boshqa kod kiriting:"); return
    
    user_states[uid]['data']['kod'] = kod
    user_states[uid]['step'] = 'kino_nomi'
    bot.send_message(uid, "✅ Kino nomini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_nomi')
def kino_nomi(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    user_states[uid]['data']['nomi'] = msg.text
    user_states[uid]['step'] = 'kino_tavsif'
    bot.send_message(uid, "✅ Kino tavsifini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_tavsif')
def kino_tavsif(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    user_states[uid]['data']['tavsif'] = msg.text
    user_states[uid]['step'] = 'kino_reyting'
    bot.send_message(uid, "✅ Reytingni kiriting (1-10):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_reyting')
def kino_reyting(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    try:
        reyting = float(msg.text)
        if reyting < 1 or reyting > 10:
            bot.send_message(uid, "❌ 1 dan 10 gacha!"); return
    except:
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    user_states[uid]['data']['reyting'] = reyting
    user_states[uid]['step'] = 'kino_media'
    bot.send_message(uid, "✅ Rasm yoki video yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_media',
                     content_types=['photo', 'video', 'text'])
def kino_media(msg):
    uid = msg.from_user.id
    if msg.text and msg.text == '/cancel': cancel(msg); return
    
    if msg.photo:
        user_states[uid]['data']['media_type'] = 'photo'
        user_states[uid]['data']['file_id'] = msg.photo[-1].file_id
    elif msg.video:
        user_states[uid]['data']['media_type'] = 'video'
        user_states[uid]['data']['file_id'] = msg.video.file_id
    else:
        bot.send_message(uid, "❌ Rasm yoki video yuboring!"); return
    
    user_states[uid]['step'] = 'kino_qismlar'
    bot.send_message(uid, "✅ Qismlar sonini kiriting (0 ham mumkin):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_qismlar')
def kino_qismlar(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    user_states[uid]['data']['qismlar'] = int(msg.text)
    user_states[uid]['step'] = 'kino_janr'
    bot.send_message(uid, "✅ Janrlarni kiriting (vergul bilan ajrating):\nMisol: Jangari, Komediya, Drama")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'kino_janr')
def kino_janr(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    
    d = user_states[uid]['data']
    cursor.execute('''INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (d['kod'], d['nomi'], d['tavsif'], d['reyting'],
                    d['media_type'], d['file_id'], d['qismlar'], msg.text))
    conn.commit()
    
    bot.send_message(uid,
        f"<b>✅ Kino muvaffaqiyatli qo'shildi!</b>\n\n"
        f"🎬 Nomi: {d['nomi']}\n"
        f"🔢 Kod: <code>{d['kod']}</code>\n"
        f"⭐ Reyting: {d['reyting']}\n"
        f"📹 Qismlar: {d['qismlar']}\n"
        f"📂 Janr: {msg.text}"
    )
    user_states.pop(uid, None)
    time.sleep(1)
    admin_panel(msg)

# ========== QISM QO'SHISH ==========
@bot.message_handler(func=lambda m: m.text == "📹 Qism qo'shish" and m.from_user.id == ADMIN_ID)
def qism_start(msg):
    uid = msg.from_user.id
    user_states[uid] = {'step': 'qism_kod', 'data': {}}
    bot.send_message(uid, "<b>📹 Qism qo'shish</b>\n\nKino kodini kiriting:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qism_kod')
def qism_kod(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    kod = int(msg.text)
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (kod,))
    kino = cursor.fetchone()
    
    if not kino:
        bot.send_message(uid, "❌ Kino topilmadi!"); return
    
    user_states[uid]['data']['kod'] = kod
    user_states[uid]['data']['max_qism'] = kino[6]
    user_states[uid]['data']['nomi'] = kino[1]
    user_states[uid]['step'] = 'qism_raqam'
    
    bot.send_message(uid,
        f"✅ Kino: <b>{kino[1]}</b>\n"
        f"📹 Maksimal qism: <b>{kino[6]}</b>\n\n"
        f"Nechinchi qismni qo'shasiz? (1-{kino[6]}):"
    )

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qism_raqam')
def qism_raqam(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel': cancel(msg); return
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    qism = int(msg.text)
    max_q = user_states[uid]['data']['max_qism']
    
    if qism < 1 or qism > max_q:
        bot.send_message(uid, f"❌ 1 dan {max_q} gacha kiriting!"); return
    
    kod = user_states[uid]['data']['kod']
    cursor.execute("SELECT id FROM qismlar WHERE kino_kod=? AND qism_raqami=?", (kod, qism))
    if cursor.fetchone():
        bot.send_message(uid, f"❌ {qism}-qism allaqachon qo'shilgan!"); return
    
    user_states[uid]['data']['qism'] = qism
    user_states[uid]['step'] = 'qism_video'
    bot.send_message(uid, f"✅ {qism}-qism videosini yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and 
                     user_states.get(m.from_user.id, {}).get('step') == 'qism_video',
                     content_types=['video', 'text'])
def qism_video(msg):
    uid = msg.from_user.id
    if msg.text and msg.text == '/cancel': cancel(msg); return
    if not msg.video:
        bot.send_message(uid, "❌ Video yuboring!"); return
    
    d = user_states[uid]['data']
    cursor.execute("INSERT INTO qismlar (kino_kod, qism_raqami, video_file_id) VALUES (?, ?, ?)",
                   (d['kod'], d['qism'], msg.video.file_id))
    conn.commit()
    
    bot.send_message(uid,
        f"✅ <b>{d['nomi']}</b> kinosining <b>{d['qism']}-qismi</b> qo'shildi!\n"
        f"🔢 Kino kodi: <code>{d['kod']}</code>"
    )
    user_states.pop(uid, None)
    time.sleep(1)
    admin_panel(msg)

# ========== KOD ORQALI QIDIRISH ==========
@bot.callback_query_handler(func=lambda c: c.data == "search_code")
def search_code(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval obuna bo'ling!", show_alert=True); return
    
    user_states[uid] = {'step': 'search'}
    bot.send_message(uid, "<b>🔍 Kino kodini kiriting:</b>\nBekor qilish uchun /cancel")

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'search')
def show_kino(msg):
    uid = msg.from_user.id
    if msg.text == '/cancel':
        user_states.pop(uid, None)
        show_menu(uid); return
    
    if not msg.text.isdigit():
        bot.send_message(uid, "❌ Raqam kiriting!"); return
    
    kod = int(msg.text)
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (kod,))
    kino = cursor.fetchone()
    
    if not kino:
        bot.send_message(uid, "❌ Topilmadi!")
        user_states.pop(uid, None); return
    
    user_states.pop(uid, None)
    send_kino(uid, kino)

def send_kino(uid, kino):
    caption = (
        f"🎬 <b>{kino[1]}</b>\n\n"
        f"📝 <b>Tavsif:</b> {kino[2]}\n"
        f"⭐ <b>Reyting:</b> {kino[3]}/10\n"
        f"📂 <b>Janr:</b> {kino[7]}\n"
        f"🔢 <b>Kod:</b> <code>{kino[0]}</code>\n"
        f"📹 <b>Qismlar soni:</b> {kino[6]}"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if kino[6] > 0:
        cursor.execute("SELECT qism_raqami FROM qismlar WHERE kino_kod=? ORDER BY qism_raqami", (kino[0],))
        for q in cursor.fetchall():
            markup.add(types.InlineKeyboardButton(
                f"📹 {q[0]}-qism",
                callback_data=f"watch_{kino[0]}_{q[0]}"
            ))
    
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_menu"))
    
    if kino[4] == 'photo':
        bot.send_photo(uid, kino[5], caption=caption, reply_markup=markup)
    elif kino[4] == 'video':
        bot.send_video(uid, kino[5], caption=caption, reply_markup=markup)
    else:
        bot.send_message(uid, caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('watch_'))
def watch_part(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval obuna bo'ling!", show_alert=True); return
    
    parts = call.data.split('_')
    kod = int(parts[1])
    qism = int(parts[2])
    
    cursor.execute("SELECT video_file_id FROM qismlar WHERE kino_kod=? AND qism_raqami=?", (kod, qism))
    res = cursor.fetchone()
    
    if res:
        bot.send_video(uid, res[0], caption=f"📹 <b>{qism}-qism</b>")
        bot.answer_callback_query(call.id, "✅ Video yuborildi!")
    else:
        bot.answer_callback_query(call.id, "❌ Topilmadi!", show_alert=True)

# ========== JANR ORQALI QIDIRISH ==========
@bot.callback_query_handler(func=lambda c: c.data == "search_genre")
def search_genre(call):
    uid = call.from_user.id
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval obuna bo'ling!", show_alert=True); return
    
    cursor.execute("SELECT DISTINCT janr FROM kinolar")
    rows = cursor.fetchall()
    
    if not rows:
        bot.answer_callback_query(call.id, "❌ Hali kinolar yo'q!", show_alert=True); return
    
    janrlar = set()
    for row in rows:
        if row[0]:
            for j in row[0].split(','):
                j = j.strip()
                if j:
                    janrlar.add(j)
    
    if not janrlar:
        bot.answer_callback_query(call.id, "❌ Janrlar topilmadi!", show_alert=True); return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for j in sorted(janrlar):
        markup.add(types.InlineKeyboardButton(f"📂 {j}", callback_data=f"genre_{j}"))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_menu"))
    
    bot.edit_message_text("<b>📂 Janrni tanlang:</b>", uid, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('genre_'))
def show_genre(call):
    uid = call.from_user.id
    janr = call.data.replace('genre_', '')
    
    cursor.execute("SELECT * FROM kinolar WHERE janr LIKE ?", (f'%{janr}%',))
    kinolar = cursor.fetchall()
    
    if not kinolar:
        bot.answer_callback_query(call.id, f"❌ '{janr}' janrida kino yo'q!", show_alert=True); return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k in kinolar:
        markup.add(types.InlineKeyboardButton(
            f"🎬 {k[1]} (⭐{k[3]})",
            callback_data=f"view_{k[0]}"
        ))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="search_genre"))
    
    bot.edit_message_text(
        f"<b>📂 '{janr}' janridagi kinolar:</b>",
        uid, call.message.message_id, reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith('view_'))
def view_kino(call):
    uid = call.from_user.id
    kod = int(call.data.replace('view_', ''))
    
    cursor.execute("SELECT * FROM kinolar WHERE kino_kod=?", (kod,))
    kino = cursor.fetchone()
    
    if kino:
        bot.delete_message(uid, call.message.message_id)
        send_kino(uid, kino)
    else:
        bot.answer_callback_query(call.id, "❌ Topilmadi!", show_alert=True)

# ========== NEXMOVIE PRO ==========
@bot.callback_query_handler(func=lambda c: c.data == "nexmovie_pro")
def nexmovie_pro(call):
    uid = call.from_user.id
    
    if not check_sub(uid):
        bot.answer_callback_query(call.id, "❌ Avval obuna bo'ling!", show_alert=True)
        return
    
    if is_pro(uid):
        bot.answer_callback_query(call.id, "✅ Siz allaqachon PRO foydalanuvchisiz!", show_alert=True)
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("💳 To'lov qildim ✅", callback_data="payment_done"))
    markup.add(types.InlineKeyboardButton("◀️ Orqaga", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        "💎 <b>NexMovie Pro</b> 💎\n\n"
        "🔥 <b>PRO imkoniyatlar:</b>\n"
        "✅ Reklamasiz kinolar\n"
        "✅ Eng yangi kinolar birinchi\n"
        "✅ Maxsus premyeralar\n"
        "✅ Full HD sifat\n\n"
        "❌ <b>Sizda PRO mavjud emas!</b>\n\n"
        f"💰 <b>To'lov summasi:</b> {TOLOV_SUMMASI}\n\n"
        "💳 <b>VISA karta:</b>\n"
        "<code>4916 9903 1619 3280</code>\n\n"
        "📌 To'lov qilib, <b>\"To'lov qildim\"</b> tugmasini bosing va chek rasmini yuboring.\n\n"
        "⏰ 24 soat ichida PRO aktivlashtiriladi!",
        uid, call.message.message_id, reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == "payment_done")
def payment_done(call):
    uid = call.from_user.id
    
    if is_pro(uid):
        bot.answer_callback_query(call.id, "✅ Siz allaqachon PROsiz!", show_alert=True)
        return
    
    user_states[uid] = {'step': 'waiting_check'}
    bot.answer_callback_query(call.id)
    bot.send_message(uid,
        "📸 <b>To'lov cheki</b>\n\n"
        f"Iltimos, {TOLOV_SUMMASI} to'lov qilganingizni tasdiqlovchi "
        "chek yoki skrinshot rasmini yuboring.\n\n"
        "⚠️ Rasm aniq va to'lov miqdori ko'rinib turishi kerak!\n\n"
        "Bekor qilish uchun /cancel"
    )

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id, {}).get('step') == 'waiting_check',
                     content_types=['photo', 'text'])
def get_check_photo(msg):
    uid = msg.from_user.id
    
    if msg.text and msg.text == '/cancel':
        user_states.pop(uid, None)
        show_menu(uid)
        return
    
    if not msg.photo:
        bot.send_message(uid, "❌ Iltimos, rasm yuboring!")
        r
