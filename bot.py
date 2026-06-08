import json
import os
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
    return "🎬 NexMovie Bot"

@app.route('/ping')
def ping():
    return "PONG"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN', 'TOKEN')
ADMIN_ID = 8306639956
CHANNEL = '@Vexron_stars'
PRO_PRICE = "14.000 som"
CARD = "4916 9903 1619 3280"
DATA_FILE = "/tmp/nexmovie.json"

class DB:
    def __init__(self):
        self.d = {"movies": {}, "users": {}, "comments": {}, "ratings": {}, "pro": [], "payments": []}
        self.load()
    
    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f:
                    self.d.update(json.load(f))
            except:
                pass
    
    def save(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.d, f, ensure_ascii=False)
    
    def add_movie(self, code, name, desc, genre, parts, photo=None):
        self.d["movies"][str(code)] = {"name": name, "desc": desc, "genre": genre, "parts_count": int(parts), "parts": {}, "rating": 0, "views": 0, "photo": photo, "added": datetime.now().strftime("%Y-%m-%d")}
        self.save()
    
    def delete_movie(self, code):
        if str(code) in self.d["movies"]:
            del self.d["movies"][str(code)]
            self.save()
            return True
        return False
    
    def add_part(self, code, part_num, video_id):
        if str(code) in self.d["movies"]:
            self.d["movies"][str(code)]["parts"][str(part_num)] = video_id
            self.save()
    
    def get_movie(self, code):
        return self.d["movies"].get(str(code))
    
    def get_all_movies(self):
        return self.d.get("movies", {})
    
    def search_by_name(self, query):
        return [{"code": c, **m} for c, m in self.d["movies"].items() if query.lower() in m["name"].lower()]
    
    def search_by_genre(self, genre):
        return [{"code": c, **m} for c, m in self.d["movies"].items() if genre.lower() in m["genre"].lower()]
    
    def get_top_rated(self, limit=10):
        return sorted([{"code": c, **m} for c, m in self.d["movies"].items()], key=lambda x: x["rating"], reverse=True)[:limit]
    
    def get_top_viewed(self, limit=10):
        return sorted([{"code": c, **m} for c, m in self.d["movies"].items()], key=lambda x: x["views"], reverse=True)[:limit]
    
    def add_view(self, code):
        if str(code) in self.d["movies"]:
            self.d["movies"][str(code)]["views"] += 1
            self.save()
    
    def add_rating(self, code, user_id, stars):
        self.d.setdefault("ratings", {}).setdefault(str(code), {})[str(user_id)] = stars
        ratings = list(self.d["ratings"][str(code)].values())
        self.d["movies"][str(code)]["rating"] = round(sum(ratings) / len(ratings), 1)
        self.save()
    
    def get_user_rating(self, code, user_id):
        return self.d.get("ratings", {}).get(str(code), {}).get(str(user_id))
    
    def add_comment(self, code, user_id, name, text):
        self.d.setdefault("comments", {}).setdefault(str(code), []).append({"user_id": str(user_id), "name": name, "text": text, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self.d["comments"][str(code)] = self.d["comments"][str(code)][-50:]
        self.save()
    
    def get_comments(self, code, limit=10):
        return self.d.get("comments", {}).get(str(code), [])[-limit:]
    
    def is_pro(self, uid):
        return str(uid) in self.d.get("pro", [])
    
    def add_pro(self, uid):
        if str(uid) not in self.d.get("pro", []):
            self.d.setdefault("pro", []).append(str(uid))
            self.save()
            return True
        return False
    
    def add_payment(self, uid, name):
        self.d.setdefault("payments", []).append({"uid": str(uid), "name": name, "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self.save()
    
    def get_genres(self):
        genres = set()
        for m in self.d["movies"].values():
            for g in m["genre"].split(","):
                genres.add(g.strip())
        return sorted(genres)
    
    def get_stats(self):
        return {"movies": len(self.d.get("movies", {})), "users": len(self.d.get("users", {})), "pro": len(self.d.get("pro", [])), "views": sum(m["views"] for m in self.d["movies"].values()), "comments": sum(len(c) for c in self.d.get("comments", {}).values())}

db = DB()

def main_menu(uid):
    kb = [
        [InlineKeyboardButton("🔢 Kod orqali qidirish", callback_data="code")],
        [InlineKeyboardButton("🔤 Nomi orqali qidirish", callback_data="name")],
        [InlineKeyboardButton("🎭 Janr orqali qidirish", callback_data="genres")],
        [InlineKeyboardButton("⭐ TOP Reyting", callback_data="topr")],
        [InlineKeyboardButton("🔥 TOP Ko'rilgan", callback_data="topv")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]
    if db.is_pro(uid):
        kb.append([InlineKeyboardButton("💎 PRO Aktiv", callback_data="pro_ok")])
    else:
        kb.append([InlineKeyboardButton(f"👑 PRO - {PRO_PRICE}", callback_data="pro_buy")])
    return InlineKeyboardMarkup(kb)

def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎬 Kino qo'shish"), KeyboardButton("📹 Qism qo'shish")],
        [KeyboardButton("📋 Kinolar ro'yxati"), KeyboardButton("🗑 Kino o'chirish")],
        [KeyboardButton("📊 Statistika"), KeyboardButton("🏠 Asosiy menyu")],
    ], resize_keyboard=True)

async def check_sub(uid, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL, uid)
        return member.status not in ['left', 'kicked']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    db.d["users"][str(uid)] = {"name": name, "joined": datetime.now().strftime("%Y-%m-%d")}
    db.save()
    
    if not await check_sub(uid, context):
        kb = [[InlineKeyboardButton("📢 Obuna bo'lish", url=f"https://t.me/{CHANNEL[1:]}")], [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]]
        await update.message.reply_text(f"👋 Salom, {name}!\n\n📢 {CHANNEL} kanaliga obuna bo'ling!", reply_markup=InlineKeyboardMarkup(kb))
        return
    
    await update.message.reply_text(f"🎬 Xush kelibsiz, {name}!\n\n🔢 Kino kodini yuboring yoki menyudan foydalaning:", reply_markup=main_menu(uid))

async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if await check_sub(q.from_user.id, context):
        await q.delete_message()
        await context.bot.send_message(q.from_user.id, "🎬 Xush kelibsiz!\n\n🔢 Kino kodini yuboring:", reply_markup=main_menu(q.from_user.id))
    else:
        await q.answer("❌ Obuna bo'lmagansiz!", show_alert=True)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin emassiz!")
        return
    await update.message.reply_text("👑 Admin Panel", reply_markup=admin_kb())

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    txt = update.message.text.strip()
    
    if txt == "🎬 Kino qo'shish":
        context.user_data['add_movie'] = True
        context.user_data['m_step'] = 'code'
        await update.message.reply_text("🔢 Kino kodini yuboring:")
    elif txt == "📹 Qism qo'shish":
        context.user_data['add_part'] = True
        context.user_data['p_step'] = 'code'
        await update.message.reply_text("🔢 Kino kodini yuboring:")
    elif txt == "📋 Kinolar ro'yxati":
        movies = db.get_all_movies()
        if not movies:
            await update.message.reply_text("📭 Kinolar yo'q!")
            return
        text = "📋 Kinolar:\n\n"
        for code, m in movies.items():
            text += f"🎬 {code} | {m['name']} | ⭐{m['rating']}\n"
        await update.message.reply_text(text)
    elif txt == "🗑 Kino o'chirish":
        context.user_data['delete_movie'] = True
        await update.message.reply_text("🗑 O'chirish uchun kino kodini yuboring:")
    elif txt == "📊 Statistika":
        s = db.get_stats()
        await update.message.reply_text(f"📊 Statistika\n\n👥 Foydalanuvchilar: {s['users']}\n🎬 Kinolar: {s['movies']}\n👁 Ko'rishlar: {s['views']}\n💎 PRO: {s['pro']}\n💬 Fikrlar: {s['comments']}")
    elif txt == "🏠 Asosiy menyu":
        await update.message.reply_text("🏠 Asosiy menyu", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True))
    elif context.user_data.get('delete_movie'):
        if db.delete_movie(txt):
            await update.message.reply_text(f"✅ Kino o'chirildi: {txt}", reply_markup=admin_kb())
        else:
            await update.message.reply_text("❌ Kino topilmadi!")
        context.user_data['delete_movie'] = False
    elif context.user_data.get('add_movie'):
        step = context.user_data.get('m_step')
        if step == 'code':
            context.user_data['m_code'] = txt; context.user_data['m_step'] = 'name'
            await update.message.reply_text("📝 Kino nomini yuboring:")
        elif step == 'name':
            context.user_data['m_name'] = txt; context.user_data['m_step'] = 'desc'
            await update.message.reply_text("📄 Tavsifni yuboring:")
        elif step == 'desc':
            context.user_data['m_desc'] = txt; context.user_data['m_step'] = 'genre'
            await update.message.reply_text("🎭 Janrni yuboring (vergul bilan):")
        elif step == 'genre':
            context.user_data['m_genre'] = txt; context.user_data['m_step'] = 'parts'
            await update.message.reply_text("🎞 Qismlar sonini yuboring:")
        elif step == 'parts':
            try:
                parts = int(txt)
                context.user_data['m_parts'] = parts; context.user_data['m_step'] = 'photo'
                await update.message.reply_text("🖼 Kino rasmini yuboring (yoki /skip):")
            except:
                await update.message.reply_text("❌ Raqam kiriting!")
    elif context.user_data.get('add_part'):
        step = context.user_data.get('p_step')
        if step == 'code':
            movie = db.get_movie(txt)
            if not movie:
                await update.message.reply_text("❌ Kino topilmadi!"); context.user_data['add_part'] = False
                return
            context.user_data['p_code'] = txt; context.user_data['p_step'] = 'num'
            await update.message.reply_text(f"🔢 Qism raqamini yuboring (1-{movie['parts_count']}):")
        elif step == 'num':
            try:
                part_num = int(txt)
                context.user_data['p_num'] = part_num; context.user_data['p_step'] = 'video'
                await update.message.reply_text("📹 Video yuboring:")
            except:
                await update.message.reply_text("❌ Raqam kiriting!")

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    if context.user_data.get('add_movie') and context.user_data.get('m_step') == 'photo':
        photo_id = update.message.photo[-1].file_id
        db.add_movie(context.user_data['m_code'], context.user_data['m_name'], context.user_data['m_desc'], context.user_data['m_genre'], context.user_data['m_parts'], photo_id)
        await update.message.reply_text(f"✅ Kino qo'shildi!\n🎬 Kod: {context.user_data['m_code']}\n📝 Nomi: {context.user_data['m_name']}", reply_markup=admin_kb())
        context.user_data['add_movie'] = False

async def handle_admin_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    if context.user_data.get('add_part') and context.user_data.get('p_step') == 'video':
        video_id = update.message.video.file_id
        db.add_part(context.user_data['p_code'], context.user_data['p_num'], video_id)
        await update.message.reply_text(f"✅ Qism qo'shildi!\n🎬 Kino: {context.user_data['p_code']}\n📹 Qism: {context.user_data['p_num']}", reply_markup=admin_kb())
        context.user_data['add_part'] = False

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.user_data.get('add_movie') and context.user_data.get('m_step') == 'photo':
        db.add_movie(context.user_data['m_code'], context.user_data['m_name'], context.user_data['m_desc'], context.user_data['m_genre'], context.user_data['m_parts'])
        await update.message.reply_text(f"✅ Kino qo'shildi!\n📝 Nomi: {context.user_data['m_name']}", reply_markup=admin_kb())
        context.user_data['add_movie'] = False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    if uid == ADMIN_ID:
        admin_texts = ["🎬 Kino qo'shish", "📹 Qism qo'shish", "📋 Kinolar ro'yxati", "🗑 Kino o'chirish", "📊 Statistika", "🏠 Asosiy menyu"]
        if txt in admin_texts or context.user_data.get('add_movie') or context.user_data.get('add_part') or context.user_data.get('delete_movie'):
            await handle_admin_text(update, context)
            return
    
    if not await check_sub(uid, context):
        await update.message.reply_text(f"❌ Iltimos, avval {CHANNEL} kanaliga obuna bo'ling!\n/start bosing.")
        return
    
    movie = db.get_movie(txt)
    if movie:
        await show_movie(update, txt, movie, uid)
        return
    
    if context.user_data.get('searching'):
        movies = db.search_by_name(txt)
        if movies:
            kb = [[InlineKeyboardButton(f"🎬 {m['name'][:30]}", callback_data=f"mv_{m['code']}")] for m in movies[:10]]
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
            await update.message.reply_text(f"🔍 '{txt}' bo'yicha topildi:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("❌ Topilmadi!")
        context.user_data['searching'] = False
        return
    
    if context.user_data.get('commenting'):
        db.add_comment(context.user_data['commenting'], uid, update.effective_user.first_name, txt)
        await update.message.reply_text("✅ Fikringiz qabul qilindi!")
        context.user_data['commenting'] = None
        return
    
    await update.message.reply_text("❌ Kino topilmadi! Kod yoki /start bosing.")

async def show_movie(update, code, movie, uid):
    db.add_view(code)
    user_rating = db.get_user_rating(code, uid)
    
    text = f"🎬 {movie['name']}\n\n📝 {movie.get('desc', '')[:300]}\n\n⭐ Reyting: {movie['rating']}/5\n🎭 Janr: {movie['genre']}\n🔢 Kod: {code}\n🎞 Qismlar: {movie['parts_count']}\n👁 Ko'rishlar: {movie['views']}\n📅 Qo'shilgan: {movie['added']}"
    
    kb = []
    
    if user_rating is None:
        kb.append([InlineKeyboardButton(f"⭐{i}", callback_data=f"rt_{code}_{i}") for i in range(1, 6)])
    else:
        kb.append([InlineKeyboardButton(f"✅ Sizning baho: {user_rating}⭐", callback_data="no")])
    
    parts_row = [InlineKeyboardButton(f"▶️{i}", callback_data=f"pt_{code}_{i}") for i in range(1, movie['parts_count'] + 1) if str(i) in movie.get("parts", {})]
    if parts_row:
        kb.append(parts_row)
    
    kb.append([InlineKeyboardButton("💬 Fikr yozish", callback_data=f"cm_{code}"), InlineKeyboardButton("📋 Fikrlar", callback_data=f"cms_{code}")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
    
    if movie.get("photo"):
        await update.message.reply_photo(movie["photo"], caption=text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    
    if d == "check_sub":
        await check_sub_callback(update, context)
        return
    
    if not await check_sub(uid, context):
        await q.answer("❌ Avval obuna bo'ling!", show_alert=True)
        return
    
    if d == "code":
        await q.edit_message_text("🔢 Kino kodini yuboring:")
    elif d == "name":
        context.user_data['searching'] = True
        await q.edit_message_text("🔤 Kino nomini yuboring:")
    elif d == "genres":
        genres = db.get_genres()
        if not genres:
            await q.edit_message_text("📭 Janrlar yo'q!")
            return
        kb = [[InlineKeyboardButton(f"🎭 {g}", callback_data=f"gn_{g}")] for g in genres[:20]]
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
        await q.edit_message_text("🎭 Janrni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("gn_"):
        genre = d.replace("gn_", "")
        movies = db.search_by_genre(genre)
        if movies:
            kb = [[InlineKeyboardButton(f"🎬 {m['name'][:30]}", callback_data=f"mv_{m['code']}")] for m in movies[:10]]
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="genres")])
            await q.edit_message_text(f"🎭 '{genre}' janridagi kinolar:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text("📭 Kinolar yo'q!")
    elif d == "topr":
        movies = db.get_top_rated(10)
        text = "⭐ TOP 10 Reyting:\n\n"
        kb = []
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - ⭐{m['rating']}\n"
            kb.append([InlineKeyboardButton(f"{i}. 🎬 {m['name'][:25]}", callback_data=f"mv_{m['code']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif d == "topv":
        movies = db.get_top_viewed(10)
        text = "🔥 TOP 10 Ko'rilgan:\n\n"
        kb = []
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - 👁{m['views']}\n"
            kb.append([InlineKeyboardButton(f"{i}. 🎬 {m['name'][:25]}", callback_data=f"mv_{m['code']}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main")])
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif d == "stats":
        s = db.get_stats()
        text = f"📊 Statistika\n\n👥 {s['users']} | 🎬 {s['movies']} | 👁 {s['views']}\n💎 {s['pro']} | 💬 {s['comments']}"
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="main")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("mv_"):
        code = d.replace("mv_", "")
        movie = db.get_movie(code)
        if movie:
            await q.delete_message()
            await show_movie(update, code, movie, uid)
    elif d.startswith("rt_"):
        code, stars = d.split("_")[1], int(d.split("_")[2])
        db.add_rating(code, uid, stars)
        await q.answer(f"⭐ {stars} yulduz!")
        movie = db.get_movie(code)
        if movie:
            await show_movie(update, code, movie, uid)
    elif d.startswith("pt_"):
        code, part_num = d.split("_")[1], d.split("_")[2]
        movie = db.get_movie(code)
        if movie and part_num in movie.get("parts", {}):
            await q.message.reply_video(movie["parts"][part_num], caption=f"🎬 {movie['name']} - {part_num}-qism")
            await q.answer("✅ Tayyor!")
    elif d.startswith("cm_"):
        context.user_data['commenting'] = d.replace("cm_", "")
        await q.edit_message_text("💬 Fikringizni yozing:")
    elif d.startswith("cms_"):
        code = d.replace("cms_", "")
        comments = db.get_comments(code)
        text = "💬 Fikrlar:\n\n" + "\n".join([f"👤 {c['name']}: {c['text']}\n📅 {c['date']}\n➖➖➖" for c in comments[-10:]]) if comments else "📭 Fikrlar yo'q!"
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data=f"mv_{code}")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    elif d == "pro_buy":
        context.user_data['buying_pro'] = True
        text = f"👑 NexMovie Pro\n\n💰 Narxi: {PRO_PRICE}\n💳 Karta: <code>{CARD}</code>\n\n📸 To'lov qilib, <b>chek rasmini</b> shu yerga yuboring!"
        await q.edit_message_text(text, parse_mode='HTML')
    elif d == "pro_ok":
        await q.answer("💎 Siz PRO foydalanuvchisisiz!", show_alert=True)
    elif d == "main":
        await q.edit_message_text("🎬 Asosiy menyu:", reply_markup=main_menu(uid))
    elif d == "no":
        await q.answer("✅ Siz allaqachon baholagansiz!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if uid == ADMIN_ID:
        if context.user_data.get('add_movie') and context.user_data.get('m_step') == 'photo':
            await handle_admin_photo(update, context)
        return
    
    if context.user_data.get('buying_pro'):
        photo = update.message.photo[-1]
        kb = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"app_{uid}"), InlineKeyboardButton("❌ Bekor", callback_data=f"rej_{uid}")]]
        await context.bot.send_photo(ADMIN_ID, photo.file_id, caption=f"📩 PRO so'rovi\n👤 {update.effective_user.first_name}\n🆔 <code>{uid}</code>\n💰 {PRO_PRICE}", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        db.add_payment(uid, update.effective_user.first_name)
        await update.message.reply_text("✅ Chek yuborildi! Admin tasdiqlaydi.\n\n<i>Tez orada PRO aktivlashtiriladi</i>", parse_mode='HTML')
        context.user_data['buying_pro'] = False
        return

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    if q.from_user.id != ADMIN_ID:
        return
    if d.startswith("app_"):
        target = d.replace("app_", "")
        if db.add_pro(target):
            try:
                await context.bot.send_message(int(target), "🎉 Tabriklaymiz! PRO aktivlashtirildi!\n\n/start bosib tekshiring.")
            except:
                pass
            await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ TASDIQLANDI!")
        else:
            await q.answer("Allaqachon PRO!", show_alert=True)
    elif d.startswith("rej_"):
        target = d.replace("rej_", "")
        try:
            await context.bot.send_message(int(target), "❌ To'lov rad etildi. Qaytadan urinib ko'ring.")
        except:
            pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n❌ RAD ETILDI!")

def main():
    Thread(target=run_flask).start()
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_cmd))
    app_bot.add_handler(CommandHandler("skip", skip_photo))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.add_handler(MessageHandler(filters.VIDEO, handle_admin_video))
    app_bot.add_handler(CallbackQueryHandler(admin_approve, pattern="^(app_|rej_)"))
    app_bot.add_handler(CallbackQueryHandler(callback))
    print("✅ Bot ishga tushdi!")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
