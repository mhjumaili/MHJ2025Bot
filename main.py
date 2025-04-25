import os
import re
import time
import logging
import asyncio
from threading import Thread
from flask import Flask
from pyrogram import Client, filters, idle
from pyrogram.types import ChatPermissions
from pyrogram.errors import FloodWait, UserAdminInvalid, ChatAdminRequired

# Load environment variables
try:
    API_ID = int(os.getenv("API_ID", "0"))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv(
        "BOT_TOKEN",
        "")  # تأكد أن هذا هو التوكن الجديد والصحيح في Replit/Render
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
    PORT = int(os.getenv("PORT",
                         "10000"))  # Render سيوفر القيمة الصحيحة تلقائيًا
except ValueError:
    logging.error("خطأ: تأكد من أن API_ID و LOG_CHANNEL و PORT أرقام صحيحة.")
    exit(1)
except Exception as e:
    logging.error(f"خطأ عند قراءة متغيرات البيئة: {e}")
    exit(1)

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logging.error(
        "خطأ: يرجى تعيين متغيرات البيئة API_ID, API_HASH, BOT_TOKEN في Replit Secrets و Render Env Vars."
    )
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize bot client
try:
    # استخدام اسم جلسة مميز
    bot = Client(name="guardian_bot_session",
                 api_id=API_ID,
                 api_hash=API_HASH,
                 bot_token=BOT_TOKEN)
except Exception as e:
    logger.error(f"فشل في تهيئة البوت: {e}")
    exit(1)

# --- Flask app for keepalive ---
app = Flask(__name__)


@app.route("/")
def home():
    # هذه الرسالة تظهر عند زيارة رابط Render
    return "🤖 Bot is running!"


def run_web():
    try:
        # الاستماع على كل الواجهات والمنفذ المحدد من Render
        logger.info(f"Starting Flask server on 0.0.0.0:{PORT}")
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        logger.error(f"Flask server failed: {e}", exc_info=True)


# --- تخزين التحذيرات (في الذاكرة) ---
warnings_store = {}

# --- قوائم الحظر (مملوءة) ---
BAD_WORDS = {
    # شتائم عربية ومشتقاتها
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
    "شرموطه",
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
    # شتائم إنجليزية ومشتقاتها
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
    # كلمات المخدرات
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
    # كلمات الإباحية والدعارة
    "مواقعاباحية",
    "رابطاباحي",
    "جروباتجنسية",
    "قروباتجنسية",
    "جروبجنسي",
    "تبادلجنسي",
    "صورجنسية",
    "مشاهدجنسية",
    # كلمات السبام والدعاية
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

BAD_EMOJIS = {"🍑", "🍆", "💦", "👙", "🍒", "👅", "👄", "😈", "👠", "🐍"}

BAD_DOMAINS = {
    "pornhub", "xnxx", "xvideos", "xhamster", "onlyfans", "redtube", "youjizz",
    "brazzers", "chaturbate", "livejasmin", "tnaflix", "hentai"
}


# --- دوال مساعدة (async) ---
async def log_action(chat_id, text):
    full_log = f"[LOG - Chat: {chat_id}] {text}"
    logger.info(full_log)
    if LOG_CHANNEL != 0:
        try:
            await bot.send_message(LOG_CHANNEL, f"📜 {full_log}")
        except Exception as e:
            logger.error(f"Logging to channel {LOG_CHANNEL} failed: {e}")


async def is_admin(chat_id, user_id):
    # ... (الكود كما هو - لا تغيير)
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("creator", "administrator")
    except UserAdminInvalid:
        return False
    except ChatAdminRequired:
        logger.warning(
            f"Bot needs admin rights in {chat_id} to check status of {user_id}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Error checking admin status for {user_id} in {chat_id}: {e}")
        return False


async def warn_user(message):
    # ... (الكود كما هو - لا تغيير)
    chat_id = message.chat.id
    user = message.from_user
    if not user: return
    key = (chat_id, user.id)
    if await is_admin(chat_id, user.id):
        logger.info(
            f"Ignoring warning for admin {user.mention()} in {chat_id}")
        return
    count = warnings_store.get(key, 0) + 1
    warnings_store[key] = count
    mention = user.mention()
    try:
        if count == 1:
            await bot.send_message(chat_id,
                                   f"⚠️ تحذير أول لـ {mention} (1/3).")
            await log_action(chat_id, f"Warning 1/3 for {mention} ({user.id})")
        elif count == 2:
            mute_duration = int(time.time() + 300)
            await bot.send_message(
                chat_id, f"⚠️ تحذير ثاني لـ {mention} (2/3). كتم 5 دقائق.")
            await bot.restrict_chat_member(chat_id,
                                           user.id,
                                           ChatPermissions(),
                                           until_date=mute_duration)
            await log_action(
                chat_id, f"Warning 2/3 (Muted 5m) for {mention} ({user.id})")
        else:
            await bot.send_message(chat_id,
                                   f"🚫 تم حظر {mention} نهائياً (3/3).")
            await bot.ban_chat_member(chat_id, user.id)
            warnings_store.pop(key, None)
            await log_action(
                chat_id, f"Warning 3/3 (Banned) for {mention} ({user.id})")
    except ChatAdminRequired:
        logger.error(
            f"Failed to warn/punish {mention} in {chat_id}: Bot lacks admin rights."
        )
    except FloodWait as e:
        logger.warning(
            f"Flood wait of {e.value}s when warning/punishing {mention}")
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Error warning/punishing {mention} in {chat_id}: {e}",
                     exc_info=True)


async def filter_and_warn(message):
    # ... (الكود كما هو - لا تغيير)
    if message.from_user and await is_admin(message.chat.id,
                                            message.from_user.id):
        return False
    text_to_check = (message.text or message.caption or "").lower()
    if not text_to_check or not BAD_WORDS: return False
    for word in BAD_WORDS:
        try:
            if not isinstance(word, str):
                logger.warning(
                    f"Skipping non-string item in BAD_WORDS: {repr(word)}")
                continue
            if re.search(rf"\b{re.escape(word)}\b", text_to_check,
                         re.IGNORECASE):
                await message.delete()
                await log_action(
                    message.chat.id,
                    f"Deleted message from {message.from_user.mention()} due to bad word: '{word}'"
                )
                await warn_user(message)
                return True
        except ChatAdminRequired:
            logger.error(
                f"Failed to delete bad word message in {message.chat.id}: Bot lacks delete permission."
            )
            return False
        except Exception as e:
            logger.error(f"Error processing bad word '{word}': {e}",
                         exc_info=True)
            continue
    return False


async def block_links(message):
    # ... (الكود كما هو - لا تغيير)
    if message.from_user and await is_admin(message.chat.id,
                                            message.from_user.id):
        return False
    text_to_check = (message.text or message.caption or "").lower()
    if not text_to_check or not BAD_DOMAINS: return False
    link_pattern = r"(https?://|www\.|t\.me/)"
    if re.search(link_pattern, text_to_check, re.IGNORECASE):
        for domain in BAD_DOMAINS:
            try:
                if not isinstance(domain, str):
                    logger.warning(
                        f"Skipping non-string item in BAD_DOMAINS: {repr(domain)}"
                    )
                    continue
                if re.search(re.escape(domain), text_to_check, re.IGNORECASE):
                    await message.delete()
                    await bot.send_message(
                        message.chat.id,
                        f"⛔️ تم حذف رابط غير مسموح به من {message.from_user.mention()}."
                    )
                    await log_action(
                        message.chat.id,
                        f"Deleted message from {message.from_user.mention()} due to forbidden domain: '{domain}'"
                    )
                    return True
            except ChatAdminRequired:
                logger.error(
                    f"Failed to delete bad link message in {message.chat.id}: Bot lacks delete permission."
                )
                return False
            except Exception as e:
                logger.error(f"Error processing bad domain '{domain}': {e}",
                             exc_info=True)
                continue
    return False


async def filter_bad_emojis(message):
    # ... (الكود كما هو - لا تغيير)
    if message.from_user and await is_admin(message.chat.id,
                                            message.from_user.id):
        return False
    text_to_check = message.text or message.caption or ""
    if not text_to_check or not BAD_EMOJIS: return False
    for emoji in BAD_EMOJIS:
        if emoji in text_to_check:
            try:
                await message.delete()
                await log_action(
                    message.chat.id,
                    f"Deleted message from {message.from_user.mention()} due to forbidden emoji: '{emoji}'"
                )
                await warn_user(message)
                return True
            except ChatAdminRequired:
                logger.error(
                    f"Failed to delete bad emoji message in {message.chat.id}: Bot lacks delete permission."
                )
                return False
            except Exception as e:
                logger.error(f"Error processing bad emoji '{emoji}': {e}",
                             exc_info=True)
                continue
    return False


# --- معالجات الرسائل ---


# معالج أمر start في الخاص (مع تسجيل إضافي)
@bot.on_message(filters.command("start") & filters.private)
async def cmd_debug_start(client, message):
    logger.info(f"!!! Received /start command from {message.from_user.id}"
                )  # <-- تسجيل عند استقبال الأمر
    try:
        await message.reply("🟢 Alive!")
        logger.info(f"!!! Replied to /start from {message.from_user.id}"
                    )  # <-- تسجيل بعد الرد بنجاح
    except Exception as e:
        logger.error(f"!!! Error replying to /start: {e}",
                     exc_info=True)  # <-- تسجيل أي خطأ يحدث عند الرد


# المعالج الرئيسي للمجموعات (لا يزال في الوضع التشخيصي)
@bot.on_message(filters.group & ~filters.service & ~filters.via_bot
                & (filters.text | filters.caption))
async def moderate(client, message):
    # هذا هو الوضع التشخيصي الحالي الذي أرسلته أنت
    # سيبقى هكذا حتى نتأكد من أن البوت يستقبل الرسائل أصلاً
    try:
        # فقط أرسل ردًا بسيطًا وتوقف
        await message.reply_text(f"تم استقبال رسالة بنجاح!")
        # سجل في الكونسول للتأكيد
        logger.info(
            f"!!! Diagnostic: Received message {message.id} from {message.from_user.id} in chat {message.chat.id}"
        )
        await log_action(message.chat.id,
                         f"!!! Diagnostic: Received message {message.id}"
                         )  # اختياري: للسجل
    except Exception as e:
        logger.error(f"!!! Diagnostic Error in moderate: {e}", exc_info=True)

    # الفلاتر الأصلية لا تزال معلقة للتجربة الحالية:
    # if await filter_and_warn(message):
    #     return
    # if await block_links(message):
    #     return
    # if await filter_bad_emojis(message):
    #     return


# معالج الترحيب
@bot.on_message(filters.new_chat_members & filters.group)
async def welcome(client, message):
    # ... (الكود كما هو - لا تغيير)
    for member in message.new_chat_members:
        try:
            await message.reply_text(f"👋 مرحباً بك {member.mention()}!")
            await log_action(
                message.chat.id,
                f"Welcomed new member: {member.mention()} ({member.id})")
        except Exception as e:
            logger.error(
                f"Failed to send welcome message in {message.chat.id}: {e}")


# --- أوامر المشرفين ---
@bot.on_message(filters.command("حظر") & filters.reply & filters.group)
async def cmd_ban(client, message):
    # ... (الكود كما هو - لا تغيير)
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("ليس لديك صلاحية استخدام هذا الأمر.")
        return
    target_user = message.reply_to_message.from_user
    if not target_user: return
    if target_user.id == message.from_user.id:
        return await message.reply_text("لا يمكنك حظر نفسك.")
    if await is_admin(message.chat.id, target_user.id):
        return await message.reply_text(
            f"لا يمكنك حظر المشرف {target_user.mention()}.")
    try:
        await client.ban_chat_member(message.chat.id, target_user.id)
        await message.reply(f"🚫 تم حظر {target_user.mention()}.")
        await log_action(
            message.chat.id,
            f"User {target_user.mention()} ({target_user.id}) banned by {message.from_user.mention()} ({message.from_user.id})"
        )
    except ChatAdminRequired:
        await message.reply_text("أحتاج صلاحيات المشرف لتنفيذ هذا الأمر.")
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await message.reply_text(f"حدث خطأ: {e}")


@bot.on_message(filters.command("طرد") & filters.reply & filters.group)
async def cmd_kick(client, message):
    # ... (الكود كما هو - لا تغيير)
    if not await is_admin(message.chat.id, message.from_user.id):
        await message.reply_text("ليس لديك صلاحية استخدام هذا الأمر.")
        return
    target_user = message.reply_to_message.from_user
    if not target_user: return
    if target_user.id == message.from_user.id:
        return await message.reply_text("لا يمكنك طرد نفسك.")
    if await is_admin(message.chat.id, target_user.id):
        return await message.reply_text(
            f"لا يمكنك طرد المشرف {target_user.mention()}.")
    try:
        await client.ban_chat_member(message.chat.id, target_user.id)
        await client.unban_chat_member(message.chat.id, target_user.id)
        await message.reply(
            f"👢 تم طرد {target_user.mention()}. يمكنه الانضمام مرة أخرى.")
        await log_action(
            message.chat.id,
            f"User {target_user.mention()} ({target_user.id}) kicked by {message.from_user.mention()} ({message.from_user.id})"
        )
    except ChatAdminRequired:
        await message.reply_text("أحتاج صلاحيات المشرف لتنفيذ هذا الأمر.")
    except Exception as e:
        logger.error(f"Error in kick command: {e}")
        await message.reply_text(f"حدث خطأ: {e}")


# --- التشغيل ---
async def main():
    global bot
    try:
        logger.info("Starting Flask thread...")
        flask_thread = Thread(target=run_web, daemon=True)
        flask_thread.start()

        logger.info("Starting Pyrogram bot...")
        await bot.start()
        # الحصول على معلومات البوت بعد البدء مباشرة
        bot_info = await bot.get_me()
        logger.info(
            f"Bot @{bot_info.username} (ID: {bot_info.id}) started successfully!"
        )
        await log_action(0, f"Bot @{bot_info.username} started!"
                         )  # chat_id=0 يعني للسجل العام

        logger.info("Bot is now idle, waiting for updates...")
        await idle()  # إبقاء البوت يعمل وينتظر التحديثات

    # معالجة الأخطاء الفادحة أثناء بدء التشغيل أو التشغيل العام
    except Exception as e:
        logger.critical(f"Critical error during startup or runtime: {e}",
                        exc_info=True)
    # التنظيف عند إيقاف التشغيل
    finally:
        logger.info("Shutting down...")
        # التأكد من أن bot_info معرف وأن البوت متصل قبل محاولة الإيقاف والتسجيل
        bot_info_exists = 'bot_info' in locals() or 'bot_info' in globals()
        if bot.is_connected:
            if bot_info_exists:
                await log_action(0, f"Bot @{bot_info.username} stopping...")
            else:
                await log_action(0,
                                 f"Bot stopping (could not get bot_info)...")
            await bot.stop()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        # تشغيل الحلقة الرئيسية غير المتزامنة
        asyncio.run(main())
    except KeyboardInterrupt:
        # معالجة الإيقاف اليدوي (Ctrl+C)
        logger.info("Shutdown requested via KeyboardInterrupt.")
    except Exception as e:
        # تسجيل أي خطأ فادح يمنع تشغيل asyncio.run
        logger.critical(f"Application failed to run: {e}", exc_info=True)
