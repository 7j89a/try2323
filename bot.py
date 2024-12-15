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
app = Client("downloader_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# تشغيل Flask
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "🚀 البوت يعمل بنجاح مع Flask و Pyrogram!"

# مسار الصورة المصغّرة
thumbnail_path = r"/data/photo.jpg"  # مسار الصورة المصغّرة

# متغيرات عالمية
user_headers = {}
user_states = {}
user_video_names = {}

# دالة لتحرير الرسائل بأمان مع معالجة FloodWait
async def safe_edit_message(message, text):
    try:
        # تحقق مما إذا كان النص الذي سيتم تحديثه مختلفًا عن النص الحالي
        if message.text != text:
            await message.edit(text)
    except FloodWait as e:
        print(f"FloodWait: الانتظار {e.value} ثانية.")
        await asyncio.sleep(e.value)
        await message.edit(text)

# دالة لإنشاء شريط التقدم
def generate_progress_bar(percent, total_bars=20, symbol="⭐", completed_symbol="✅"):
    """إنشاء شريط تقدم دقيق يتأكد من اكتمال الرموز عند 100%"""
    completed = int(percent / (100 / total_bars))
    remaining = total_bars - completed

    # عند الوصول إلى 100% تأكد أن جميع الرموز مكتملة
    if percent >= 100:
        return completed_symbol * total_bars

    return completed_symbol * completed + symbol * remaining

# دالة لحساب مدة الفيديو باستخدام moviepy
def get_video_duration(file_path):
    """حساب مدة الفيديو باستخدام moviepy"""
    try:
        with VideoFileClip(file_path) as video_clip:
            return int(video_clip.duration)
    except Exception as e:
        print(f"Error calculating video duration: {str(e)}")
        return 0

# استقبال أمر /start
@app.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    user_states[user_id] = "idle"
    await message.reply_text(
        "مرحبًا بك! أرسل لي رابط الفيديو الذي تريد تنزيله.\n\n"
        "يمكنك أيضًا تخصيص الهيدرز (مثل User-Agent وReferer) باستخدام الأزرار أدناه.",
        reply_markup=InlineKeyboardMarkup([  # إضافة الأزرار
            [
                InlineKeyboardButton("تحديد User-Agent", callback_data="user_agent"),
                InlineKeyboardButton("تحديد Referer", callback_data="referer"),
                InlineKeyboardButton("تحديد اسم الفيديو", callback_data="set_video_name")
            ],
            [
                InlineKeyboardButton("إفراغ User-Agent", callback_data="clear_user_agent"),
                InlineKeyboardButton("إفراغ Referer", callback_data="clear_referer")
            ]
        ])
    )

# استقبال أوامر الأزرار
@app.on_callback_query(filters.regex("user_agent"))
async def set_user_agent(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "setting_user_agent"
    await callback_query.message.reply_text("🚀 أرسل الـ User-Agent الذي ترغب في استخدامه:")
    await callback_query.answer()

@app.on_callback_query(filters.regex("referer"))
async def set_referer(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "setting_referer"
    await callback_query.message.reply_text("🔗 أرسل الـ Referer الذي ترغب في استخدامه:")
    await callback_query.answer()

@app.on_callback_query(filters.regex("set_video_name"))
async def set_video_name(client, callback_query):
    user_id = callback_query.from_user.id
    user_states[user_id] = "setting_video_name"
    await callback_query.message.reply_text("🎥 أرسل اسم الفيديو:")
    await callback_query.answer()

@app.on_callback_query(filters.regex("clear_user_agent"))
async def clear_user_agent(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_headers and "User-Agent" in user_headers[user_id]:
        del user_headers[user_id]["User-Agent"]
    await callback_query.message.reply_text("✅ تم مسح الـ User-Agent.")
    await callback_query.answer()

@app.on_callback_query(filters.regex("clear_referer"))
async def clear_referer(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_headers and "Referer" in user_headers[user_id]:
        del user_headers[user_id]["Referer"]
    await callback_query.message.reply_text("✅ تم مسح الـ Referer.")
    await callback_query.answer()

# استقبال النصوص بناءً على حالة المستخدم
@app.on_message(filters.text)
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

    elif state == "idle" and (text.startswith("http://") or text.startswith("https://")):
        headers = user_headers.get(user_id, {})
        output_file = f"{user_id}_video.mp4"

        command = ['yt-dlp', '--no-check-certificate', '-N', '20', '-o', output_file]
        if 'User-Agent' in headers:
            command.extend(['--add-header', f'User-Agent: {headers["User-Agent"]}'])
        if 'Referer' in headers:
            command.extend(['--add-header', f'Referer: {headers["Referer"]}'])
        command.append(text)

        progress_message = await message.reply_text("🚀 جاري التنزيل...")
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

            # تحقق مما إذا كان الملف قد تم تنزيله بنجاح
            if not os.path.exists(output_file):
                await message.reply_text("❌ لم يتم تنزيل الفيديو بشكل صحيح، يرجى المحاولة لاحقًا.")
                return

            # انتظر فترة بعد اكتمال التنزيل قبل رفع الفيديو
            time.sleep(5)  # تأخير 5 ثواني

            # حساب مدة الفيديو (اختياري)
            video_duration = get_video_duration(output_file)
            await message.reply_text(f"📦 تم تنزيل الفيديو بنجاح! المدة: {video_duration} ثانية")

            # رفع الفيديو مباشرة
            caption = user_video_names.get(user_id, "فيديو تم تنزيله")
            await upload_with_progress(client, progress_message, output_file, caption, video_duration)

        except Exception as e:
            await message.reply_text(f"❌ خطأ أثناء التنزيل: {str(e)}")

# دالة لرفع الفيديو مع شريط تقدم دقيق
async def upload_with_progress(client, progress_message, file_path, caption, duration):
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
                f"📤 **Uploading...**\n\n"
                f"{progress_bar}\n\n"
                f"✅ **Completed:** {current / (1024*1024):.2f} MB / {total_size / (1024*1024):.2f} MB\n"
                f"⚡ **Speed:** {speed:.2f} MB/s"
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

    # حذف الفيديو بعد رفعه
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"تم حذف الملف: {file_path}")

# تشغيل Flask في Thread منفصل
def run_flask():
    app_flask.run(host="0.0.0.0", port=8080)

# بدء تشغيل البوت وخادم Flask
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("🚀 بدء تشغيل البوت وخادم Flask...")
    app_bot.run()
