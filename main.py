import os
import re
import time
import logging
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions

# Load environment variables
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
PORT = int(os.getenv("PORT", "8080"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize bot client
bot = Client(name="guardian_bot",
             api_id=API_ID,
             api_hash=API_HASH,
             bot_token=BOT_TOKEN)

# Flask app for keepalive
app = Flask(__name__)


@app.route("/")
def home():
    return "🤖 Bot is running!"


def run_web():
    app.run(host="0.0.0.0", port=PORT)


# Start Flask in a separate thread
Thread(target=run_web, daemon=True).start()

# In-memory store for warnings: key = (chat_id, user_id)
warnings_store = {}

# Forbidden content lists
BAD_WORDS = {
    # Arabic profanity
    "قذر",
    "وسخ",
    "نجس",
    "ديوث",
    "ديوس",
    "خنيث",
    "مخنث",
    "مخنثين",
    "منيوك",
    "منيوكه",
    "منيوكة",
    "قحاب",
    "قحبة",
    "قحب",
    "شرموطة",
    "شرموته",
    "شراميط",
    "عرص",
    "عرصة",
    "عراص",
    "زاني",
    "زانية",
    "زنا",
    "لوطي",
    "لوطية",
    "سحاق",
    "سحاقية",
    "سحاقيات",
    "نيك",
    "نايك",
    "ينيك",
    "تناك",
    "متناك",
    "متناكة",
    "زب",
    "زبي",
    "زبه",
    "زبيبة",
    "كس",
    "كسي",
    "كسمك",
    "كسم",
    "كساك",
    "طيز",
    "طيزي",
    "طيزها",
    "طيزه",
    "يمصكس",
    "يمص زب",
    "مصزب",
    "مص كس",
    "ابنكلب",
    "ابنحمار",
    "ابنزانية",
    "ابنقحبة",
    "تيس",
    "بغل",
    "خنزير",
    "خنزيرة",
    "خنازير",
    "حمار",
    "كلب",
    "كلبه",
    "كلاب",
    # English profanity
    "fuck",
    "fucking",
    "motherfucker",
    "shit",
    "shitty",
    "bitch",
    "bitches",
    "asshole",
    "dick",
    "dicks",
    "pussy",
    "pussies",
    "slut",
    "sluts",
    "whore",
    "whores",
    "hoe",
    "hoes",
    "cum",
    "cumming",
    "suckmydick",
    "blowjob",
    "handjob",
    "porn",
    "porno",
    "pornhub",
    "naked",
    "nudes",
    "nsfw",
    "boobs",
    "vagina",
    "penis",
    "anal",
    "oral",
    "hardcore",
    "softcore",
    "gay",
    "gays",
    "lesbian",
    "lesbians",
    "shemale",
    "tranny",
    "masturbate",
    "masturbation",
    "jerkoff",
    "orgasm",
    "fetish",
    "bdsm",
    "69",
    "cock",
    "cocks",
    "balls",
    "testicles",
    "sperm",
    "semen",
    # Drugs
    "شبو",
    "شبو مخدر",
    "حشيش",
    "حشيشه",
    "زطلة",
    "زطله",
    "قات",
    "مضغ قات",
    "شمة",
    "شمام",
    "شمشمام",
    "مخدرات",
    "مخدر",
    "مخدر قوي",
    "هيروين",
    "كوكايين",
    "كوكاين",
    "ترامادول",
    "حبوبمخدرة",
    "كحول",
    "كحولية",
    "خمر",
    "خمور",
    "سكران",
    "مخمور",
    "عرقمسكر",
    "عرق",
    "بودرةبيضاء",
    # Porn/sex services
    "مواقعاباحية",
    "رابطاباحي",
    "جروباتجنسية",
    "قروباتجنسية",
    "جروبجنسي",
    "تبادلجنسي",
    "صورجنسية",
    "مشاهدجنسية",
    # Spam/ads
    "ترويج",
    "بيعمتابعين",
    "زيادمتابعين",
    "تبادللايكات",
    "لايكفولو",
    "رشقمتابعين",
    "حساباتوهمية",
    "موقعمشبوه",
    "رابطمشبوه",
    "مروجمخدرات",
    "ترويجمخدرات",
    "بيعمخدرات"
}
BAD_DOMAINS = {
    "pornhub", "xnxx", "xvideos", "xhamster", "onlyfans", "redtube", "youjizz",
    "brazzers", "chaturbate", "livejasmin", "tnaflix", "hentai"
}
BAD_EMOJIS = {"🍑", "🍆", "💦", "👙", "🍒", "👅", "👄", "😈", "👠", "🐍"}

# Helper: log actions


def log_action(chat_id, text):
    if LOG_CHANNEL:
        try:
            bot.send_message(LOG_CHANNEL, f"[LOG] {text}")
        except Exception as e:
            logger.error(f"Logging failed: {e}")


# Issue warning / penalties
def warn_user(message):
    chat_id = message.chat.id
    user = message.from_user
    key = (chat_id, user.id)
    count = warnings_store.get(key, 0) + 1
    warnings_store[key] = count
    mention = user.mention()
    if count == 1:
        bot.send_message(chat_id, f"⚠️ تم تحذير {mention} (1/3)")
    elif count == 2:
        bot.send_message(chat_id,
                         f"⚠️ تحذير ثاني لـ{mention} (2/3). كتم 5 دقائق.")
        bot.restrict_chat_member(chat_id,
                                 user.id,
                                 ChatPermissions(),
                                 until_date=int(time.time() + 300))
    else:
        bot.send_message(chat_id, f"🚫 تم حظر {mention} نهائياً (3/3).")
        bot.ban_chat_member(chat_id, user.id)
        warnings_store.pop(key, None)
    log_action(chat_id, f"Warning {count}/3 for {mention}")


# Filter forbidden words
def filter_and_warn(client, message):
    text = message.text or ""
    lower = text.lower()
    # Direct matches
    for word in BAD_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", lower):
            message.delete()
            warn_user(message)
            return True
    # Obfuscated matches
    cleaned = re.sub(r"\W+", "", lower)
    for word in BAD_WORDS:
        if word in cleaned:
            message.delete()
            warn_user(message)
            return True
    return False


# Filter forbidden links
def block_links(client, message):
    text = message.text or ""
    lower = text.lower()
    if re.search(r"(https?://|www\.|t\.me/)", lower):
        for domain in BAD_DOMAINS:
            if domain in lower:
                message.delete()
                bot.send_message(message.chat.id, "⛔ روابط غير مسموح بها.")
                log_action(message.chat.id, f"Blocked domain {domain}")
                return True
        message.delete()
        bot.send_message(message.chat.id, "⛔ روابط غير مسموح بها.")
        log_action(message.chat.id, "Blocked general link")
        return True
    return False


# Main message handler\@bot.on_message(filters.group & ~filters.service)
def moderate(client, message):
    if message.text:
        if filter_and_warn(client, message):
            return
        if block_links(client, message):
            return


# Welcome new members
@bot.on_message(filters.new_chat_members)
def welcome(client, message):
    for m in message.new_chat_members:
        client.send_message(message.chat.id, f"👋 مرحباً {m.mention()}!")


# Check admin status
async def is_admin(chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ("creator", "administrator")


# Admin commands
@bot.on_message(filters.command("حظر") & filters.reply & filters.group)
async def cmd_ban(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    t = message.reply_to_message.from_user
    await client.ban_chat_member(message.chat.id, t.id)
    await message.reply(f"🚫 تم حظر {t.mention()}.")
    log_action(message.chat.id, f"Ban {t.id} by {message.from_user.id}")


@bot.on_message(filters.command("طرد") & filters.reply & filters.group)
async def cmd_kick(client, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return
    t = message.reply_to_message.from_user
    await client.kick_chat_member(message.chat.id, t.id)
    await client.unban_chat_member(message.chat.id, t.id)
    await message.reply(f"👢 تم طرد {t.mention()}.")
    log_action(message.chat.id, f"Kick {t.id} by {message.from_user.id}")


# ... باقي أوامر المشرفين بنفس النمط ...


# Run forever with auto-restart on crash
def run_forest():
    while True:
        try:
            bot.run()
        except Exception as e:
            logger.error(f"Crash: {e}", exc_info=True)
            time.sleep(10)


if __name__ == "__main__":
    run_forest()
