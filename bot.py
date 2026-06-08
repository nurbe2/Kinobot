import json
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import logging
from flask import Flask
from threading import Thread

# Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 NexMovie Bot"

@app.route('/ping')
def ping():
    return "PONG"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Sozlamalar
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = 8306639956
CHANNEL = "@Vexron_stars"
PRO_PRICE = "14.000 so'm"
CARD = "4916 9903 1619 3280"
DATA_FILE = "/tmp/data.json"

# Conversation states
ADD_MOVIE, ADD_PART, RATING, COMMENT = range(4)

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
        with open(DATA_FILE, 'w') as f: json.dump(self.d, f, ensure_ascii=False, indent=2)
    
    def add_movie(self, code, name, desc, rating, genre, parts_count):
        code = str(code)
        self.d["movies"][code] = {
            "name": name, "desc": desc, "rating": rating,
            "genre": genre, "parts_count": parts_count,
            "views": 0, "parts": {}, "photo": None,
            "added": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.save()
    
    def add_part(self, code, part_num, video_id):
        code = str(code); part_num = int(part_num)
        if code in self.d["movies"]:
            self.d["movies"][code]["parts"][str(part_num)] = video_id
            self.save()
    
    def get_movie(self, code):
        return self.d["movies"].get(str(code))
    
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
        # O'rtacha hisoblash
        ratings = self.d["ratings"][code].values()
        avg = sum(ratings) / len(ratings)
        self.d["movies"][code]["rating"] = round(avg, 1)
        self.save()
    
    def get_user_rating(self, code, user_id):
        code = str(code); user_id = str(user_id)
        return self.d.get("ratings", {}).get(code, {}).get(user_id)
    
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

# Yordamchi
def check_sub(user_id):
    try:
        import requests
        # Oddiy tekshirish (TODO: To'liq API bilan)
        return True
    except:
        return True

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
        kb.append([InlineKeyboardButton("⭐ PRO", callback_data="pro_active")])
    else:
        kb.append([InlineKeyboardButton(f"⭐ NexMovie Pro - {PRO_PRICE}", callback_data="pro_buy")])
    return InlineKeyboardMarkup(kb)

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    # Majburiy obuna
    if not check_sub(uid):
        kb = [
            [InlineKeyboardButton("📢 Obuna bo'lish", url=f"https://t.me/{CHANNEL[1:]}")],
            [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            f"❗ <b>Botdan foydalanish uchun {CHANNEL} kanaliga obuna bo'ling!</b>",
            reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML'
        )
        return
    
    db.d["users"][str(uid)] = {"name": update.effective_user.first_name, "joined": datetime.now().strftime("%Y-%m-%d")}
    db.save()
    
    await update.message.reply_text(
        f"🎬 <b>NexMovie Bot</b>\n\n👋 {update.effective_user.first_name}\n\nKino kodini yuboring yoki menyudan foydalaning:",
        reply_markup=main_menu(uid), parse_mode='HTML'
    )

# KINO QIDIRISH
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    # Kod bo'yicha
    movie = db.get_movie(txt)
    if movie:
        await show_movie(update, txt, movie, uid)
        return
    
    # Admin panel
    if txt == "/admin" and uid == ADMIN_ID:
        await admin_panel(update, context)
        return
    
    await update.message.reply_text("❌ Kino topilmadi! Kodni tekshiring yoki menyudan qidiring.")

async def show_movie(update, code, movie, uid):
    db.add_view(code)
    comments = db.get_comments(code)
    user_rating = db.get_user_rating(code, uid)
    
    text = f"""🎬 <b>{movie['name']}</b>

📝 {movie.get('desc', 'Tavsif yo\'q')[:200]}
⭐ Reyting: {movie['rating']}/5
🎭 Janr: {movie['genre']}
🔢 Kod: <code>{code}</code>
🎞 Qismlar: {movie['parts_count']}
👁 Ko'rishlar: {movie['views']}

💬 Fikrlar ({len(comments)}):"""
    
    for c in comments[-3:]:
        text += f"\n  👤 {c['name']}: {c['text'][:50]}"
    
    kb = []
    
    # Reyting tugmalari
    if user_rating is None:
        kb.append([InlineKeyboardButton(f"{'⭐'*i}", callback_data=f"rate_{code}_{i}") for i in range(1, 6)])
    else:
        kb.append([InlineKeyboardButton(f"Sizning bahoingiz: {'⭐'*user_rating}", callback_data="none")])
    
    # Qismlar
    parts_kb = []
    for i in range(1, movie['parts_count'] + 1):
        parts_kb.append(InlineKeyboardButton(str(i), callback_data=f"part_{code}_{i}"))
    kb.append(parts_kb)
    
    kb.append([
        InlineKeyboardButton("💬 Fikr bildirish", callback_data=f"comment_{code}"),
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
    
    if d == "check_sub":
        if check_sub(uid):
            await start(update, context)
        else:
            await q.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)
    
    elif d == "search_code":
        await q.edit_message_text("🔢 <b>Kino kodini yuboring:</b>\n\n<i>Masalan: 1 yoki 101</i>", parse_mode='HTML')
    
    elif d == "search_name":
        await q.edit_message_text("🔤 <b>Kino nomini yuboring:</b>", parse_mode='HTML')
        context.user_data['searching'] = 'name'
    
    elif d == "genres":
        genres = db.get_genres()
        if not genres:
            await q.edit_message_text("📭 Janrlar yo'q!")
            return
        kb = []
        for g in genres[:20]:
            kb.append([InlineKeyboardButton(f"🎭 {g}", callback_data=f"genre_{g}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
        await q.edit_message_text("🎭 <b>Janrni tanlang:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    
    elif d.startswith("genre_"):
        genre = d.replace("genre_", "")
        movies = db.search_by_genre(genre)
        if movies:
            text = f"🎭 <b>{genre}</b> kinolari:\n\n"
            kb = []
            for m in movies[:10]:
                text += f"🔢 {m['code']} - {m['name']} (⭐{m['rating']})\n"
                kb.append([InlineKeyboardButton(f"🎬 {m['name'][:30]}", callback_data=f"movie_{m['code']}")])
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="genres")])
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        else:
            await q.edit_message_text("📭 Bu janrda kinolar yo'q!")
    
    elif d == "top_rated":
        movies = db.get_top_rated(10)
        text = "⭐ <b>TOP 10 Reyting:</b>\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - ⭐{m['rating']} (👁{m['views']})\n"
        await q.edit_message_text(text, parse_mode='HTML')
    
    elif d == "top_viewed":
        movies = db.get_top_viewed(10)
        text = "👁 <b>TOP 10 Ko'rilgan:</b>\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - 👁{m['views']} (⭐{m['rating']})\n"
        await q.edit_message_text(text, parse_mode='HTML')
    
    elif d == "stats":
        s = db.get_stats()
        await q.edit_message_text(
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Foydalanuvchilar: {s['users']}\n"
            f"🎬 Kinolar: {s['movies']}\n"
            f"👁 Ko'rishlar: {s['total_views']}\n"
            f"⭐ PRO: {s['pro']}\n"
            f"💬 Fikrlar: {s['comments']}",
            parse_mode='HTML'
        )
    
    elif d.startswith("movie_"):
        code = d.replace("movie_", "")
        movie = db.get_movie(code)
        if movie:
            await show_movie(update, code, movie, uid)
    
    elif d.startswith("rate_"):
        parts = d.split("_")
        code, stars = parts[1], int(parts[2])
        db.add_rating(code, uid, stars)
        await q.answer(f"✅ {stars} yulduz baholandi!")
        movie = db.get_movie(code)
        if movie:
            await show_movie(update, code, movie, uid)
    
    elif d.startswith("part_"):
        parts = d.split("_")
        code, part_num = parts[1], parts[2]
        movie = db.get_movie(code)
        if movie and part_num in movie["parts"]:
            await q.message.reply_video(movie["parts"][part_num], caption=f"🎬 {movie['name']} - {part_num}-qism")
    
    elif d.startswith("comment_"):
        code = d.replace("comment_", "")
        context.user_data['commenting'] = code
        await q.edit_message_text("💬 <b>Fikringizni yozing:</b>", parse_mode='HTML')
    
    elif d.startswith("comments_"):
        code = d.replace("comments_", "")
        comments = db.get_comments(code)
        if comments:
            text = f"💬 <b>Fikrlar ({len(comments)}):</b>\n\n"
            for c in comments[-10:]:
                text += f"👤 {c['name']}: {c['text']}\n  📅 {c['date']}\n\n"
        else:
            text = "📭 Hali fikrlar yo'q!"
        await q.edit_message_text(text, parse_mode='HTML')
    
    elif d == "pro_buy":
        context.user_data['buying_pro'] = True
        await q.edit_message_text(
            f"⭐ <b>NexMovie Pro</b>\n\nNarxi: <b>{PRO_PRICE}</b>\nKarta: <code>{CARD}</code>\n\nTo'lov qilib, chek rasmini yuboring!",
            parse_mode='HTML'
        )
    
    elif d == "pro_active":
        await q.answer("✅ Sizda PRO aktiv!", show_alert=True)
    
    elif d == "main":
        await q.edit_message_text(
            f"🎬 <b>NexMovie Bot</b>\n\nKino kodini yuboring yoki menyudan foydalaning:",
            reply_markup=main_menu(uid), parse_mode='HTML'
        )
    
    elif d == "none":
        await q.answer("Siz allaqachon baholagansiz!")

# Admin panel
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    kb = [
        [InlineKeyboardButton("➕ Kino qo'shish", callback_data="admin_add")],
        [InlineKeyboardButton("🎞 Qism qo'shish", callback_data="admin_part")],
        [InlineKeyboardButton("📋 Kinolar ro'yxati", callback_data="admin_list")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]
    
    await update.message.reply_text("👑 <b>Admin Panel</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

# PRO rasmi
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if context.user_data.get('buying_pro'):
        photo = update.message.photo[-1]
        kb = [
            [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{uid}"),
             InlineKeyboardButton("❌ Bekor", callback_data=f"reject_{uid}")]
        ]
        await context.bot.send_photo(ADMIN_ID, photo.file_id,
            caption=f"⭐ PRO so'rov!\n👤 {update.effective_user.first_name}\n🆔 {uid}",
            reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ Chek yuborildi!")
        context.user_data['buying_pro'] = False
    
    elif uid == ADMIN_ID and context.user_data.get('adding_movie'):
        context.user_data['movie_photo'] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Rasm qabul qilindi!")

# Admin approve
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); d = q.data; uid = q.from_user.id
    
    if not uid == ADMIN_ID and d.startswith(("approve_", "reject_")):
        return
    
    if d.startswith("approve_"):
        target = d.replace("approve_", "")
        db.add_pro(target)
        try: await context.bot.send_message(int(target), "🎉 Pro aktivlashtirildi!")
        except: pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ TASDIQLANDI!", parse_mode='HTML')
    
    elif d.startswith("reject_"):
        target = d.replace("reject_", "")
        try: await context.bot.send_message(int(target), "❌ Rad etildi.")
        except: pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n❌ RAD", parse_mode='HTML')

# Main
def main():
    Thread(target=run_flask).start()
    print("🎬 NexMovie Bot ishga tushmoqda...")
    
    app_bot = Application.builder().token(BOT_TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_panel))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.add_handler(CallbackQueryHandler(callback))
    app_bot.add_handler(CallbackQueryHandler(admin_callback, pattern="^(approve_|reject_)"))
    
    print("✅ Bot ishga tushdi!")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
