import telebot
from telebot import types
import json
import os
import importlib.util
from flask import Flask, render_template, send_from_directory
import threading
import time

# --- المتغيرات العالمية ---
current_config = None
bot = None

def load_settings():
    """تحميل الإعدادات من ملف .config.py أو من المتغيرات البيئية"""
    global current_config, bot
    config_loaded = False

    # المحاولة الأولى: تحميل من ملف .config.py
    try:
        if os.path.exists('.config.py'):
            spec = importlib.util.spec_from_file_location("config", ".config.py")
            new_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(new_config)
            print("✅ تم تحميل الإعدادات من ملف .config.py")
            config_loaded = True
        else:
            print("⚠️ ملف .config.py غير موجود، سيتم استخدام المتغيرات البيئية")
    except Exception as e:
        print(f"❌ خطأ في تحميل .config.py: {e}")

    # إذا فشل التحميل من الملف، استخدم المتغيرات البيئية
    if not config_loaded:
        # إنشاء كائن إعدادات ديناميكي
        class EnvConfig:
            pass
        new_config = EnvConfig
        # قراءة المتغيرات من البيئة
        new_config.API_TOKEN = os.environ.get('BOT_TOKEN', '')
        new_config.PHOTOS_DIR = os.environ.get('PHOTOS_DIR', 'photos')
        new_config.JSON_FILE = os.environ.get('JSON_FILE', 'products.json')
        new_config.BASE_URL = os.environ.get('BASE_URL', 'https://your-app.onrender.com')
        print("✅ تم تحميل الإعدادات من المتغيرات البيئية")

    # التحقق من وجود التوكن
    if not hasattr(new_config, 'API_TOKEN') or not new_config.API_TOKEN:
        print("❌ خطأ: لم يتم العثور على توكن البوت! تأكد من وجود BOT_TOKEN في البيئة أو في .config.py")
        return False

    # التأكد من وجود المجلدات المطلوبة
    if not hasattr(new_config, 'PHOTOS_DIR'):
        new_config.PHOTOS_DIR = 'photos'
    if not hasattr(new_config, 'JSON_FILE'):
        new_config.JSON_FILE = 'products.json'
    if not hasattr(new_config, 'BASE_URL'):
        new_config.BASE_URL = 'https://your-app.onrender.com'

    if not os.path.exists(new_config.PHOTOS_DIR):
        os.makedirs(new_config.PHOTOS_DIR)

    # تحديث كائن البوت إذا تغير التوكن
    if current_config is None or getattr(current_config, 'API_TOKEN', None) != new_config.API_TOKEN:
        bot = telebot.TeleBot(new_config.API_TOKEN)
        print(f"✅ تم تحديث توكن البوت: {new_config.API_TOKEN[:10]}...")
        # إعادة تسجيل معالجات البوت
        register_bot_handlers(bot)

    current_config = new_config
    return True

def register_bot_handlers(bot_instance):
    """تسجيل جميع معالجات أوامر البوت"""
    if bot_instance is None:
        return

    @bot_instance.message_handler(commands=['start'])
    def send_welcome(message):
        bot_instance.reply_to(message, "مرحباً بك في نظام المتجر المحدث تلقائياً!")

    # يمكنك إضافة باقي المعالجات هنا
    # مثال: معالج لاستقبال البيانات من لوحة التحكم
    @bot_instance.message_handler(func=lambda message: True)
    def echo_all(message):
        # هنا يمكن معالجة الرسائل العادية
        pass

    print("✅ تم تسجيل معالجات البوت")

# تحميل الإعدادات الأولية
load_settings()

def config_refresher():
    """خلفية لتحديث الإعدادات كل 60 ثانية"""
    while True:
        time.sleep(60)
        load_settings()
        print("🔄 تم فحص وتحديث المتغيرات تلقائياً...")

threading.Thread(target=config_refresher, daemon=True).start()

# --- إعدادات Flask ---
app = Flask(__name__, template_folder='.')
waiting_for_images = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin-page')
def admin_page():
    return render_template('admin.html', config=current_config)

@app.route('/products.json')
def serve_json():
    return send_from_directory('.', 'products.json')

@app.route('/photos/<path:filename>')
def serve_photos(filename):
    if current_config:
        return send_from_directory(current_config.PHOTOS_DIR, filename)
    return "Photos directory not configured", 404

# --- دوال مساعدة ---
def update_json(products):
    if current_config:
        with open(current_config.JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=4, ensure_ascii=False)

# --- تشغيل البوت في خلفية ---
def run_bot():
    while True:
        try:
            if bot:
                print("🤖 البوت يعمل الآن...")
                bot.remove_webhook()
                bot.polling(none_stop=True, interval=3)
        except Exception as e:
            print(f"⚠️ خطأ في البوت، سيعيد المحاولة: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # تشغيل البوت في خيط منفصل
    threading.Thread(target=run_bot, daemon=True).start()
    
    # تشغيل السيرفر
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)