import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging
from flask import Flask
from threading import Thread

# Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 NexMovie"

@app.route('/ping')
def ping():
    return "PONG"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Sozlamalar
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = 8306639956
CHANNEL = "@Vexron_stars"
PRO_PRICE = "14.000 so'm"
CARD = "4916 9903 1619 3280"
DATA_FILE = "/tmp/nexmovie.json"

# Database
class DB:
    def __init__(self):
        self.d = {"movies": {}, "users": {}, "comments": {}, "ratings": {}, "pro": [], "payments": []}
        self.load()
    
    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: self.d.update(json.load(f))
            except: pass
    
    def save(self):
        with open(DATA_FILE, 'w') as f: json.dump(self.d, f, ensure_ascii=False)
    
    def add_movie(self, code, name, desc, genre, parts, photo=None):
        self.d["movies"][str(code)] = {
            "name": name, "desc": desc, "genre": genre,
            "parts_count": int(parts), "parts": {},
            "rating": 0, "views": 0, "photo": photo,
            "added": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.save()
    
    def add_part(self, code, part_num, video_id):
        code = str(code)
        if code in self.d["movies"]:
            self.d["movies"][code]["parts"][str(part_num)] = video_id
            self.save()
    
    def get_movie(self, code):
        return self.d["movies"].get(str(code))
    
    def get_all_movies(self):
        return self.d.get("movies", {})
    
    def search_by_name(self, query):
        results = []
        for code, m in self.d["movies"].items():
            if query.lower() in m["name"].lower():
                results.append({"code": code, **m})
        return results
    
    def search_by_genre(self, genre):
        results = []
        for code, m in self.d["movies"].items():
            if genre.lower() in m["genre"].lower():
                results.append({"code": code, **m})
        return results
    
    def get_top_rated(self, limit=10):
        movies = [{"code": c, **m} for c, m in self.d["movies"].items()]
        return sorted(movies, key=lambda x: x["rating"], reverse=True)[:limit]
    
    def get_top_viewed(self, limit=10):
        movies = [{"code": c, **m} for c, m in self.d["movies"].items()]
        return sorted(movies, key=lambda x: x["views"], reverse=True)[:limit]
    
    def add_view(self, code):
        code = str(code)
        if code in self.d["movies"]:
            self.d["movies"][code]["views"] += 1
            self.save()
    
    def add_rating(self, code, user_id, stars):
        code = str(code); user_id = str(user_id)
        if code not in self.d["ratings"]:
            self.d["ratings"][code] = {}
        self.d["ratings"][code][user_id] = stars
        ratings = self.d["ratings"][code].values()
        self.d["movies"][code]["rating"] = round(sum(ratings) / len(ratings), 1)
        self.save()
    
    def get_user_rating(self, code, user_id):
        return self.d.get("ratings", {}).get(str(code), {}).get(str(user_id))
    
    def add_comment(self, code, user_id, name, text):
        code = str(code)
        if code not in self.d["comments"]:
            self.d["comments"][code] = []
        self.d["comments"][code].append({
            "user_id": str(user_id), "name": name, "text": text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        self.d["comments"][code] = self.d["comments"][code][-50:]
        self.save()
    
    def get_comments(self, code, limit=10):
        return self.d.get("comments", {}).get(str(code), [])[-limit:]
    
    def is_pro(self, uid): return str(uid) in self.d["pro"]
    def add_pro(self, uid):
        uid = str(uid)
        if uid not in self.d["pro"]: self.d["pro"].append(uid); self.save()
    
    def get_genres(self):
        genres = set()
        for m in self.d["movies"].values():
            for g in m["genre"].split(","):
                genres.add(g.strip())
        return sorted(genres)
    
    def get_stats(self):
        return {
            "movies": len(self.d["movies"]),
            "users": len(self.d.get("users", {})),
            "pro": len(self.d["pro"]),
            "total_views": sum(m["views"] for m in self.d["movies"].values()),
            "comments": sum(len(c) for c in self.d.get("comments", {}).values())
        }

db = DB()

# Menyu
def main_menu(uid):
    kb = [
        [InlineKeyboardButton("🔢 Kod bo'yicha qidirish", callback_data="search_code")],
        [InlineKeyboardButton("🔤 Nomi bo'yicha qidirish", callback_data="search_name")],
        [InlineKeyboardButton("🎭 Janr bo'yicha qidirish", callback_data="genres")],
        [InlineKeyboardButton("⭐ TOP Reyting", callback_data="top_rated")],
        [InlineKeyboardButton("👁 TOP Ko'rilgan", callback_data="top_viewed")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]
    if db.is_pro(uid):
        kb.append([InlineKeyboardButton("⭐ PRO ✅", callback_data="pro_active")])
    else:
        kb.append([InlineKeyboardButton(f"⭐ NexMovie Pro - {PRO_PRICE}", callback_data="pro_buy")])
    return InlineKeyboardMarkup(kb)

def admin_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Kino qo'shish"), KeyboardButton("🎞 Qism qo'shish")],
        [KeyboardButton("📋 Kinolar ro'yxati"), KeyboardButton("📊 Statistika")],
        [KeyboardButton("🏠 Asosiy menyu")],
    ], resize_keyboard=True)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    db.d["users"][str(uid)] = {"name": update.effective_user.first_name, "joined": datetime.now().strftime("%Y-%m-%d")}
    db.save()
    
    if uid == ADMIN_ID:
        await update.message.reply_text(
            f"🎬 <b>NexMovie Bot</b>\n\n👋 {update.effective_user.first_name}\n\nAdmin panel uchun: /admin",
            reply_markup=main_menu(uid), parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"🎬 <b>NexMovie Bot</b>\n\n👋 {update.effective_user.first_name}\n\nKino kodini yuboring yoki menyudan foydalaning:",
            reply_markup=main_menu(uid), parse_mode='HTML'
        )

# ADMIN PANEL
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Ruxsat yo'q!")
        return
    
    await update.message.reply_text("👑 <b>Admin Panel</b>", reply_markup=admin_menu(), parse_mode='HTML')

# ADMIN XABARLARI
async def handle_admin_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID: return
    
    txt = update.message.text.strip()
    
    if txt == "➕ Kino qo'shish":
        context.user_data['add_movie'] = True
        context.user_data['m_step'] = 'code'
        await update.message.reply_text("🎬 <b>Kino qo'shish</b>\n\n<b>1. Kino kodini yuboring:</b>\n<i>Masalan: 101</i>", parse_mode='HTML')
    
    elif txt == "🎞 Qism qo'shish":
        context.user_data['add_part'] = True
        await update.message.reply_text("🎞 <b>Qism qo'shish</b>\n\n<b>Kino kodini yuboring:</b>", parse_mode='HTML')
    
    elif txt == "📋 Kinolar ro'yxati":
        movies = db.get_all_movies()
        if not movies:
            await update.message.reply_text("📭 Kinolar yo'q!")
            return
        text = "📋 <b>Kinolar:</b>\n\n"
        for code, m in movies.items():
            text += f"🔢 {code} | {m['name']} | ⭐{m['rating']} | 👁{m['views']}\n"
        await update.message.reply_text(text, parse_mode='HTML')
    
    elif txt == "📊 Statistika":
        s = db.get_stats()
        await update.message.reply_text(
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: {s['users']}\n"
            f"🎬 Kinolar: {s['movies']}\n"
            f"👁 Ko'rishlar: {s['total_views']}\n"
            f"⭐ PRO: {s['pro']}\n"
            f"💬 Fikrlar: {s['comments']}",
            parse_mode='HTML'
        )
    
    elif txt == "🏠 Asosiy menyu":
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        await update.message.reply_text("🏠 Asosiy menyu", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True))
    
    # Kino qo'shish bosqichlari
    elif context.user_data.get('add_movie'):
        step = context.user_data.get('m_step')
        
        if step == 'code':
            context.user_data['m_code'] = txt
            context.user_data['m_step'] = 'name'
            await update.message.reply_text("✅ Kod qabul qilindi!\n\n<b>2. Kino nomini yuboring:</b>", parse_mode='HTML')
        
        elif step == 'name':
            context.user_data['m_name'] = txt
            context.user_data['m_step'] = 'desc'
            await update.message.reply_text("✅ Nom qabul qilindi!\n\n<b>3. Tavsifni yuboring:</b>", parse_mode='HTML')
        
        elif step == 'desc':
            context.user_data['m_desc'] = txt
            context.user_data['m_step'] = 'genre'
            await update.message.reply_text("✅ Tavsif qabul qilindi!\n\n<b>4. Janrni yuboring:</b>\n<i>Masalan: Jangari, Drama</i>", parse_mode='HTML')
        
        elif step == 'genre':
            context.user_data['m_genre'] = txt
            context.user_data['m_step'] = 'parts'
            await update.message.reply_text("✅ Janr qabul qilindi!\n\n<b>5. Qismlar sonini yuboring:</b>\n<i>Masalan: 12</i>", parse_mode='HTML')
        
        elif step == 'parts':
            try:
                parts = int(txt)
                context.user_data['m_parts'] = parts
                context.user_data['m_step'] = 'photo'
                await update.message.reply_text("✅ Qismlar soni qabul qilindi!\n\n<b>6. Kino rasmini yuboring</b> (yoki /skip):", parse_mode='HTML')
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
        
        elif step == 'photo':
            # Kino qo'shish yakunlandi
            db.add_movie(
                context.user_data['m_code'],
                context.user_data['m_name'],
                context.user_data['m_desc'],
                context.user_data['m_genre'],
                context.user_data['m_parts']
            )
            await update.message.reply_text(
                f"✅ <b>Kino qo'shildi!</b>\n\n"
                f"🔢 Kod: {context.user_data['m_code']}\n"
                f"🎬 Nomi: {context.user_data['m_name']}\n"
                f"🎞 Qismlar: {context.user_data['m_parts']}",
                reply_markup=admin_menu(), parse_mode='HTML'
            )
            context.user_data['add_movie'] = False
    
    # Qism qo'shish
    elif context.user_data.get('add_part'):
        if not context.user_data.get('p_code'):
            context.user_data['p_code'] = txt
            await update.message.reply_text("✅ Kod qabul qilindi!\n\n<b>Qism raqamini va video yuboring</b>\n<i>Avval raqam, keyin video</i>", parse_mode='HTML')
        else:
            try:
                part_num = int(txt)
                context.user_data['p_num'] = part_num
                await update.message.reply_text("📹 <b>Video yuboring:</b>", parse_mode='HTML')
            except:
                await update.message.reply_text("❌ Qism raqami raqam bo'lishi kerak!")

# ADMIN VIDEO QABUL QILISH
async def handle_admin_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID: return
    
    if context.user_data.get('add_part') and context.user_data.get('p_code'):
        code = context.user_data['p_code']
        part_num = context.user_data['p_num']
        video_id = update.message.video.file_id
        
        db.add_part(code, part_num, video_id)
        
        await update.message.reply_text(
            f"✅ <b>Qism qo'shildi!</b>\n\n🎬 Kino: {code}\n🎞 Qism: {part_num}",
            reply_markup=admin_menu(), parse_mode='HTML'
        )
        
        context.user_data['add_part'] = False
        context.user_data['p_code'] = None
        context.user_data['p_num'] = None

# ADMIN RASM QABUL QILISH (kino uchun)
async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID: return
    
    if context.user_data.get('add_movie') and context.user_data.get('m_step') == 'photo':
        photo_id = update.message.photo[-1].file_id
        
        db.add_movie(
            context.user_data['m_code'],
            context.user_data['m_name'],
            context.user_data['m_desc'],
            context.user_data['m_genre'],
            context.user_data['m_parts'],
            photo_id
        )
        
        await update.message.reply_text(
            f"✅ <b>Kino qo'shildi!</b>\n\n"
            f"🔢 Kod: {context.user_data['m_code']}\n"
            f"🎬 Nomi: {context.user_data['m_name']}\n"
            f"🎞 Qismlar: {context.user_data['m_parts']}",
            reply_markup=admin_menu(), parse_mode='HTML'
        )
        
        context.user_data['add_movie'] = False

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID: return
    
    if context.user_data.get('add_movie') and context.user_data.get('m_step') == 'photo':
        db.add_movie(
            context.user_data['m_code'],
            context.user_data['m_name'],
            context.user_data['m_desc'],
            context.user_data['m_genre'],
            context.user_data['m_parts']
        )
        
        await update.message.reply_text(
            f"✅ <b>Kino qo'shildi!</b>\n\n"
            f"🔢 Kod: {context.user_data['m_code']}\n"
            f"🎬 Nomi: {context.user_data['m_name']}",
            reply_markup=admin_menu(), parse_mode='HTML'
        )
        
        context.user_data['add_movie'] = False

# TEXT HANDLER
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    # Admin
    if uid == ADMIN_ID and txt in ["➕ Kino qo'shish", "🎞 Qism qo'shish", "📋 Kinolar ro'yxati", "📊 Statistika", "🏠 Asosiy menyu"]:
        await handle_admin_msg(update, context)
        return
    
    if uid == ADMIN_ID and (context.user_data.get('add_movie') or context.user_data.get('add_part')):
        await handle_admin_msg(update, context)
        return
    
    # Kino kodini qidirish
    movie = db.get_movie(txt)
    if movie:
        await show_movie(update, txt, movie, uid)
        return
    
    # Nomi bo'yicha qidirish
    if context.user_data.get('searching'):
        movies = db.search_by_name(txt)
        if movies:
            text = f"🔍 <b>'{txt}' qidiruvi:</b>\n\n"
            kb = []
            for m in movies[:10]:
                text += f"🔢 {m['code']} - {m['name']} (⭐{m['rating']})\n"
                kb.append([InlineKeyboardButton(f"🎬 {m['name'][:30]}", callback_data=f"movie_{m['code']}")])
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        else:
            await update.message.reply_text("❌ Topilmadi!")
        context.user_data['searching'] = False
        return
    
    # Fikr yozish
    if context.user_data.get('commenting'):
        code = context.user_data['commenting']
        db.add_comment(code, uid, update.effective_user.first_name, txt)
        await update.message.reply_text("✅ Fikringiz qabul qilindi!")
        context.user_data['commenting'] = None
        return
    
    await update.message.reply_text("❌ Kino topilmadi! Kodni tekshiring.")

async def show_movie(update, code, movie, uid):
    db.add_view(code)
    comments = db.get_comments(code)
    user_rating = db.get_user_rating(code, uid)
    
    text = f"🎬 <b>{movie['name']}</b>\n\n"
    text += f"📝 {movie.get('desc', '')[:200]}\n"
    text += f"⭐ Reyting: {movie['rating']}/5\n"
    text += f"🎭 Janr: {movie['genre']}\n"
    text += f"🔢 Kod: <code>{code}</code>\n"
    text += f"🎞 Qismlar: {movie['parts_count']}\n"
    text += f"👁 Ko'rishlar: {movie['views']}\n"
    
    kb = []
    
    # Reyting
    if user_rating is None:
        kb.append([InlineKeyboardButton(f"{'⭐'*i}", callback_data=f"rate_{code}_{i}") for i in range(1, 6)])
    else:
        kb.append([InlineKeyboardButton(f"Siz: {'⭐'*user_rating}", callback_data="none")])
    
    # Qismlar
    parts_kb = []
    for i in range(1, movie['parts_count'] + 1):
        if str(i) in movie.get("parts", {}):
            parts_kb.append(InlineKeyboardButton(f"▶️{i}", callback_data=f"part_{code}_{i}"))
    if parts_kb:
        kb.append(parts_kb)
    
    kb.append([
        InlineKeyboardButton("💬 Fikr", callback_data=f"comment_{code}"),
        InlineKeyboardButton("📋 Fikrlar", callback_data=f"comments_{code}")
    ])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
    
    if movie.get("photo"):
        await update.message.reply_photo(movie["photo"], caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

# CALLBACK
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); d = q.data; uid = q.from_user.id
    
    if d == "search_code":
        await q.edit_message_text("🔢 <b>Kino kodini yuboring:</b>", parse_mode='HTML')
    
    elif d == "search_name":
        context.user_data['searching'] = True
        await q.edit_message_text("🔤 <b>Kino nomini yuboring:</b>", parse_mode='HTML')
    
    elif d == "genres":
        genres = db.get_genres()
        if not genres:
            await q.edit_message_text("📭 Janrlar yo'q!"); return
        kb = []
        for g in genres[:20]:
            kb.append([InlineKeyboardButton(f"🎭 {g}", callback_data=f"genre_{g}")])
        kb.append([InlineKeyboardButton("🔙", callback_data="main")])
        await q.edit_message_text("🎭 <b>Janrni tanlang:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    
    elif d.startswith("genre_"):
        genre = d.replace("genre_", "")
        movies = db.search_by_genre(genre)
        if movies:
            text = f"🎭 <b>{genre}</b>:\n\n"
            kb = []
            for m in movies[:10]:
                text += f"🔢 {m['code']} - {m['name']} (⭐{m['rating']})\n"
                kb.append([InlineKeyboardButton(f"🎬 {m['name'][:30]}", callback_data=f"movie_{m['code']}")])
            kb.append([InlineKeyboardButton("🔙", callback_data="genres")])
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        else:
            await q.edit_message_text("📭 Yo'q!")
    
    elif d == "top_rated":
        movies = db.get_top_rated(10)
        text = "⭐ <b>TOP 10:</b>\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - ⭐{m['rating']}\n"
        await q.edit_message_text(text, parse_mode='HTML')
    
    elif d == "top_viewed":
        movies = db.get_top_viewed(10)
        text = "👁 <b>TOP 10:</b>\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - 👁{m['views']}\n"
        await q.edit_message_text(text, parse_mode='HTML')
    
    elif d == "stats
