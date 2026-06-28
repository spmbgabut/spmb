import os
import time
import sqlite3
import logging
import asyncio
import aiohttp
import schedule
import threading
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from flask import Flask
import pytz
import urllib3

# Hilangkan warning SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================================
# 💎 ULTRA VIP KONFIGURASI SISTEM 💎
# =====================================================================
TOKEN = "TOKEN_BOT_TELEGRAM_KAMU" # Isi token kamu
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"

DAFTAR_SEKOLAH = {
    "20329531": {"nama": "SMPN 1 Pekalongan", "kuota": 200},
    "20329533": {"nama": "SMPN 2 Pekalongan", "kuota": 256},
    "20329534": {"nama": "SMPN 3 Pekalongan", "kuota": 200},
    "20329535": {"nama": "SMPN 4 Pekalongan", "kuota": 220},
    "20331635": {"nama": "SMPN 5 Pekalongan", "kuota": 200},
    "20329536": {"nama": "SMPN 6 Pekalongan", "kuota": 200},
    "20329547": {"nama": "SMPN 7 Pekalongan", "kuota": 67},
    "20331636": {"nama": "SMPN 8 Pekalongan", "kuota": 200},
    "20331637": {"nama": "SMPN 9 Pekalongan", "kuota": 200},
    "20331628": {"nama": "SMPN 10 Pekalongan", "kuota": 200},
    "20331629": {"nama": "SMPN 11 Pekalongan", "kuota": 200},
    "20331630": {"nama": "SMPN 12 Pekalongan", "kuota": 200},
    "20331631": {"nama": "SMPN 13 Pekalongan", "kuota": 200},
    "20331632": {"nama": "SMPN 14 Pekalongan", "kuota": 200},
    "20329532": {"nama": "SMPN 15 Pekalongan", "kuota": 200}
}

DB_NAME = "database_spmb.db"

# =====================================================================
# 🛠️ DATABASE & FLASK (SERVER KEEP-ALIVE)
# =====================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 VIP Async SPMB Monitor is Running!"

def get_db_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS riwayat_peringkat 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, waktu TEXT, nisn TEXT, 
                    sekolah TEXT, peringkat INTEGER, status_jurnal TEXT)''')
    conn.commit()
    conn.close()

def simpan_ke_db(nisn, sekolah, peringkat, status):
    tz = pytz.timezone('Asia/Jakarta')
    waktu_skrg = datetime.now(tz).strftime("%d %b %Y | %H:%M:%S")
    conn = get_db_connection()
    conn.execute("INSERT INTO riwayat_peringkat (waktu, nisn, sekolah, peringkat, status_jurnal) VALUES (?, ?, ?, ?, ?)",
                 (waktu_skrg, nisn, sekolah, peringkat, status))
    conn.commit()
    conn.close()

def ambil_data_terakhir():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT sekolah, peringkat FROM riwayat_peringkat WHERE nisn=? ORDER BY id DESC LIMIT 1", (NISN_ANAK,))
    hasil = c.fetchone()
    conn.close()
    return hasil if hasil else ("", 999)

# =====================================================================
# 🕰️ UTILS: WAKTU & KALKULASI SINKRONISASI
# =====================================================================
def analisa_zona(peringkat, kuota):
    if peringkat == 999:
        return "⚫ <b>ZONA HITAM</b>", "Data tidak ditemukan di sistem!"
    persentase = (peringkat / kuota) * 100
    if persentase <= 60:
        return "🟢 <b>ZONA AMAN</b>", "Bisa tidur nyenyak! Posisi solid. ☕"
    elif persentase <= 85:
        return "🟡 <b>ZONA WASPADA</b>", "Mulai terkejar, pantau terus pergerakan! 👀"
    else:
        return "🔴 <b>ZONA KRITIS</b>", "Sangat rawan tergeser! Siapkan rencana B. 🚨"

def kalkulasi_waktu_sinkron():
    tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz)
    
    # Cari interval 15 menit ke bawah untuk Web Terakhir
    menit_terakhir = (now.minute // 15) * 15
    waktu_terakhir = now.replace(minute=menit_terakhir, second=0, microsecond=0)
    
    # Tambah 15 menit untuk jadwal Berikutnya
    waktu_berikutnya = waktu_terakhir + timedelta(minutes=15)
    
    terakhir_str = waktu_terakhir.strftime("%H:%M:00")
    berikutnya_str = waktu_berikutnya.strftime("%H:%M:00")
    sync_bot_str = waktu_berikutnya.replace(second=10).strftime("%H:%M:10")
    
    return terakhir_str, berikutnya_str, sync_bot_str

# =====================================================================
# 🚀 CORE ENGINE: BULLETPROOF ASYNC SCRAPER
# =====================================================================
async def fetch_halaman(session, npsn, nama_sekolah, kuota, halaman):
    url_target = f"https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn={npsn}&page={halaman}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'}
    
    try:
        async with session.get(url_target, headers=headers, timeout=20) as response:
            if response.status == 200:
                html = await response.text()
                if NISN_ANAK not in html:
                    return None
                
                soup = BeautifulSoup(html, 'html.parser')
                baris_tabel = soup.find_all('tr')
                
                for baris in baris_tabel:
                    kolom = baris.find_all('td')
                    if len(kolom) >= 5 and NISN_ANAK in kolom[1].text:
                        try:
                            nomor_urut = int(kolom[0].text.strip())
                        except ValueError:
                            nomor_urut = 999
                            
                        return {
                            "ditemukan": True, 
                            "nama_siswa": kolom[2].text.strip(),
                            "sekolah": nama_sekolah, 
                            "kuota": kuota,
                            "peringkat": nomor_urut, 
                            "status": kolom[4].text.strip(),
                            "url": url_target
                        }
    except Exception as e:
        pass
    return None

async def cari_semua_sekolah_async():
    hasil_akhir = None
    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [asyncio.create_task(fetch_halaman(session, npsn, data["nama"], data["kuota"], hal)) 
                 for npsn, data in DAFTAR_SEKOLAH.items() for hal in range(1, 6)]
        
        for future in asyncio.as_completed(tasks):
            try:
                hasil = await future
                if hasil and hasil.get("ditemukan"):
                    hasil_akhir = hasil
                    for t in tasks: t.cancel()
                    break
            except asyncio.CancelledError:
                pass
    return hasil_akhir

# =====================================================================
# 📱 UI TELEGRAM TERBARU (VIP DASHBOARD)
# =====================================================================
def kirim_telegram(pesan):
    for chat_id in DAFTAR_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "HTML", "disable_web_page_preview": True}
        try:
            requests.post(url_tele, json=payload, verify=False, timeout=10)
        except Exception as e:
            logging.error(f"Gagal kirim Telegram: {e}")

def buat_pesan_dashboard(tipe, data, sek_sblm, per_sblm):
    terakhir, berikutnya, sync_bot = kalkulasi_waktu_sinkron()
    peringkat = data["peringkat"]
    
    label_zona, pesan_psiko = analisa_zona(peringkat, data["kuota"])
    
    if tipe == "pindah":
        ikon_judul = "🚨 <b>STATUS: PINDAH SEKOLAH!</b>"
        detail = f"🔄 Terlempar dari <i>{sek_sblm}</i>\n➡️ Masuk di <b>{data['sekolah']}</b>"
    elif tipe == "aman":
        ikon_judul = "🛡️ <b>STATUS: POSISI BERTAHAN</b>"
        detail = "📌 Tidak ada pergeseran peringkat."
    elif tipe == "turun":
        ikon_judul = "📉 <b>STATUS: POSISI TURUN</b>"
        detail = f"🔻 Turun <b>{peringkat - per_sblm} posisi</b> dari {per_sblm}."
    elif tipe == "naik":
        ikon_judul = "🚀 <b>STATUS: POSISI NAIK!</b>"
        detail = f"🟩 Naik <b>{per_sblm - peringkat} posisi</b> dari {per_sblm}."
    else:
        ikon_judul = "✨ <b>STATUS: DATA DITEMUKAN</b>"
        detail = "🎯 Baru masuk ke dalam sistem pantauan."

    return f"""┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
{ikon_judul}
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛
👤 <b>Nama:</b> {data['nama_siswa']}
💳 <b>NISN:</b> <code>{NISN_ANAK}</code>

🏫 <b>Sekolah:</b> <b>{data['sekolah']}</b>
📊 <b>Peringkat:</b> <b>{peringkat}</b> dari {data['kuota']} Kuota
🏷️ <b>Status Jurnal:</b> <i>{data['status']}</i>

{label_zona}
💬 <i>"{pesan_psiko}"</i>

📈 <b>Detail Pergerakan:</b>
{detail}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>JADWAL SINKRONISASI SERVER:</b>
▪️ Update Web Terakhir: <b>{terakhir} WIB</b>
▪️ Update Web Berikutnya: <b>{berikutnya} WIB</b>
🤖 <i>Bot Auto-Scrape: <b>{sync_bot} WIB</b></i>

🔗 <a href='{data["url"]}'>Buka Web Jurnal Resmi Dindik</a>"""

# =====================================================================
# 🧠 EKSEKUSI & SCHEDULER (10 DETIK DELAY)
# =====================================================================
def jalankan_cek_web_sinkron():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(proses_cek_web())
    finally:
        loop.close()

async def proses_cek_web():
    sek_sblm, per_sblm = ambil_data_terakhir()
    hasil = await cari_semua_sekolah_async()
    
    if hasil:
        tipe = "pindah" if (sek_sblm != "" and hasil["sekolah"] != sek_sblm) else \
               ("aman" if hasil["peringkat"] == per_sblm else \
               ("turun" if hasil["peringkat"] > per_sblm else \
               ("baru" if per_sblm == 999 else "naik")))
                
        pesan = buat_pesan_dashboard(tipe, hasil, sek_sblm, per_sblm)
        if tipe != "aman":
            simpan_ke_db(NISN_ANAK, hasil["sekolah"], hasil["peringkat"], hasil["status"])
        kirim_telegram(pesan)
    else:
        tz = pytz.timezone('Asia/Jakarta')
        waktu = datetime.now(tz).strftime("%H:%M:%S WIB")
        kirim_telegram(f"❌ <b>DATA HILANG / WEB GANGGUAN</b> ❌\nNISN {NISN_ANAK} tidak ditemukan.\n⏱️ Update: {waktu}")

def jalankan_jadwal_otomatis():
    # Menjadwalkan bot sinkronisasi tepat di detik ke-10 setiap interval 15 menit
    schedule.every().hour.at("00:10").do(jalankan_cek_web_sinkron)
    schedule.every().hour.at("15:10").do(jalankan_cek_web_sinkron)
    schedule.every().hour.at("30:10").do(jalankan_cek_web_sinkron)
    schedule.every().hour.at("45:10").do(jalankan_cek_web_sinkron)

    while True:
        schedule.run_pending()
        time.sleep(1)

def dengar_telegram_terus_menerus():
    offset = None
    while True:
        try:
            url_get = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            res = requests.get(url_get, params={"timeout": 30, "offset": offset}, verify=False, timeout=40).json()
            if res.get("ok"):
                for r in res.get("result", []):
                    offset = r["update_id"] + 1
                    if "message" in r and "text" in r["message"] and str(r["message"]["chat"]["id"]) in DAFTAR_CHAT_ID:
                        if "/cek" in r["message"]["text"].lower():
                            kirim_telegram("⚡ <i>Menyapu bersih data dari server Dindik...</i>")
                            jalankan_cek_web_sinkron()
        except:
            time.sleep(5)

if __name__ == "__main__":
    init_db()
    # Mengaktifkan Scheduler dan Polling secara bersamaan
    threading.Thread(target=jalankan_jadwal_otomatis, daemon=True).start()
    threading.Thread(target=dengar_telegram_terus_menerus, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))