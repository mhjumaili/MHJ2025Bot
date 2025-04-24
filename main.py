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
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "0"))
    PORT = int(os.getenv("PORT", "10000"))
except ValueError:
    logging.error("خطأ: تأكد من أن API_ID و LOG_CHANNEL و PORT أرقام صحيحة.")
    exit(1)
except Exception as e:
    logging.error(f"خطأ عند قراءة متغيرات البيئة: {e}")
    exit(1)

if not all([API_ID, API_HASH, BOT_TOKEN]):
    logging.error(
        "خطأ: يرجى تعيين متغيرات البيئة API_ID, API_HASH, BOT_TOKEN.")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize bot client
try:
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
    return "🤖 Bot is running!"


def run_web():
    try:
        logger.info(f"Starting Flask server on 0.0.0.0:{PORT}")
        app.run(host="0.0.0.0", port=PORT)
    except Exception as e:
        logger.error(f"Flask server failed: {e}", exc_info=True)


# --- تخزين التحذيرات (في الذاكرة) ---
warnings_store = {}

# --- قوائم الحظر (تم ملؤها من قبلك) ---
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
    if message.from_user and await is_admin(message.chat.id,
                                            message.from_user.id):
        return False

    text_to_check = (message.text or message.caption or "").lower()
    if not text_to_check or not BAD_WORDS:
        return False

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
            return False  # توقف إذا لم نتمكن من الحذف
        except Exception as e:
            logger.error(f"Error processing bad word '{word}': {e}",
                         exc_info=True)
            continue

    return False


async def block_links(message):
    if message.from_user and await is_admin(message.chat.id,
                                            message.from_user.id):
        return False

    text_to_check = (message.text or message.caption or "").lower()
    if not text_to_check or not BAD_DOMAINS:  # تحقق من وجود نطاقات للحظر
        return False

    link_pattern = r"(https?://|www\.|t\.me/)"  # تحقق من وجود رابط أولاً
    if re.search(link_pattern, text_to_check, re.IGNORECASE):
        for domain in BAD_DOMAINS:
            try:
                if not isinstance(domain, str):
                    logger.warning(
                        f"Skipping non-string item in BAD_DOMAINS: {repr(domain)}"
                    )
                    continue
                # تحقق مما إذا كان النطاق المحظور موجودًا في النص
                # لا حاجة لحدود الكلمات (\b) للنطاقات
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
                    # await warn_user(message) # يمكنك إضافة تحذير هنا أيضًا
                    return True
            except ChatAdminRequired:
                logger.error(
                    f"Failed to delete bad link message in {message.chat.id}: Bot lacks delete permission."
                )
                return False  # توقف إذا لم نتمكن من الحذف
            except Exception as e:
                logger.error(f"Error processing bad domain '{domain}': {e}",
                             exc_info=True)
                continue

    return False


# --- دالة فلترة الإيموجيات (جديدة) ---
async def filter_bad_emojis(message):
    if message.from_user and await is_admin(message.chat.id,
                                            message.from_user.id):
        return False

    text_to_check = message.text or message.caption or ""
    if not text_to_check or not BAD_EMOJIS:  # تحقق من وجود إيموجيات للحظر
        return False

    for emoji in BAD_EMOJIS:
        if emoji in text_to_check:  # البحث المباشر عن الإيموجي كافٍ
            try:
                await message.delete()
                await log_action(
                    message.chat.id,
                    f"Deleted message from {message.from_user.mention()} due to forbidden emoji: '{emoji}'"
                )
                await warn_user(message)  # تحذير المستخدم
                return True  # تم العثور والمعالجة
            except ChatAdminRequired:
                logger.error(
                    f"Failed to delete bad emoji message in {message.chat.id}: Bot lacks delete permission."
                )
                return False  # توقف
            except Exception as e:
                logger.error(f"Error processing bad emoji '{emoji}': {e}",
                             exc_info=True)
                continue  # انتقل إلى الإيموجي التالي

    return False  # لم يتم العثور على إيموجي محظور


# --- معالج الرسائل الرئيسي ---
@bot.on_message(filters.group & ~filters.service & ~filters.via_bot
                & (filters.text | filters.caption))
async def moderate(client, message):
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

    # تأكد من أن الأسطر التالية معلقة (عليها #) أو محذوفة مؤقتًا
    # if await filter_and_warn(message):
    #     return
    # if await block_links(message):
    #     return
    # if await filter_bad_emojis(message):
    #     return


# --- معالج الترحيب ---
@bot.on_message(filters.new_chat_members & filters.group)
async def welcome(client, message):
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
        bot_info = await bot.get_me()
        logger.info(f"Bot @{bot_info.username} started successfully!")
        await log_action(0, f"Bot @{bot_info.username} started!")

        logger.info("Bot is now idle, waiting for updates...")
        await idle()

    except Exception as e:
        logger.critical(f"Critical error during startup or runtime: {e}",
                        exc_info=True)
    finally:
        logger.info("Shutting down...")
        if 'bot_info' in locals(
        ) and bot.is_connected:  # تحقق من وجود bot_info قبل استخدامه
            await log_action(0, f"Bot @{bot_info.username} stopping...")
            await bot.stop()
        elif bot.is_connected:
            await bot.stop()  # أوقف البوت حتى لو لم يتم الحصول على المعلومات
        logger.info("Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt.")
    except Exception as e:
        logger.critical(f"Application failed to run: {e}", exc_info=True)
