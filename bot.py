import json
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlamoqda!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Sozlamalar
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8901775007:AAHzy1X8D2F0PQjwrjUJRWzTskWZYVhjAxE')
ADMIN_ID = 8306639956
CHANNEL_USERNAME = '@Vexron_stars'
CARD = "4916 9903 1619 3280"
PRO_PRICE = "14.000 so'm"
DATA_FILE = "/tmp/kino_data.json"

# Database
class DB:
    def __init__(self):
        self.d = {"kinolar": {}, "qismlar": {}, "pro": [], "reviews": {}, "ratings": {}, "users": {}}
        self.load()
    
    def load(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE) as f: self.d.update(json.load(f))
            except: pass
    
    def save(self):
        with open(DATA_FILE, 'w') as f: json.dump(self.d, f, ensure_ascii=False)
    
    def add_kino(self, kod, nomi, tavsif, reyting, tip, fayl, qism, janr):
        self.d["kinolar"][str(kod)] = {
            "nomi": nomi, "tavsif": tavsif, "reyting": reyting,
            "tip": tip, "fayl": fayl, "qism": qism, "janr": janr,
            "sana": datetime.now().strftime("%Y-%m-%d"), "korish": 0
        }
        self.save()
    
    def get_kino(self, kod):
        return self.d["kinolar"].get(str(kod))
    
    def add_qism(self, kod, qism_no, video):
        self.d["qismlar"].setdefault(str(kod), {})
        self.d["qismlar"][str(kod)][str(qism_no)] = video
        self.save()
    
    def get_qismlar(self, kod):
        return self.d["qismlar"].get(str(kod), {})
    
    def add_view(self, kod):
        if str(kod) in self.d["kinolar"]:
            self.d["kinolar"][str(kod)]["korish"] += 1
            self.save()
    
    def pro(self, uid): return str(uid) in self.d["pro"]
    
    def apro(self, uid):
        uid = str(uid)
        if uid not in self.d["pro"]:
            self.d["pro"].append(uid); self.save(); return True
        return False
    
    def add_rating(self, kod, uid, rating):
        self.d["ratings"].setdefault(str(kod), {})
        self.d["ratings"][str(kod)][str(uid)] = rating
        self.d["kinolar"][str(kod)]["reyting"] = round(
            sum(self.d["ratings"][str(kod)].values()) / len(self.d["ratings"][str(kod)]), 1
        )
        self.save()
    
    def add_review(self, kod, uid, username, matn):
        self.d["reviews"].setdefault(str(kod), [])
        self.d["reviews"][str(kod)].append({
            "uid": uid, "username": username, "matn": matn,
            "sana": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        self.save()
    
    def get_reviews(self, kod):
        return self.d["reviews"].get(str(kod), [])[-10:]
    
    def add_user(self, uid, name, username):
        self.d["users"][str(uid)] = {"name": name, "username": username}
        self.save()
    
    def top_rating(self):
        return sorted(self.d["kinolar"].items(), key=lambda x: x[1]["reyting"], reverse=True)[:10]
    
    def top_views(self):
        return sorted(self.d["kinolar"].items(), key=lambda x: x[1]["korish"], reverse=True)[:10]
    
    def search_name(self, name):
        return [(k, v) for k, v in self.d["kinolar"].items() if name.lower() in v["nomi"].lower()]
    
    def get_janrlar(self):
        janrlar = set()
        for v in self.d["kinolar"].values():
            for j in v["janr"].split(','):
                if j.strip(): janrlar.add(j.strip())
        return sorted(janrlar)
    
    def search_janr(self, janr):
        return [(k, v) for k, v in self.d["kinolar"].items() if janr.lower() in v["janr"].lower()]
    
    def stats(self):
        return {
            "users": len(self.d["users"]),
            "kinolar": len(self.d["kinolar"]),
            "views": sum(v["korish"] for v in self.d["kinolar"].values()),
            "pro": len(self.d["pro"]),
            "reviews": sum(len(v) for v in self.d["reviews"].values()),
            "ratings": sum(len(v) for v in self.d["ratings"].values())
        }

db = DB()

# Keyboardlar
def main_menu():
    kb = [
        [InlineKeyboardButton("🔍 Kod orqali", callback_data="search_code")],
        [InlineKeyboardButton("🔎 Nomi orqali", callback_data="search_name")],
        [InlineKeyboardButton("📂 Janr orqali", callback_data="search_genre")],
        [InlineKeyboardButton("⭐ TOP Reyting", callback_data="top_rating")],
        [InlineKeyboardButton("🔥 TOP Ko'rilgan", callback_data="top_views")],
        [InlineKeyboardButton("🎬 NexMovie Pro", callback_data="pro_info")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(kb)

def admin_menu():
    kb = [
        [InlineKeyboardButton("🎬 Kino qo'shish", callback_data="admin_kino")],
        [InlineKeyboardButton("📹 Qism qo'shish", callback_data="admin_qism")],
        [InlineKeyboardButton("📋 Kinolar", callback_data="admin_list")],
    ]
    return InlineKeyboardMarkup(kb)

# Handlerlar
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = update.effective_user
    db.add_user(uid, user.first_name, user.username)
    
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        if member.status in ['left', 'kicked']:
            kb = [[InlineKeyboardButton("📢 Obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                  [InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")]]
            await update.message.reply_text(f"👋 Salom!\n\n{CHANNEL_USERNAME} ga obuna bo'ling!", reply_markup=InlineKeyboardMarkup(kb))
            return
    except:
        pass
    
    pro = "PRO" if db.pro(uid) else "Oddiy"
    await update.message.reply_text(f"🎬 Xush kelibsiz!\n👤 {pro}", reply_markup=main_menu())

async def check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, uid)
        if member.status not in ['left', 'kicked']:
            await q.delete_message()
            pro = "PRO" if db.pro(uid) else "Oddiy"
            await context.bot.send_message(uid, f"🎬 Xush kelibsiz!\n👤 {pro}", reply_markup=main_menu())
        else:
            await q.answer("❌ Obuna bo'lmagansiz!", show_alert=True)
    except:
        await q.answer("❌ Xatolik!", show_alert=True)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        await update.message.reply_text("❌ Admin emassiz!"); return
    await update.message.reply_text("👑 Admin Panel", reply_markup=admin_menu())

# Admin: Kino qo'shish
async def admin_kino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data['admin_step'] = 'kino_kod'
    await q.edit_message_text("Kino kodini kiriting:")

# Admin: Qism qo'shish
async def admin_qism(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data['admin_step'] = 'qism_kod'
    await q.edit_message_text("Kino kodini kiriting:")

async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    kinolar = db.d["kinolar"]
    if not kinolar:
        await q.edit_message_text("Kinolar yo'q!"); return
    text = "📋 Kinolar:\n\n"
    for k, v in kinolar.items():
        text += f"🎬 {v['nomi']} | Kod: {k} | ⭐{v['reyting']}\n"
    await q.edit_message_text(text)

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text
    
    if uid != ADMIN_ID: return
    
    step = context.user_data.get('admin_step')
    
    if step == 'kino_kod':
        context.user_data['kino'] = {'kod': msg}
        context.user_data['admin_step'] = 'kino_nomi'
        await update.message.reply_text("Kino nomini kiriting:")
    
    elif step == 'kino_nomi':
        context.user_data['kino']['nomi'] = msg
        context.user_data['admin_step'] = 'kino_tavsif'
        await update.message.reply_text("Tavsifni kiriting:")
    
    elif step == 'kino_tavsif':
        context.user_data['kino']['tavsif'] = msg
        context.user_data['admin_step'] = 'kino_reyting'
        await update.message.reply_text("Reyting (1-10):")
    
    elif step == 'kino_reyting':
        try:
            r = float(msg)
            if r < 1 or r > 10:
                await update.message.reply_text("1-10 gacha!"); return
        except:
            await update.message.reply_text("Raqam kiriting!"); return
        context.user_data['kino']['reyting'] = r
        context.user_data['admin_step'] = 'kino_media'
        await update.message.reply_text("Rasm yoki video yuboring:")
    
    elif step == 'qism_kod':
        context.user_data['qism_kod'] = msg
        context.user_data['admin_step'] = 'qism_no'
        k = db.get_kino(msg)
        if not k:
            await update.message.reply_text("Topilmadi!"); context.user_data.pop('admin_step'); return
        await update.message.reply_text(f"Qism raqami (1-{k['qism']}):")
    
    elif step == 'qism_no':
        context.user_data['qism_no'] = msg
        context.user_data['admin_step'] = 'qism_video'
        await update.message.reply_text("Video yuboring:")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID: return
    
    step = context.user_data.get('admin_step')
    
    if step == 'kino_media':
        if update.message.photo:
            context.user_data['kino']['tip'] = 'photo'
            context.user_data['kino']['fayl'] = update.message.photo[-1].file_id
        elif update.message.video:
            context.user_data['kino']['tip'] = 'video'
            context.user_data['kino']['fayl'] = update.message.video.file_id
        else:
            await update.message.reply_text("Rasm yoki video!"); return
        
        context.user_data['admin_step'] = 'kino_qism'
        await update.message.reply_text("Qismlar soni:")
    
    elif step == 'kino_qism':
        try:
            q = int(update.message.text)
        except:
            await update.message.reply_text("Raqam!"); return
        context.user_data['kino']['qism'] = q
        context.user_data['admin_step'] = 'kino_janr'
        await update.message.reply_text("Janr (vergul bilan):")
    
    elif step == 'kino_janr':
        k = context.user_data['kino']
        db.add_kino(k['kod'], k['nomi'], k['tavsif'], k['reyting'], k['tip'], k['fayl'], k['qism'], update.message.text)
        context.user_data.pop('kino', None); context.user_data.pop('admin_step', None)
        await update.message.reply_text(f"✅ {k['nomi']} qo'shildi!")
    
    elif step == 'qism_video':
        if not update.message.video:
            await update.message.reply_text("Video yuboring!"); return
        db.add_qism(context.user_data['qism_kod'], context.user_data['qism_no'], update.message.video.file_id)
        context.user_data.pop('qism_kod', None); context.user_data.pop('qism_no', None); context.user_data.pop('admin_step', None)
        await update.message.reply_text("✅ Qism qo'shildi!")

# Qidirish
async def search_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data['search_type'] = 'code'
    await q.edit_message_text("Kino kodini kiriting:")

async def search_name_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    context.user_data['search_type'] = 'name'
    await q.edit_message_text("Kino nomini kiriting:")

async def search_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message.text
    st = context.user_data.get('search_type')
    
    if st == 'code':
        k = db.get_kino(msg)
        if not k:
            await update.message.reply_text("Topilmadi!"); return
        await send_kino(update, context, uid, msg, k)
    
    elif st == 'name':
        kinolar = db.search_name(msg)
        if not kinolar:
            await update.message.reply_text("Topilmadi!"); return
        if len(kinolar) == 1:
            await send_kino(update, context, uid, kinolar[0][0], kinolar[0][1])
        else:
            kb = []
            for k, v in kinolar:
                kb.append([InlineKeyboardButton(f"🎬 {v['nomi']} (⭐{v['reyting']})", callback_data=f"view_{k}")])
            kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
            await update.message.reply_text("Topildi:", reply_markup=InlineKeyboardMarkup(kb))

async def send_kino(update, context, uid, kod, k):
    db.add_view(kod)
    cap = f"🎬 {k['nomi']}\n\n📝 {k['tavsif']}\n⭐ {k['reyting']}/10\n📂 {k['janr']}\n🔢 {kod}\n📹 {k['qism']}\n👁 {k['korish']}"
    
    kb = []
    # Reyting
    rate_row = []
    for i in range(1, 6):
        rate_row.append(InlineKeyboardButton(str(i), callback_data=f"rate_{kod}_{i}"))
    kb.append(rate_row)
    
    # Qismlar
    qismlar = db.get_qismlar(kod)
    for qn, vid in sorted(qismlar.items(), key=lambda x: int(x[0])):
        kb.append([InlineKeyboardButton(f"📹 {qn}-qism", callback_data=f"watch_{kod}_{qn}")])
    
    kb.append([InlineKeyboardButton("💬 Fikr", callback_data=f"review_{kod}"),
               InlineKeyboardButton("📋 Fikrlar", callback_data=f"reviews_{kod}")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    
    if k['tip'] == 'photo':
        await context.bot.send_photo(uid, k['fayl'], caption=cap, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_video(uid, k['fayl'], caption=cap, reply_markup=InlineKeyboardMarkup(kb))

# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    d = q.data; uid = q.from_user.id
    
    if d == "check_sub": await check_sub(update, context)
    elif d == "main_menu":
        pro = "PRO" if db.pro(uid) else "Oddiy"
        await q.edit_message_text(f"🎬 Xush kelibsiz!\n👤 {pro}", reply_markup=main_menu())
    
    elif d == "search_code": await search_code(update, context)
    elif d == "search_name": await search_name_start(update, context)
    elif d == "search_genre": await genre_menu(update, context)
    
    elif d.startswith("view_"):
        kod = d.replace("view_", "")
        k = db.get_kino(kod)
        if k:
            await q.delete_message()
            await send_kino(update, context, uid, kod, k)
    
    elif d.startswith("rate_"):
        _, kod, rating = d.split('_')
        db.add_rating(kod, uid, int(rating))
        await q.answer(f"⭐ {rating} baholandi!")
    
    elif d.startswith("review_"):
        kod = d.replace("review_", "")
        context.user_data['review_kod'] = kod
        await q.edit_message_text("💬 Fikringizni yozing:")
    
    elif d.startswith("reviews_"):
        kod = d.replace("reviews_", "")
        revs = db.get_reviews(kod)
        if not revs:
            await q.answer("Fikrlar yo'q!", show_alert=True); return
        text = "💬 Fikrlar:\n\n"
        for r in revs:
            text += f"👤 {r['username']}: {r['matn']}\n📅 {r['sana']}\n➖➖➖➖➖\n"
        await q.edit_message_text(text)
    
    elif d.startswith("watch_"):
        _, kod, qn = d.split('_')
        qismlar = db.get_qismlar(kod)
        if qn in qismlar:
            await context.bot.send_video(uid, qismlar[qn], caption=f"📹 {qn}-qism")
    
    elif d.startswith("genre_"):
        janr = d.replace("genre_", "")
        kinolar = db.search_janr(janr)
        kb = []
        for k, v in kinolar:
            kb.append([InlineKeyboardButton(f"🎬 {v['nomi']} (⭐{v['reyting']})", callback_data=f"view_{k}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="search_genre")])
        await q.edit_message_text(f"'{janr}' janri:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif d == "top_rating":
        kinolar = db.top_rating()
        kb = []
        for k, v in kinolar:
            kb.append([InlineKeyboardButton(f"{v['nomi']} ⭐{v['reyting']}", callback_data=f"view_{k}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        await q.edit_message_text("⭐ TOP Reyting:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif d == "top_views":
        kinolar = db.top_views()
        kb = []
        for k, v in kinolar:
            kb.append([InlineKeyboardButton(f"{v['nomi']} 👁{v['korish']}", callback_data=f"view_{k}")])
        kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        await q.edit_message_text("🔥 TOP Ko'rilgan:", reply_markup=InlineKeyboardMarkup(kb))
    
    elif d == "stats":
        s = db.stats()
        text = f"📊 Statistika:\n\n👥 {s['users']}\n🎬 {s['kinolar']}\n👁 {s['views']}\n👑 {s['pro']}\n💬 {s['reviews']}\n⭐ {s['ratings']}"
        kb = [[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))
    
    elif d == "pro_info":
        if db.pro(uid):
            await q.answer("✅ Siz PROsiz!", show_alert=True); return
        kb = [[InlineKeyboardButton("💳 To'lov qildim", callback_data="pay")],
              [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]]
        await q.edit_message_text(f"💎 NexMovie Pro\n\n💰 {PRO_PRICE}\n💳 {CARD}\n\nChek yuboring!", reply_markup=InlineKeyboardMarkup(kb))
    
    elif d == "pay":
        context.user_data['waiting_check'] = True
        await q.edit_message_text("📸 Chek rasmini yuboring:")
    
    elif d.startswith("app_"):
        if uid != ADMIN_ID: return
        uid_pro = d.replace("app_", "")
        db.apro(uid_pro)
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n✅ TASDIQLANDI!")
        try: await context.bot.send_message(int(uid_pro), "🎉 PRO aktiv!")
        except: pass
    
    elif d.startswith("rej_"):
        if uid != ADMIN_ID: return
        await q.edit_message_caption(caption=f"{q.message.caption}\n\n❌ BEKOR!")
    
    elif d == "admin_kino": await admin_kino(update, context)
    elif d == "admin_qism": await admin_qism(update, context)
    elif d == "admin_list": await admin_list(update, context)

async def genre_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    janrlar = db.get_janrlar()
    if not janrlar:
        await q.answer("Kinolar yo'q!", show_alert=True); return
    kb = []
    for j in janrlar:
        kb.append([InlineKeyboardButton(f"📂 {j}", callback_data=f"genre_{j}")])
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
    await q.edit_message_text("Janrni tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def handle_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_check'): return
    user = update.effective_user
    photo = update.message.photo[-1]
    kb = [[InlineKeyboardButton("✅", callback_data=f"app_{user.id}"),
           InlineKeyboardButton("❌", callback_data=f"rej_{user.id}")]]
    await context.bot.send_photo(ADMIN_ID, photo.file_id,
        caption=f"📩 Chek!\n👤 {user.first_name}\n🆔 {user.id}\n💰 {PRO_PRICE}",
        reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Yuborildi!")
    context.user_data['waiting_check'] = False

async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kod = context.
