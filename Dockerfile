# تحديد صورة Python
FROM python:3.9-slim

# تثبيت الأدوات المطلوبة
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# تعيين مجلد العمل
WORKDIR /app

# نسخ الملفات
COPY . /app

# تثبيت الحزم
RUN pip install --no-cache-dir -r requirements.txt

# فتح المنفذ 8080 لـ Flask
EXPOSE 8080

# تشغيل التطبيق
CMD ["python", "bot.py"]
