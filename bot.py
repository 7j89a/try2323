from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from flask import Flask
from moviepy.video.io.VideoFileClip import VideoFileClip
import subprocess
import os
import time
import asyncio
import threading
import re

# بيانات الاتصال بالبوت
api_id = 20944746  # استبدل بـ API ID الخاص بك
api_hash = "d169162c1bcf092a6773e685c62c3894"  # استبدل بـ API Hash الخاص بك
bot_token = "7701589300:AAG-64FpYOaXkH1OnTXgD08Fk84j4A3dwp4"  # استبدل بـ توكن البوت الخاص بك

# تشغيل البوت
app_bot = Client("downloader_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# تشغيل Flask
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "🚀 البوت يعمل بنجاح مع Flask و Pyrogram!"

# مسار الصورة المصغّرة
thumbnail_path = r"data/photo.jpg"

# متغيرات عالمية
user_headers = {}
user_states = {}
user_video_names = {}

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
    if percent >= 100:
        return completed_symbol * total_bars
    return completed_symbol * completed + symbol * remaining

# استقبال أمر /start
@app_bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "مرحبًا بك! أرسل لي رابط الفيديو الذي تريد تنزيله.\n\n"
        "يمكنك أيضًا تخصيص الهيدرز (مثل User-Agent وReferer) باستخدام الأزرار أدناه.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("تحديد User-Agent", callback_data="user_agent"),
             InlineKeyboardButton("تحديد Referer", callback_data="referer"),
             InlineKeyboardButton("تحديد اسم الفيديو", callback_data="set_video_name")],
            [InlineKeyboardButton("إفراغ User-Agent", callback_data="clear_user_agent"),
             InlineKeyboardButton("إفراغ Referer", callback_data="clear_referer")]
        ])
    )

# استقبال النصوص بناءً على الحالة
@app_bot.on_message(filters.text)
async def handle_text(client, message):
    user_id = message.from_user.id
    state = user_states.get(user_id, "idle")
    text = message.text.strip()

    if state == "idle" and text.startswith(("http://", "https://")):
        output_file = f"{user_id}_video.mp4"
        progress_message = await message.reply_text("🚀 جاري التنزيل...")
        command = ['yt-dlp', '-N', '20', '-o', output_file, text]

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
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

            await message.reply_text("✅ تم التنزيل بنجاح، جاري التحميل إلى Telegram...")
            await upload_with_progress(client, progress_message, output_file, "📤 فيديو تم تنزيله")
        except Exception as e:
            await message.reply_text(f"❌ خطأ أثناء التنزيل: {e}")

# دالة لرفع الفيديو مع شريط تقدم
async def upload_with_progress(client, progress_message, file_path, caption):
    total_size = os.path.getsize(file_path)
    start_time = time.time()

    async def progress_callback(current, total):
        percent = (current / total_size) * 100
        elapsed_time = time.time() - start_time
        speed = (current / (1024 * 1024)) / elapsed_time if elapsed_time > 0 else 0
        progress_bar = generate_progress_bar(percent)

        message_text = (
            f"📤 **Uploading...**\n\n"
            f"{progress_bar}\n\n"
            f"✅ **Completed:** {current / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB\n"
            f"⚡ **Speed:** {speed:.2f} MB/s"
        )
        await safe_edit_message(progress_message, message_text)

    await client.send_video(
        chat_id=progress_message.chat.id,
        video=file_path,
        caption=caption,
        progress=progress_callback
    )
    await safe_edit_message(progress_message, "✅ **تم اكتمال التحميل بنجاح!**")
    os.remove(file_path)

# تشغيل Flask في Thread منفصل
def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# بدء تشغيل البوت وخادم Flask
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("🚀 بدء تشغيل البوت وخادم Flask...")
    app_bot.run()
