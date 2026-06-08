import json
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import logging
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "🎬 NEXMOVIE PRO MAX"

@app.route('/ping')
def ping():
    return "PONG"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = 8306639956
CHANNEL = '@Vexron_stars'
PRO_PRICE = "14.000 so'm"
CARD = "4916 9903 1619 3280"
DATA_FILE = "/tmp/nexmovie.json"

class Database:
    def __init__(self):
        self.data = {"movies": {}, "users": {}, "comments": {}, "ratings": {}, "pro_users": [], "payments": [], "admins": [str(ADMIN_ID)]}
        self.load()
    
    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    loaded = json.load(f)
                    for key in self.data:
                        if key in loaded:
                            self.data[key] = loaded[key]
            except:
                self.save()
    
    def save(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def is_admin(self, uid):
        return str(uid) in self.data.get("admins", [])
    
    def add_admin(self, uid):
        if str(uid) not in self.data.get("admins", []):
            self.data["admins"].append(str(uid))
            self.save()
    
    def add_movie(self, code, name, desc, genre, parts, is_pro=False, photo=None):
        self.data["movies"][str(code)] = {"name": name, "desc": desc, "genre": genre, "parts_count": int(parts), "parts": {}, "rating": 0, "views": 0, "photo": photo, "is_pro": is_pro, "added": datetime.now().strftime("%Y-%m-%d %H:%M")}
        self.save()
        return self.data["movies"][str(code)]
    
    def delete_movie(self, code):
        if str(code) in self.data["movies"]:
            del self.data["movies"][str(code)]
            self.save()
            return True
        return False
    
    def get_movie(self, code):
        return self.data["movies"].get(str(code))
    
    def get_all_movies(self):
        return self.data.get("movies", {})
    
    def get_movies_by_type(self, pro_only=False):
        if pro_only:
            return {k: v for k, v in self.data["movies"].items() if v.get("is_pro")}
        return {k: v for k, v in self.data["movies"].items()}
    
    def search_movies(self, query, by="name", pro_only=False):
        movies = self.get_movies_by_type(pro_only) if pro_only else self.data["movies"]
        results = []
        for code, m in movies.items():
            if by == "name" and query.lower() in m["name"].lower():
                results.append({"code": code, **m})
            elif by == "genre" and query.lower() in m["genre"].lower():
                results.append({"code": code, **m})
        return results
    
    def get_top(self, by="rating", limit=10, pro_only=False):
        movies = self.get_movies_by_type(pro_only) if pro_only else self.data["movies"]
        return sorted([{"code": c, **m} for c, m in movies.items()], key=lambda x: x[by], reverse=True)[:limit]
    
    def add_part(self, code, part_num, video_id):
        if str(code) in self.data["movies"]:
            self.data["movies"][str(code)]["parts"][str(part_num)] = video_id
            self.save()
    
    def add_view(self, code):
        if str(code) in self.data["movies"]:
            self.data["movies"][str(code)]["views"] += 1
            self.save()
    
    def add_rating(self, code, user_id, stars):
        code, user_id = str(code), str(user_id)
        self.data.setdefault("ratings", {}).setdefault(code, {})[user_id] = stars
        ratings = list(self.data["ratings"][code].values())
        self.data["movies"][code]["rating"] = round(sum(ratings) / len(ratings), 1)
        self.save()
    
    def get_user_rating(self, code, user_id):
        return self.data.get("ratings", {}).get(str(code), {}).get(str(user_id))
    
    def add_comment(self, code, user_id, name, text):
        code = str(code)
        self.data.setdefault("comments", {}).setdefault(code, [])
        self.data["comments"][code].append({"user_id": str(user_id), "name": name, "text": text, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        if len(self.data["comments"][code]) > 50:
            self.data["comments"][code] = self.data["comments"][code][-50:]
        self.save()
    
    def get_comments(self, code, limit=10):
        return self.data.get("comments", {}).get(str(code), [])[-limit:]
    
    def is_pro(self, uid):
        return str(uid) in self.data.get("pro_users", [])
    
    def add_pro(self, uid):
        if str(uid) not in self.data.get("pro_users", []):
            self.data["pro_users"].append(str(uid))
            self.save()
            return True
        return False
    
    def add_payment(self, uid, name):
        self.data.setdefault("payments", []).append({"uid": str(uid), "name": name, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self.save()
    
    def get_genres(self, pro_only=False):
        movies = self.get_movies_by_type(pro_only) if pro_only else self.data["movies"]
        genres = set()
        for m in movies.values():
            for g in m.get("genre", "").split(","):
                if g.strip():
                    genres.add(g.strip())
        return sorted(genres)
    
    def get_stats(self):
        movies = self.data.get("movies", {})
        return {"movies": len(movies), "users": len(self.data.get("users", {})), "pro": len(self.data.get("pro_users", [])), "views": sum(m.get("views", 0) for m in movies.values()), "comments": sum(len(c) for c in self.data.get("comments", {}).values())}
    
    def get_all_users(self):
        return self.data.get("users", {})

db = Database()

async def broadcast_message(context, text, photo=None):
    users = db.get_all_users()
    count = 0
    for uid in users:
        try:
            if photo:
                await context.bot.send_photo(int(uid), photo, caption=text, parse_mode='HTML')
            else:
                await context.bot.send_message(int(uid), text, parse_mode='HTML')
            count += 1
            await asyncio.sleep(0.3)
        except:
            pass
    return count

def get_main_menu(uid):
    is_pro = db.is_pro(uid)
    kb = [
        [InlineKeyboardButton("🔢 Kod bo'yicha qidirish", callback_data="search_code")],
        [InlineKeyboardButton("🔤 Nomi bo'yicha qidirish", callback_data="search_name")],
        [InlineKeyboardButton("🎭 Janr bo'yicha qidirish", callback_data="search_genre")],
        [InlineKeyboardButton("⭐ TOP Reyting", callback_data="top_rating")],
        [InlineKeyboardButton("🔥 TOP Ko'rilgan", callback_data="top_views")],
        [InlineKeyboardButton("📊 Statistika", callback_data="show_stats")],
    ]
    if is_pro:
        kb.append([InlineKeyboardButton("💎 PRO Qidiruv", callback_data="pro_search")])
        kb.append([InlineKeyboardButton("✅ PRO Aktiv", callback_data="pro_active")])
    else:
        kb.append([InlineKeyboardButton(f"⭐ PRO bo'lish - {PRO_PRICE}", callback_data="buy_pro")])
    return InlineKeyboardMarkup(kb)

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("📹 Qism qo'shish")],
        [KeyboardButton("📋 Barcha kinolar"), KeyboardButton("🗑 Kino o'chirish")],
        [KeyboardButton("👥 Admin boshqarish"), KeyboardButton("📢 E'lon yuborish")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("🏠 Asosiy menyu")],
    ], resize_keyboard=True)

def get_pro_search_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔢 PRO Kod qidirish", callback_data="pro_code")],
        [InlineKeyboardButton("🔤 PRO Nomi qidirish", callback_data="pro_name")],
        [InlineKeyboardButton("🎭 PRO Janr qidirish", callback_data="pro_genre")],
        [InlineKeyboardButton("⭐ PRO TOP Reyting", callback_data="pro_topr")],
        [InlineKeyboardButton("🔥 PRO TOP Ko'rilgan", callback_data="pro_topv")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")],
    ])

async def check_subscription(uid, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, uid)
        return member.status not in ['left', 'kicked']
    except:
        return False

async def broadcast_new_movie(context, movie, code):
    text = f"🎬 <b>YANGI KINO!</b>\n\n<b>{movie['name']}</b>\n\n📝 {movie.get('desc', '')[:150]}...\n🎭 {movie['genre']}\n🎞 {movie['parts_count']} qism\n🔢 Kod: <code>{code}</code>\n{'🔒 PRO' if movie.get('is_pro') else '🆓 Bepul'}\n\n<i>Ko'rish uchun kodni yuboring!</i>"
    count = await broadcast_message(context, text, movie.get("photo"))
    logger.info(f"📢 Yangi kino {count} kishiga yuborildi")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    db.data["users"][str(uid)] = {"name": name, "joined": datetime.now().strftime("%Y-%m-%d")}
    db.save()
    
    if not await check_subscription(uid, context):
        kb = [[InlineKeyboardButton("📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL[1:]}")], [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub")]]
        await update.message.reply_text(f"👋 <b>Salom, {name}!</b>\n\n📢 Botdan foydalanish uchun <b>{CHANNEL}</b> kanaliga obuna bo'ling!", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return
    
    is_pro = db.is_pro(uid)
    text = f"🎬 <b>NEXMOVIE PRO MAX</b>\n\n👋 Xush kelibsiz, <b>{name}</b>!\n\n💎 Holat: {'⭐ PRO' if is_pro else '🆓 Free'}\n🎬 Kinolar: {len(db.data['movies'])} ta\n\n🔢 Kino kodini yuboring yoki menyudan foydalaning:"
    await update.message.reply_text(text, reply_markup=get_main_menu(uid), parse_mode='HTML')

async def show_movie_details(update, code, movie, uid):
    db.add_view(code)
    user_rating = db.get_user_rating(code, uid)
    
    text = f"🎬 <b>{movie['name']}</b>\n\n📝 {movie.get('desc', 'Tavsif yo\'q')[:300]}\n\n⭐ Reyting: <b>{movie['rating']}/5</b>\n🎭 Janr: <b>{movie['genre']}</b>\n🔢 Kod: <code>{code}</code>\n🎞 Qismlar: <b>{movie['parts_count']}</b>\n👁 Ko'rishlar: <b>{movie['views']}</b>\n📅 Qo'shilgan: {movie['added']}\n🔒 {'PRO Kino' if movie.get('is_pro') else '🆓 Bepul'}"
    
    kb = []
    
    if user_rating is None:
        kb.append([InlineKeyboardButton(f"⭐{i}", callback_data=f"rate_{code}_{i}") for i in range(1, 6)])
    else:
        kb.append([InlineKeyboardButton(f"✅ Siz: {user_rating}⭐", callback_data="ignore")])
    
    parts_buttons = [InlineKeyboardButton(f"▶️{i}", callback_data=f"play_{code}_{i}") for i in range(1, movie['parts_count'] + 1) if str(i) in movie.get("parts", {})]
    if parts_buttons:
        kb.append(parts_buttons)
    
    kb.append([InlineKeyboardButton("💬 Fikr yozish", callback_data=f"comment_{code}"), InlineKeyboardButton("📋 Fikrlar", callback_data=f"comments_{code}")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    
    if movie.get("photo"):
        await update.message.reply_photo(movie["photo"], caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db.is_admin(uid):
        return
    
    txt = update.message.text.strip()
    
    if txt == "🎬 Kino qo'shish":
        context.user_data['admin_step'] = 'movie_code'
        await update.message.reply_text("🔢 <b>Kino kodini yuboring:</b>", parse_mode='HTML')
    elif txt == "📹 Qism qo'shish":
        context.user_data['admin_step'] = 'part_code'
        await update.message.reply_text("🔢 <b>Kino kodini yuboring:</b>", parse_mode='HTML')
    elif txt == "📋 Barcha kinolar":
        movies = db.get_all_movies()
        if not movies:
            await update.message.reply_text("📭 Hali kinolar yo'q!"); return
        text = "📋 <b>Barcha kinolar:</b>\n\n"
        for code, m in movies.items():
            text += f"🎬 {code} | {m['name']} | ⭐{m['rating']} | {'🔒PRO' if m.get('is_pro') else '🆓'}\n"
        await update.message.reply_text(text, parse_mode='HTML')
    elif txt == "🗑 Kino o'chirish":
        context.user_data['admin_step'] = 'delete_code'
        await update.message.reply_text("🗑 <b>O'chirish uchun kino kodini yuboring:</b>", parse_mode='HTML')
    elif txt == "👥 Admin boshqarish":
        admins = db.data.get("admins", [])
        text = f"👥 <b>Adminlar ({len(admins)}):</b>\n\n" + "\n".join([f"👤 <code>{a}</code>" for a in admins]) + "\n\n<i>Yangi admin qo'shish uchun ID yuboring:</i>"
        context.user_data['admin_step'] = 'add_admin'
        await update.message.reply_text(text, parse_mode='HTML')
    elif txt == "📢 E'lon yuborish":
        context.user_data['admin_step'] = 'broadcast'
        await update.message.reply_text("📢 <b>E'lon matnini yuboring:</b>\n\n<i>Rasm bilan yuborish uchun rasm yuboring</i>", parse_mode='HTML')
    elif txt == "📊 Statistika":
        s = db.get_stats()
        await update.message.reply_text(f"📊 <b>Statistika</b>\n\n👥 Foydalanuvchilar: {s['users']}\n🎬 Kinolar: {s['movies']}\n👁 Ko'rishlar: {s['views']}\n💎 PRO: {s['pro']}\n💬 Fikrlar: {s['comments']}", parse_mode='HTML')
    elif txt == "🏠 Asosiy menyu":
        context.user_data.clear()
        await update.message.reply_text("🏠 Asosiy menyuga qaytdingiz", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True))
    elif context.user_data.get('admin_step') == 'movie_code':
        context.user_data['movie_code'] = txt; context.user_data['admin_step'] = 'movie_name'
        await update.message.reply_text("📝 <b>Kino nomini yuboring:</b>", parse_mode='HTML')
    elif context.user_data.get('admin_step') == 'movie_name':
        context.user_data['movie_name'] = txt; context.user_data['admin_step'] = 'movie_desc'
        await update.message.reply_text("📄 <b>Tavsifni yuboring:</b>", parse_mode='HTML')
    elif context.user_data.get('admin_step') == 'movie_desc':
        context.user_data['movie_desc'] = txt; context.user_data['admin_step'] = 'movie_genre'
        await update.message.reply_text("🎭 <b>Janrni yuboring:</b>\n\n<i>Masalan: Jangari, Drama</i>", parse_mode='HTML')
    elif context.user_data.get('admin_step') == 'movie_genre':
        context.user_data['movie_genre'] = txt; context.user_data['admin_step'] = 'movie_parts'
        await update.message.reply_text("🎞 <b>Qismlar sonini yuboring:</b>", parse_mode='HTML')
    elif context.user_data.get('admin_step') == 'movie_parts':
        try:
            parts = int(txt)
            context.user_data['movie_parts'] = parts; context.user_data['admin_step'] = 'movie_pro'
            await update.message.reply_text("🔒 <b>Bu PRO kino bo'lsinmi?</b>\n\n<code>ha</code> yoki <code>yo'q</code>", parse_mode='HTML')
        except:
            await update.message.reply_text("❌ Raqam kiriting!")
    elif context.user_data.get('admin_step') == 'movie_pro':
        context.user_data['movie_pro'] = txt.lower() in ['ha', 'yes', 'haa', '1', 'pro']
        context.user_data['admin_step'] = 'movie_photo'
        await update.message.reply_text("🖼 <b>Kino rasmini yuboring</b> (yoki /skip):", parse_mode='HTML')
    elif context.user_data.get('admin_step') == 'part_code':
        movie = db.get_movie(txt)
        if not movie:
            await update.message.reply_text("❌ Kino topilmadi!"); context.user_data['admin_step'] = None; return
        context.user_data['part_code'] = txt; context.user_data['admin_step'] = 'part_num'
        await update.message.reply_text(f"🔢 <b>Qism raqamini yuboring</b> (1-{movie['parts_count']}):", parse_mode='HTML')
    elif context.user_data.get('admin_step') == 'part_num':
        try:
            context.user_data['part_num'] = int(txt); context.user_data['admin_step'] = 'part_video'
            await update.message.reply_text("📹 <b>Video yuboring:</b>", parse_mode='HTML')
        except:
            await update.message.reply_text("❌ Raqam kiriting!")
    elif context.user_data.get('admin_step') == 'delete_code':
        if db.delete_movie(txt):
            await update.message.reply_text(f"✅ Kino o'chirildi: {txt}", reply_markup=get_admin_keyboard())
        else:
            await update.message.reply_text("❌ Kino topilmadi!")
        context.user_data['admin_step'] = None
    elif context.user_data.get('admin_step') == 'add_admin':
        db.add_admin(txt)
        await update.message.reply_text(f"✅ Yangi admin qo'shildi: <code>{txt}</code>", reply_markup=get_admin_keyboard(), parse_mode='HTML')
        context.user_data['admin_step'] = None
    elif context.user_data.get('admin_step') == 'broadcast':
        count = await broadcast_message(context, f"📢 <b>E'lon</b>\n\n{txt}")
        await update.message.reply_text(f"✅ E'lon {count} kishiga yuborildi!", reply_markup=get_admin_keyboard())
        context.user_data['admin_step'] = None

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db.is_admin(uid): return
    
    if context.user_data.get('admin_step') == 'movie_photo':
        photo_id = update.message.photo[-1].file_id
        movie = db.add_movie(context.user_data['movie_code'], context.user_data['movie_name'], context.user_data['movie_desc'], context.user_data['movie_genre'], context.user_data['movie_parts'], context.user_data.get('movie_pro', False), photo_id)
        await update.message.reply_text(f"✅ <b>Kino qo'shildi!</b>\n\n🎬 {movie['name']}\n🔢 Kod: {context.user_data['movie_code']}", reply_markup=get_admin_keyboard(), parse_mode='HTML')
        await broadcast_new_movie(context, movie, context.user_data['movie_code'])
        context.user_data['admin_step'] = None
    elif context.user_data.get('admin_step') == 'broadcast':
        count = await broadcast_message(context, update.message.caption or "📢 E'lon", update.message.photo[-1].file_id)
        await update.message.reply_text(f"✅ E'lon {count} kishiga yuborildi!", reply_markup=get_admin_keyboard())
        context.user_data['admin_step'] = None

async def handle_admin_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db.is_admin(uid): return
    if context.user_data.get('admin_step') == 'part_video':
        db.add_part(context.user_data['part_code'], context.user_data['part_num'], update.message.video.file_id)
        await update.message.reply_text(f"✅ <b>Qism qo'shildi!</b>\n\n🎬 Kino: {context.user_data['part_code']}\n📹 Qism: {context.user_data['part_num']}", reply_markup=get_admin_keyboard(), parse_mode='HTML')
        context.user_data['admin_step'] = None

async def skip_photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id): return
    if context.user_data.get('admin_step') == 'movie_photo':
        movie = db.add_movie(context.user_data['movie_code'], context.user_data['movie_name'], context.user_data['movie_desc'], context.user_data['movie_genre'], context.user_data['movie_parts'], context.user_data.get('movie_pro', False))
        await update.message.reply_text(f"✅ <b>Kino qo'shildi!</b>\n\n🎬 {movie['name']}", reply_markup=get_admin_keyboard(), parse_mode='HTML')
        await broadcast_new_movie(context, movie, context.user_data['movie_code'])
        context.user_data['admin_step'] = None

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    if db.is_admin(uid):
        admin_commands = ["🎬 Kino qo'shish", "📹 Qism qo'shish", "📋 Barcha kinolar", "🗑 Kino o'chirish", "👥 Admin boshqarish", "📢 E'lon yuborish", "📊 Statistika", "🏠 Asosiy menyu"]
        if txt in admin_commands or context.user_data.get('admin_step'):
            await handle_admin_panel(update, context)
            return
    
    if not await check_subscription(uid, context):
        await update.message.reply_text(f"❌ Iltimos, avval {CHANNEL} kanaliga obuna bo'ling!\n/start bosing.")
        return
    
    movie = db.get_movie(txt)
    if movie:
        if movie.get("is_pro") and not db.is_pro(uid):
            await update.message.reply_text(f"🔒 <b>Bu PRO kino!</b>\n\nPRO bo'lish uchun: <b>{PRO_PRICE}</b>\n💳 Karta: <code>{CARD}</code>", parse_mode='HTML')
            return
        await show_movie_details(update, txt, movie, uid)
        return
    
    if context.user_data.get('search_mode'):
        pro_only = context.user_data.get('pro_search', False)
        movies = db.search_movies(txt, pro_only=pro_only)
        if movies:
            kb = [[InlineKeyboardButton(f"🎬 {m['name'][:35]}", callback_data=f"view_{m['code']}")] for m in movies[:10]]
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
            await update.message.reply_text(f"🔍 '{txt}' bo'yicha natijalar:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("❌ Hech narsa topilmadi!")
        context.user_data['search_mode'] = False
        return
    
    if context.user_data.get('comment_mode'):
        db.add_comment(context.user_data['comment_mode'], uid, update.effective_user.first_name, txt)
        await update.message.reply_text("✅ Fikringiz qabul qilindi!")
        context.user_data['comment_mode'] = None
        return
    
    await update.message.reply_text("❌ Kino topilmadi! Kodni tekshiring yoki /start bosing.")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    
    if d == "check_sub":
        if await check_subscription(uid, context):
            await q.delete_message()
            await context.bot.send_message(uid, "🎬 Xush kelibsiz!\n\n🔢 Kino kodini yuboring:", reply_markup=get_main_menu(uid))
        else:
            await q.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)
        return
    
    if not await check_subscription(uid, context):
        await q.answer("❌ Avval obuna bo'ling!", show_alert=True)
        return
    
    if d == "search_code":
        await q.edit_message_text("🔢 <b>Kino kodini yuboring:</b>", parse_mode='HTML')
    elif d == "search_name":
        context.user_data['search_mode'] = True
        context.user_data['pro_search'] = False
        await q.edit_message_text("🔤 <b>Kino nomini yuboring:</b>", parse_mode='HTML')
    elif d == "search_genre":
        genres = db.get_genres()
        if not genres:
            await q.edit_message_text("📭 Janrlar yo'q!"); return
        kb = [[InlineKeyboardButton(f"🎭 {g}", callback_data=f"genre_{g}")] for g in genres[:20]]
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        await q.edit_message_text("🎭 <b>Janrni tanlang:</b>", reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("genre_"):
        genre = d.replace("genre_", "")
        movies = db.search_movies(genre, by="genre")
        if movies:
            kb = [[InlineKeyboardButton(f"🎬 {m['name'][:35]}", callback_data=f"view_{m['code']}")] for m in movies[:10]]
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="search_genre")])
            await q.edit_message_text(f"🎭 <b>{genre}</b> janridagi kinolar:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text("📭 Kinolar yo'q!")
    elif d == "top_rating":
        movies = db.get_top("rating", 10)
        text = "⭐ <b>TOP 10 Reyting:</b>\n\n"
        kb = []
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - ⭐{m['rating']}\n"
            kb.append([InlineKeyboardButton(f"{i}. 🎬 {m['name'][:30]}", callback_data=f"view_{m['code']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    elif d == "top_views":
        movies = db.get_top("views", 10)
        text = "🔥 <b>TOP 10 Ko'rilgan:</b>\n\n"
        kb = []
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - 👁{m['views']}\n"
            kb.append([InlineKeyboardButton(f"{i}. 🎬 {m['name'][:30]}", callback_data=f"view_{m['code']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    elif d == "show_stats":
        s = db.get_stats()
        text = f"📊 <b>Statistika</b>\n\n👥 {s['users']} | 🎬 {s['movies']} | 👁 {s['views']}\n💎 {s['pro']} | 💬 {s['comments']}"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]]), parse_mode='HTML')
    elif d == "pro_search":
        if not db.is_pro(uid):
            await q.answer("❌ Faqat PRO foydalanuvchilar uchun!", show_alert=True); return
        await q.edit_message_text("💎 <b>PRO Qidiruv</b>", reply_markup=get_pro_search_menu(), parse_mode='HTML')
    elif d == "pro_code":
        context.user_data['pro_search'] = True
        await q.edit_message_text("🔢 <b>PRO kino kodini yuboring:</b>", parse_mode='HTML')
    elif d == "pro_name":
        context.user_data['pro_search'] = True
        context.user_data['search_mode'] = True
        await q.edit_message_text("🔤 <b>PRO kino nomini yuboring:</b>", parse_mode='HTML')
    elif d == "pro_genre":
        genres = db.get_genres(pro_only=True)
        if not genres:
            await q.edit_message_text("📭 PRO janrlar yo'q!"); return
        kb = [[InlineKeyboardButton(f"🎭 {g}", callback_data=f"pgenre_{g}")] for g in genres[:20]]
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="pro_search")])
        await q.edit_message_text("🎭 <b>PRO Janrni tanlang:</b>", reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("pgenre_"):
        genre = d.replace("pgenre_", "")
        movies = db.search_movies(genre, by="genre", pro_only=True)
        if movies:
            kb = [[InlineKeyboardButton(f"🎬 {m['name'][:35]}", callback_data=f"view_{m['code']}")] for m in movies[:10]]
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="pro_genre")])
            await q.edit_message_text(f"🎭 PRO <b>{genre}</b> janridagi kinolar:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text("📭 Kinolar yo'q!")
    elif d == "pro_topr":
        movies = db.get_top("rating", 10, pro_only=True)
        text = "⭐ <b>PRO TOP 10 Reyting:</b>\n\n"
        kb = []
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - ⭐{m['rating']}\n"
            kb.append([InlineKeyboardButton(f"{i}. 🎬 {m['name'][:30]}", callback_data=f"view_{m['code']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="pro_search")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    elif d == "pro_topv":
        movies = db.get_top("views", 10, pro_only=True)
        text = "🔥 <b>PRO TOP 10 Ko'rilgan:</b>\n\n"
        kb = []
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - 👁{m['views']}\n"
            kb.append([InlineKeyboardButton(f"{i}. 🎬 {m['name'][:30]}", callback_data=f"view_{m['code']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="pro_search")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    elif d.startswith("view_"):
        code = d.replace("view_", "")
        movie = db.get_movie(code)
        if movie:
            await q.delete_message()
            await show_movie_details(update, code, movie, uid)
    elif d.startswith("rate_"):
        _, code, stars = d.split("_")
        db.add_rating(code, uid, int(stars))
        await q.answer(f"⭐ {stars} yulduz!")
        movie = db.get_movie(code)
        if movie:
            await show_movie_details(update, code, movie, uid)
    elif d.startswith("play_"):
        _, code, part_num = d.split("_")
        movie = db.get_movie(code)
        if movie and part_num in movie.get("parts", {}):
            await q.message.reply_video(movie["parts"][part_num], caption=f"🎬 {movie['name']} - Qism {part_num}")
    elif d.startswith("comment_"):
        context.user_data['comment_mode'] = d.replace("comment_", "")
        await q.edit_message_text("💬 <b>Fikringizni yozing:</b>", parse_mode='HTML')
    elif d.startswith("comments_"):
        code = d.replace("comments_", "")
        comments = db.get_comments(code)
        if comments:
            text = "💬 <b>Fikrlar:</b>\n\n" + "\n".join([f"👤 {c['name']}: {c['text']}\n📅 {c['date']}\n➖➖➖" for c in comments])
        else:
            text = "📭 Fikrlar yo'q!"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data=f"view_{code}")]]), parse_mode='HTML')
    elif d == "buy_pro":
        context.user_data['buying_pro'] = True
        text = f"⭐ <b>PRO OBUNA</b>\n\n💳 Karta: <code>{CARD}</code>\n💰 Narxi: <b>{PRO_PRICE}</b>\n\n📸 To'lov qilib, <b>chek rasmini</b> shu yerga yuboring!"
        await q.edit_message_text(text, parse_mode='HTML')
    elif d == "pro_active":
        await q.answer("✅ Sizda PRO aktiv!", show_alert=True)
    elif d == "main_menu":
        await q.edit_message_text("🎬 <b>Asosiy menyu</b>", reply_markup=get_main_menu(uid), parse_mode='HTML')
    elif d == "ignore":
        await q.answer("Siz allaqachon baholagansiz!")

async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if db.is_admin(uid) and context.user_data.get('admin_step') == 'movie_photo':
        await handle_admin_photo(update, context)
        return
    
    if context.user_data.get('buying_pro'):
        photo = update.message.photo[-1]
        kb = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{uid}"), InlineKeyboardButton("❌ Bekor qilish", callback_data=f"reject_{uid}")]]
        await context.bot.send_photo(ADMIN_ID, photo.file_id, caption=f"📩 <b>PRO OBUNA SO'ROVI</b>\n\n👤 {update.effective_user.first_name}\n🆔 <code>{uid}</code>\n💰 {PRO_PRICE}\n\n<b>Tasdiqlaysizmi?</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        db.add_payment(uid, update.effective_user.first_name)
        await update.message.reply_text("✅ <b>Chek yuborildi!</b>\n\nAdmin tekshirib, PRO aktivlashtiradi.\n<i>Bu biroz vaqt olishi mumkin.</i>", parse_mode='HTML')
        context.user_data['buying_pro'] = False
        return

async def admin_approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    if q.from_user.id != ADMIN_ID: return
    
    if d.startswith("approve_"):
        target = d.replace("approve_", "")
        if db.add_pro(target):
            try:
                await context.bot.send_message(int(target), "🎉 <b>Tabriklaymiz!</b>\n\n⭐ <b>PRO OBUNA AKTIVLASHTIRILDI!</b>\n\nEndi siz barcha PRO kinolarni ko'rishingiz mumkin!\n/start bosib tekshiring.", parse_mode='HTML')
            except: pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ <b>TASDIQLANDI!</b>", parse_mode='HTML')
    elif d.startswith("reject_"):
        target = d.replace("reject_", "")
        try:
            await context.bot.send_message(int(target), "❌ <b>To'lov rad etildi.</b>\n\nIltimos, qaytadan urinib ko'ring yoki adminga murojaat qiling.", parse_mode='HTML')
        except: pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n❌ <b>RAD ETILDI!</b>", parse_mode='HTML')

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Siz admin emassiz!"); return
    await update.message.reply_text("👑 <b>Admin Panel</b>", reply_markup=get_admin_keyboard(), parse_mode='HTML')

def main():
    Thread(target=run_flask).start()
    logger.info("🎬 NEXMOVIE PRO MAX ishga tushmoqda...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("skip", skip_photo_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_admin_video))
    application.add_handler(CallbackQueryHandler(admin_approve_handler, pattern="^(approve_|reject_)"))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    logger.info("✅ Bot ishga tushdi!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
