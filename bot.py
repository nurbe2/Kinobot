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
    return "NexMovie Bot"

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
CHANNEL = "@Vexron_stars"
PRO_PRICE = "14.000 som"
CARD = "4916 9903 1619 3280"
DATA_FILE = "/tmp/nexmovie.json"

class DB:
    def __init__(self):
        self.d = {"movies": {}, "users": {}, "comments": {}, "ratings": {}, "pro": []}
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
        code = str(code)
        self.d["movies"][code] = {
            "name": name,
            "desc": desc,
            "genre": genre,
            "parts_count": int(parts),
            "parts": {},
            "rating": 0,
            "views": 0,
            "photo": photo,
            "added": datetime.now().strftime("%Y-%m-%d")
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
        code = str(code)
        user_id = str(user_id)
        if "ratings" not in self.d:
            self.d["ratings"] = {}
        if code not in self.d["ratings"]:
            self.d["ratings"][code] = {}
        self.d["ratings"][code][user_id] = stars
        ratings = list(self.d["ratings"][code].values())
        self.d["movies"][code]["rating"] = round(sum(ratings) / len(ratings), 1)
        self.save()
    
    def get_user_rating(self, code, user_id):
        return self.d.get("ratings", {}).get(str(code), {}).get(str(user_id))
    
    def add_comment(self, code, user_id, name, text):
        code = str(code)
        if "comments" not in self.d:
            self.d["comments"] = {}
        if code not in self.d["comments"]:
            self.d["comments"][code] = []
        self.d["comments"][code].append({
            "user_id": str(user_id),
            "name": name,
            "text": text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        self.d["comments"][code] = self.d["comments"][code][-50:]
        self.save()
    
    def get_comments(self, code, limit=10):
        return self.d.get("comments", {}).get(str(code), [])[-limit:]
    
    def is_pro(self, uid):
        return str(uid) in self.d.get("pro", [])
    
    def add_pro(self, uid):
        uid = str(uid)
        if "pro" not in self.d:
            self.d["pro"] = []
        if uid not in self.d["pro"]:
            self.d["pro"].append(uid)
            self.save()
    
    def get_genres(self):
        genres = set()
        for m in self.d["movies"].values():
            for g in m["genre"].split(","):
                genres.add(g.strip())
        return sorted(genres)
    
    def get_stats(self):
        return {
            "movies": len(self.d.get("movies", {})),
            "users": len(self.d.get("users", {})),
            "pro": len(self.d.get("pro", [])),
            "views": sum(m["views"] for m in self.d["movies"].values()),
            "comments": sum(len(c) for c in self.d.get("comments", {}).values())
        }

db = DB()

def main_menu(uid):
    kb = [
        [InlineKeyboardButton("Kod boyicha qidirish", callback_data="code")],
        [InlineKeyboardButton("Nomi boyicha qidirish", callback_data="name")],
        [InlineKeyboardButton("Janr boyicha qidirish", callback_data="genres")],
        [InlineKeyboardButton("TOP Reyting", callback_data="topr")],
        [InlineKeyboardButton("TOP Korilgan", callback_data="topv")],
        [InlineKeyboardButton("Statistika", callback_data="stats")],
    ]
    if db.is_pro(uid):
        kb.append([InlineKeyboardButton("PRO Aktiv", callback_data="pro_ok")])
    else:
        kb.append([InlineKeyboardButton(f"PRO - {PRO_PRICE}", callback_data="pro_buy")])
    return InlineKeyboardMarkup(kb)

def admin_kb():
    return ReplyKeyboardMarkup([
        [KeyboardButton("Kino qoshish"), KeyboardButton("Qism qoshish")],
        [KeyboardButton("Kinolar royxati"), KeyboardButton("Statistika")],
        [KeyboardButton("Asosiy menyu")],
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    
    db.d["users"][str(uid)] = {"name": name, "joined": datetime.now().strftime("%Y-%m-%d")}
    db.save()
    
    if uid == ADMIN_ID:
        await update.message.reply_text(
            f"NexMovie Bot\n\nSalom, {name}!\n\n/admin - Admin panel",
            reply_markup=main_menu(uid),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"NexMovie Bot\n\nSalom, {name}!\n\nKino kodini yuboring yoki menyudan foydalaning:",
            reply_markup=main_menu(uid),
            parse_mode='HTML'
        )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        "Admin Panel",
        reply_markup=admin_kb(),
        parse_mode='HTML'
    )

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    
    txt = update.message.text.strip()
    
    if txt == "Kino qoshish":
        context.user_data['add_movie'] = True
        context.user_data['m_step'] = 'code'
        await update.message.reply_text("Kino kodini yuboring:\nMasalan: 101")
    
    elif txt == "Qism qoshish":
        context.user_data['add_part'] = True
        context.user_data['p_step'] = 'code'
        await update.message.reply_text("Kino kodini yuboring:")
    
    elif txt == "Kinolar royxati":
        movies = db.get_all_movies()
        if not movies:
            await update.message.reply_text("Kinolar yoq!")
            return
        text = "Kinolar:\n\n"
        for code, m in movies.items():
            text += f"{code} | {m['name']} | {m['rating']}\n"
        await update.message.reply_text(text)
    
    elif txt == "Statistika":
        s = db.get_stats()
        await update.message.reply_text(
            f"Statistika\n\n"
            f"Foydalanuvchilar: {s['users']}\n"
            f"Kinolar: {s['movies']}\n"
            f"Korishlar: {s['views']}\n"
            f"PRO: {s['pro']}\n"
            f"Fikrlar: {s['comments']}"
        )
    
    elif txt == "Asosiy menyu":
        await update.message.reply_text(
            "Asosiy menyu",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/start")]], resize_keyboard=True)
        )
    
    elif context.user_data.get('add_movie'):
        step = context.user_data.get('m_step')
        
        if step == 'code':
            context.user_data['m_code'] = txt
            context.user_data['m_step'] = 'name'
            await update.message.reply_text("Kino nomini yuboring:")
        
        elif step == 'name':
            context.user_data['m_name'] = txt
            context.user_data['m_step'] = 'desc'
            await update.message.reply_text("Tavsifni yuboring:")
        
        elif step == 'desc':
            context.user_data['m_desc'] = txt
            context.user_data['m_step'] = 'genre'
            await update.message.reply_text("Janrni yuboring:\nMasalan: Jangari, Drama")
        
        elif step == 'genre':
            context.user_data['m_genre'] = txt
            context.user_data['m_step'] = 'parts'
            await update.message.reply_text("Qismlar sonini yuboring:\nMasalan: 12")
        
        elif step == 'parts':
            try:
                parts = int(txt)
                context.user_data['m_parts'] = parts
                context.user_data['m_step'] = 'photo'
                await update.message.reply_text("Kino rasmini yuboring (yoki /skip):")
            except:
                await update.message.reply_text("Raqam kiriting!")
    
    elif context.user_data.get('add_part'):
        step = context.user_data.get('p_step')
        
        if step == 'code':
            context.user_data['p_code'] = txt
            context.user_data['p_step'] = 'num'
            await update.message.reply_text("Qism raqamini yuboring:\nMasalan: 1")
        
        elif step == 'num':
            try:
                part_num = int(txt)
                context.user_data['p_num'] = part_num
                context.user_data['p_step'] = 'video'
                await update.message.reply_text("Video yuboring:")
            except:
                await update.message.reply_text("Raqam kiriting!")

async def handle_admin_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    
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
            f"Kino qoshildi!\nKod: {context.user_data['m_code']}\nNomi: {context.user_data['m_name']}",
            reply_markup=admin_kb()
        )
        context.user_data['add_movie'] = False

async def handle_admin_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return
    
    if context.user_data.get('add_part') and context.user_data.get('p_step') == 'video':
        video_id = update.message.video.file_id
        code = context.user_data['p_code']
        part_num = context.user_data['p_num']
        
        db.add_part(code, part_num, video_id)
        
        await update.message.reply_text(
            f"Qism qoshildi!\nKino: {code}\nQism: {part_num}",
            reply_markup=admin_kb()
        )
        context.user_data['add_part'] = False

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.user_data.get('add_movie') and context.user_data.get('m_step') == 'photo':
        db.add_movie(
            context.user_data['m_code'],
            context.user_data['m_name'],
            context.user_data['m_desc'],
            context.user_data['m_genre'],
            context.user_data['m_parts']
        )
        await update.message.reply_text(
            f"Kino qoshildi!\nNomi: {context.user_data['m_name']}",
            reply_markup=admin_kb()
        )
        context.user_data['add_movie'] = False

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txt = update.message.text.strip()
    
    if uid == ADMIN_ID:
        admin_texts = ["Kino qoshish", "Qism qoshish", "Kinolar royxati", "Statistika", "Asosiy menyu"]
        if txt in admin_texts or context.user_data.get('add_movie') or context.user_data.get('add_part'):
            await handle_admin_text(update, context)
            return
    
    movie = db.get_movie(txt)
    if movie:
        await show_movie(update, txt, movie, uid)
        return
    
    if context.user_data.get('searching'):
        movies = db.search_by_name(txt)
        if movies:
            text = f"Qidiruv: {txt}\n\n"
            kb = []
            for m in movies[:10]:
                text += f"{m['code']} - {m['name']}\n"
                kb.append([InlineKeyboardButton(m['name'][:30], callback_data=f"mv_{m['code']}")])
            kb.append([InlineKeyboardButton("Orqaga", callback_data="main")])
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await update.message.reply_text("Topilmadi!")
        context.user_data['searching'] = False
        return
    
    if context.user_data.get('commenting'):
        code = context.user_data['commenting']
        db.add_comment(code, uid, update.effective_user.first_name, txt)
        await update.message.reply_text("Fikringiz qabul qilindi!")
        context.user_data['commenting'] = None
        return
    
    await update.message.reply_text("Kino topilmadi! Kodni tekshiring.")

async def show_movie(update, code, movie, uid):
    db.add_view(code)
    comments = db.get_comments(code)
    user_rating = db.get_user_rating(code, uid)
    
    text = f"{movie['name']}\n\n"
    text += f"{movie.get('desc', '')[:200]}\n"
    text += f"Reyting: {movie['rating']}/5\n"
    text += f"Janr: {movie['genre']}\n"
    text += f"Kod: {code}\n"
    text += f"Qismlar: {movie['parts_count']}\n"
    text += f"Korishlar: {movie['views']}"
    
    kb = []
    
    if user_rating is None:
        stars_row = []
        for i in range(1, 6):
            stars_row.append(InlineKeyboardButton(str(i), callback_data=f"rt_{code}_{i}"))
        kb.append(stars_row)
    else:
        kb.append([InlineKeyboardButton(f"Siz: {user_rating} yulduz", callback_data="no")])
    
    parts_row = []
    for i in range(1, movie['parts_count'] + 1):
        if str(i) in movie.get("parts", {}):
            parts_row.append(InlineKeyboardButton(str(i), callback_data=f"pt_{code}_{i}"))
    if parts_row:
        kb.append(parts_row)
    
    kb.append([
        InlineKeyboardButton("Fikr yozish", callback_data=f"cm_{code}"),
        InlineKeyboardButton("Fikrlar", callback_data=f"cms_{code}")
    ])
    kb.append([InlineKeyboardButton("Orqaga", callback_data="main")])
    
    if movie.get("photo"):
        await update.message.reply_photo(movie["photo"], caption=text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    
    if d == "code":
        await q.edit_message_text("Kino kodini yuboring:")
    
    elif d == "name":
        context.user_data['searching'] = True
        await q.edit_message_text("Kino nomini yuboring:")
    
    elif d == "genres":
        genres = db.get_genres()
        if not genres:
            await q.edit_message_text("Janrlar yoq!"); return
        kb = []
        for g in genres[:20]:
            kb.append([InlineKeyboardButton(g, callback_data=f"gn_{g}")])
        kb.append([InlineKeyboardButton("Orqaga", callback_data="main")])
        await q.edit_message_text("Janrni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif d.startswith("gn_"):
        genre = d.replace("gn_", "")
        movies = db.search_by_genre(genre)
        if movies:
            text = f"{genre} kinolari:\n\n"
            kb = []
            for m in movies[:10]:
                text += f"{m['code']} - {m['name']}\n"
                kb.append([InlineKeyboardButton(m['name'][:30], callback_data=f"mv_{m['code']}")])
            kb.append([InlineKeyboardButton("Orqaga", callback_data="genres")])
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await q.edit_message_text("Kinolar yoq!")
    
    elif d == "topr":
        movies = db.get_top_rated(10)
        text = "TOP 10 Reyting:\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - {m['rating']}\n"
        await q.edit_message_text(text)
    
    elif d == "topv":
        movies = db.get_top_viewed(10)
        text = "TOP 10 Korilgan:\n\n"
        for i, m in enumerate(movies, 1):
            text += f"{i}. {m['name']} - {m['views']}\n"
        await q.edit_message_text(text)
    
    elif d == "stats":
        s = db.get_stats()
        await q.edit_message_text(
            f"Statistika\n\n"
            f"Foydalanuvchilar: {s['users']}\n"
            f"Kinolar: {s['movies']}\n"
            f"Korishlar: {s['views']}\n"
            f"PRO: {s['pro']}\n"
            f"Fikrlar: {s['comments']}"
        )
    
    elif d.startswith("mv_"):
        code = d.replace("mv_", "")
        movie = db.get_movie(code)
        if movie:
            await show_movie(update, code, movie, uid)
    
    elif d.startswith("rt_"):
        parts = d.split("_")
        code, stars = parts[1], int(parts[2])
        db.add_rating(code, uid, stars)
        await q.answer(f"{stars} yulduz!")
        movie = db.get_movie(code)
        if movie:
            await show_movie(update, code, movie, uid)
    
    elif d.startswith("pt_"):
        parts = d.split("_")
        code, part_num = parts[1], parts[2]
        movie = db.get_movie(code)
        if movie and part_num in movie.get("parts", {}):
            await q.message.reply_video(movie["parts"][part_num], caption=f"{movie['name']} - {part_num}-qism")
    
    elif d.startswith("cm_"):
        code = d.replace("cm_", "")
        context.user_data['commenting'] = code
        await q.edit_message_text("Fikringizni yozing:")
    
    elif d.startswith("cms_"):
        code = d.replace("cms_", "")
        comments = db.get_comments(code)
        if comments:
            text = "Fikrlar:\n\n"
            for c in comments[-10:]:
                text += f"{c['name']}: {c['text']}\n\n"
        else:
            text = "Fikrlar yoq!"
        await q.edit_message_text(text)
    
    elif d == "pro_buy":
        context.user_data['buying_pro'] = True
        await q.edit_message_text(f"PRO narxi: {PRO_PRICE}\nKarta: {CARD}\n\nChek rasmini yuboring!")
    
    elif d == "pro_ok":
        await q.answer("PRO aktiv!", show_alert=True)
    
    elif d == "main":
        await q.edit_message_text("Menyu:", reply_markup=main_menu(uid))
    
        elif d == "no":
        await q.answer("Siz baholagansiz!")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    
    if uid == ADMIN_ID:
        await handle_admin_photo(update, context)
        return
    
    if context.user_data.get('buying_pro'):
        photo = update.message.photo[-1]
        kb = [
            [InlineKeyboardButton("Tasdiqlash", callback_data=f"app_{uid}"),
             InlineKeyboardButton("Bekor", callback_data=f"rej_{uid}")]
        ]
        await context.bot.send_photo(ADMIN_ID, photo.file_id,
            caption=f"PRO sorov\nFoydalanuvchi: {update.effective_user.first_name}\nID: {uid}",
            reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("Chek yuborildi!")
        context.user_data['buying_pro'] = False

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    uid = q.from_user.id
    
    if uid != ADMIN_ID:
        return
    
    if d.startswith("app_"):
        target = d.replace("app_", "")
        db.add_pro(target)
        try:
            await context.bot.send_message(int(target), "PRO aktivlashtirildi!")
        except:
            pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\nTASDIQLANDI!")
    
    elif d.startswith("rej_"):
        target = d.replace("rej_", "")
        try:
            await context.bot.send_message(int(target), "Rad etildi.")
        except:
            pass
        await q.edit_message_caption(caption=f"{q.message.caption}\n\nRAD ETILDI!")

def main():
    Thread(target=run_flask).start()
    print("NexMovie Bot ishga tushmoqda...")
    
    app_bot = Application.builder().token(BOT_TOKEN).build()
    
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_cmd))
    app_bot.add_handler(CommandHandler("skip", skip_photo))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app_bot.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app_bot.add_handler(MessageHandler(filters.VIDEO, handle_admin_video))
    app_bot.add_handler(CallbackQueryHandler(callback))
    app_bot.add_handler(CallbackQueryHandler(admin_approve, pattern="^(app_|rej_)"))
    
    print("Bot ishga tushdi!")
    app_bot.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
