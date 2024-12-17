from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from aiohttp import web
from moviepy.video.io.VideoFileClip import VideoFileClip
import asyncio
import subprocess
import os
import time
import re

# بيانات الاتصال بالبوت
api_id = 20944746  # استبدل بـ API ID الخاص بك
api_hash = "d169162c1bcf092a6773e685c62c3894"  # استبدل بـ API Hash الخاص بك
bot_token = "7701589300:AAG-64FpYOaXkH1OnTXgD08Fk84j4A3dwp4"  # استبدل بـ توكن البوت الخاص بك

# تشغيل البوت
app = Client("dwnloader_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# إعداد aiohttp بديل لـ Flask
async def handle_home(request):
    return web.Response(text="🚀 البوت يعمل بنجاح مع aiohttp و Pyrogram!")

app_aiohttp = web.Application()
app_aiohttp.router.add_get("/", handle_home)

# مجلد لحفظ الصور المصغرة
thumbnail_folder = "thumbnails"
os.makedirs(thumbnail_folder, exist_ok=True)

# متغيرات عامة
user_headers = {}
user_states = {}
user_video_names = {}
last_start_time = {}  # لتتبع آخر وقت لتنفيذ أمر /start لكل مستخدم

# دالة لتحرير الرسائل بأمان مع معالجة FloodWait
async def safe_edit_message(message, text):
    try:
        if message.text != text:
            await message.edit(text)
    except FloodWait as e:
        print(f"FloodWait: الانتظار {e.value} ثانية.")
        await asyncio.sleep(e.value)
        await message.edit(text)

# دالة لإنشاء شريط التقدم
def generate_progress_bar(percent, total_bars=10, symbol="🚀", completed_symbol="✅"):
    completed = int(percent / (100 / total_bars))
    remaining = total_bars - completed
    return completed_symbol * completed + symbol * remaining

# دالة لحساب مدة الفيديو باستخدام moviepy
def get_video_duration(file_path):
    try:
        with VideoFileClip(file_path) as video_clip:
            return int(video_clip.duration)
    except Exception as e:
        print(f"Error calculating video duration: {str(e)}")
        return 0

# استقبال أمر /start
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    user_id = message.from_user.id
    current_time = time.time()

    # التحقق من تكرار أمر /start
    if user_id in last_start_time:
        elapsed_time = current_time - last_start_time[user_id]
        if elapsed_time < 60:  # السماح بأمر /start مرة كل 60 ثانية
            await message.reply_text("**⚠️ لقد أرسلت أمر /start مؤخرًا. الرجاء الانتظار قليلًا.**")
            return

    # تحديث وقت آخر أمر /start
    last_start_time[user_id] = current_time

    # الرد على المستخدم
    user_states[user_id] = "idle"
    await message.reply_text(
        "✨ **  مرحبًا بك! لقد تم التصميم بواسطة @YA_AE **\n\n"
        "**أرسل رابط الفيديو الذي تريد تنزيله، أو استخدم الأزرار أدناه لتخصيص إعداداتك:**",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📱 User-Agent", callback_data="user_agent"),
                InlineKeyboardButton("🔗 Referer", callback_data="referer")
            ],
            [
                InlineKeyboardButton("🎥 اسم الفيديو", callback_data="set_video_name"),
                InlineKeyboardButton("♻️ مسح الإعدادات", callback_data="clear_settings")
            ]
        ])
    )

# استقبال الصور المصغرة
@app.on_message(filters.photo & filters.private)
async def handle_thumbnail(client, message):
    user_id = message.from_user.id
    thumbnail_path = os.path.join(thumbnail_folder, f"{user_id}_thumbnail.jpg")  # مسار الصورة المصغرة
    
    # تنزيل الصورة
    await message.download(file_name=thumbnail_path)
    await message.reply_text("**✅ تم حفظ الصورة المصغرة! سيتم استخدامها مع الفيديوهات القادمة.**")

# استقبال أوامر الأزرار
@app.on_callback_query(filters.regex("user_agent"))
async def set_user_agent(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "setting_user_agent"
    await callback_query.message.reply_text("**🚀 أرسل الـ User-Agent الذي ترغب في استخدامه:**")
    await callback_query.answer()

@app.on_callback_query(filters.regex("referer"))
async def set_referer(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "setting_referer"
    await callback_query.message.reply_text("**🔗 أرسل الـ Referer الذي ترغب في استخدامه:**")
    await callback_query.answer()

@app.on_callback_query(filters.regex("set_video_name"))
async def set_video_name(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "setting_video_name"
    await callback_query.message.reply_text("**🎥 أرسل اسم الفيديو:**")
    await callback_query.answer()

@app.on_callback_query(filters.regex("clear_settings"))
async def clear_settings(client, callback_query):
    user_id = callback_query.from_user.id
    user_headers.pop(user_id, None)
    user_video_names.pop(user_id, None)
    thumbnail_path = os.path.join(thumbnail_folder, f"{user_id}_thumbnail.jpg")
    if os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)  # حذف الصورة المصغرة إذا كانت موجودة
    await callback_query.message.reply_text("**✅ تم مسح جميع الإعدادات!**")
    await callback_query.answer()

# استقبال النصوص بناءً على حالة المستخدم
@app.on_message(filters.text & filters.private)
async def handle_text(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id, "idle")
    text = message.text.strip()

    if state == "setting_user_agent":
        user_headers[user_id] = user_headers.get(user_id, {})
        user_headers[user_id]["User-Agent"] = text
        await message.reply_text(f"✅ تم تحديد User-Agent:\n{text}")
        user_states[user_id] = "idle"

    elif state == "setting_referer":
        user_headers[user_id] = user_headers.get(user_id, {})
        user_headers[user_id]["Referer"] = text
        await message.reply_text(f"✅ تم تحديد Referer:\n{text}")
        user_states[user_id] = "idle"

    elif state == "setting_video_name":
        user_video_names[user_id] = text
        await message.reply_text(f"✅ تم تحديد اسم الفيديو:\n{text}")
        user_states[user_id] = "idle"

    elif state == "idle":
        # تقسيم النص إلى أسطر
        urls = text.split("\n")
        valid_urls = [url.strip() for url in urls if url.startswith(("http://", "https://"))]

        if not valid_urls:
            await message.reply_text("❌ لم يتم العثور على روابط صالحة في النص.")
            return

        total_videos = len(valid_urls)
        await message.reply_text(f"🚀 **تم اكتشاف {total_videos} رابطًا. سيتم تنزيلها واحدًا تلو الآخر.**")

        for idx, url in enumerate(valid_urls, start=1):
            await message.reply_text(f"📥 **جاري تنزيل الفيديو {idx} من {total_videos}...**")
            await process_video_download(client, message, url)

        await message.reply_text("✅ **تم اكتمال تنزيل جميع الروابط!**")

# دالة معالجة التنزيل
async def process_video_download(client, message, url):
    user_id = message.from_user.id
    headers = user_headers.get(user_id, {})
    output_file = f"{user_id}_video.mp4"

    command = ['yt-dlp', '--no-check-certificate', '-N', '20', '-o', output_file]
    if 'User-Agent' in headers:
        command.extend(['--add-header', f'User-Agent: {headers["User-Agent"]}'])
    if 'Referer' in headers:
        command.extend(['--add-header', f'Referer: {headers["Referer"]}'])
    command.append(url)

    progress_message = await message.reply_text("🚀 **جاري التنزيل...**")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        last_update_time = time.time()

        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output and time.time() - last_update_time >= 5:
                match = re.search(r'(\d+(\.\d+)?%) of ~\s*([\d.]+[A-Za-z]+) at\s*([\d.]+[A-Za-z]+/s) ETA (\d{2}:\d{2})', output)
                if match:
                    percent = float(match.group(1).strip('%'))
                    total_size = match.group(3)
                    speed = match.group(4)
                    eta = match.group(5)
                    progress_bar = generate_progress_bar(percent)

                    message_text = (
                        f"🚀 **جاري التنزيل...**\n\n"
                        f"{progress_bar}  **{percent:.1f}%**\n\n"
                        f"📦 **الحجم:** {total_size}\n"
                        f"⚡ **السرعة:** {speed}\n"
                        f"⏳ **الوقت المتبقي:** {eta}"
                    )
                    await safe_edit_message(progress_message, message_text)
                    last_update_time = time.time()

        if not os.path.exists(output_file):
            await message.reply_text("❌ لم يتم تنزيل الفيديو.")
            return

        video_duration = get_video_duration(output_file)
        caption = user_video_names.get(user_id, "📹 فيديو جاهز!")
        await upload_with_progress(client, progress_message, output_file, caption, video_duration)

    except Exception as e:
        await message.reply_text(f"❌ خطأ أثناء التنزيل: {e}")

# دالة رفع الفيديو مع الصورة المصغرة
async def upload_with_progress(client, progress_message, file_path, caption, duration):
    user_id = progress_message.chat.id
    thumbnail_path = os.path.join(thumbnail_folder, f"{user_id}_thumbnail.jpg")

    if not os.path.exists(thumbnail_path):
        thumbnail_path = None
    
    total_size = os.path.getsize(file_path)
    start_time = time.time()
    last_update_time = time.time()
    last_percent = 0

    async def progress_callback(current, total):
        nonlocal last_percent, last_update_time
        percent = int((current / total_size) * 100)
        current_time = time.time()

        if percent >= last_percent + 10 or current_time - last_update_time >= 5 or percent == 100:
            elapsed_time = current_time - start_time
            speed = (current / (1024 * 1024)) / elapsed_time if elapsed_time > 0 else 0
            progress_bar = generate_progress_bar(percent)

            message_text = (
                f"📤 **جاري الرفع:**\n\n"
                f"{progress_bar}\n\n"
                f"✅ **تم الرفع:** {current / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB\n"
                f"⚡ **السرعة:** {speed:.2f} MB/s\n"
                f"⏳ **النسبة المئوية:** {percent}%"
            )
            await safe_edit_message(progress_message, message_text)
            last_percent = percent
            last_update_time = current_time

    await client.send_video(
        chat_id=progress_message.chat.id,
        video=file_path,
        width=640,
        height=360,
        duration=duration,
        thumb=thumbnail_path,
        caption=caption,
        supports_streaming=True,
        progress=progress_callback
    )
    await safe_edit_message(progress_message, "✅ **تم اكتمال التحميل وإرسال الفيديو بنجاح!**")

    if os.path.exists(file_path):
        os.remove(file_path)

async def main():
    runner = web.AppRunner(app_aiohttp)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🚀 خادم aiohttp يعمل على http://0.0.0.0:8080")
    
    # تشغيل البوت
    await app.start()
    print("🚀 البوت يعمل بنجاح!")

    try:
        await asyncio.Event().wait()  # إبقاء التطبيق قيد التشغيل
    finally:
        await app.stop()
        await runner.cleanup()

if __name__ == "__main__":
    app.run(main())
