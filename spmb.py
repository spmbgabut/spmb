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
from datetime import datetime
from flask import Flask
import pytz

# =====================================================================
# 💎 ULTRA VIP KONFIGURASI SISTEM 💎
# =====================================================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE" # Wajib ganti/reset nanti di BotFather!
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"

# Kuota Daya Tampung Asli Sekolah (Bisa disesuaikan dengan data riil)
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
WAKTU_MULAI_SERVER = time.time()

# =====================================================================
# 🛠️ SISTEM LOGGING & FLASK SERVER (UNTUK RENDER)
# =====================================================================
logging.basicConfig(
    filename='system.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
app = Flask(__name__)

@app.route('/')
def home():
    uptime = int(time.time() - WAKTU_MULAI_SERVER)
    jam = uptime // 3600
    menit = (uptime % 3600) // 60
    return f"🚀 VIP Async SPMB Monitor is Running! Uptime: {jam}h {menit}m"

# =====================================================================
# 🗄️ MANAJEMEN DATABASE SQLITE (VERSI ANTI-ERROR THREADING)
# =====================================================================
def get_db_connection():
    # check_same_thread=False mencegah crash saat diakses scheduler & polling
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS riwayat_peringkat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu TEXT,
                nisn TEXT,
                sekolah TEXT,
                peringkat INTEGER,
                status_jurnal TEXT
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error Init DB: {e}")

def simpan_ke_db(nisn, sekolah, peringkat, status):
    try:
        waktu_sekarang = dapatkan_waktu_wib()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO riwayat_peringkat (waktu, nisn, sekolah, peringkat, status_jurnal) VALUES (?, ?, ?, ?, ?)",
                  (waktu_sekarang, nisn, sekolah, peringkat, status))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error Simpan DB: {e}")

def ambil_data_terakhir():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT sekolah, peringkat FROM riwayat_peringkat WHERE nisn=? ORDER BY id DESC LIMIT 1", (NISN_ANAK,))
        hasil = c.fetchone()
        conn.close()
        if hasil:
            return hasil[0], hasil[1]
    except Exception as e:
        logging.error(f"Error Ambil Data Terakhir: {e}")
    return "", 999

def ambil_riwayat_5_terakhir():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT waktu, sekolah, peringkat FROM riwayat_peringkat WHERE nisn=? ORDER BY id DESC LIMIT 5", (NISN_ANAK,))
        hasil = c.fetchall()
        conn.close()
        return hasil
    except Exception as e:
        logging.error(f"Error Ambil Riwayat: {e}")
        return []

# =====================================================================
# 🕰️ UTILS: WAKTU, ZONA & ANTI-BLOCK
# =====================================================================
def dapatkan_waktu_wib():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz).strftime("%d %b %Y | %H:%M:%S")

def get_random_header():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
    ]
    return {'User-Agent': random.choice(user_agents)}

def analisa_zona(peringkat, kuota):
    if peringkat == 999:
        return "⚫ <b>TIDAK DITEMUKAN</b>", "Data hilang dari radar!"
        
    persentase = (peringkat / kuota) * 100
    if persentase <= 50:
        return "🟢 <b>AMAN TENTARAM</b>", "Bisa tidur nyenyak! Posisi solid. ☕"
    elif persentase <= 85:
        return "🟡 <b>WASPADA</b>", "Mulai terkejar, terus pantau pergerakan! 👀"
    elif persentase <= 100:
        return "🔴 <b>KRITIS DARURAT</b>", "Sangat rawan tergeser! Siapkan cabut berkas. 🚨"
    else:
        return "⚫ <b>TERLEMPAR</b>", "Sudah melewati batas kuota penerimaan! 😭"

# =====================================================================
# 🚀 CORE ENGINE: SUPER FAST ASYNC SCRAPER
# =====================================================================
async def fetch_halaman(session, npsn, nama_sekolah, kuota, halaman):
    url_target = f"https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn={npsn}&page={halaman}"
    try:
        async with session.get(url_target, headers=get_random_header(), timeout=15) as response:
            if response.status == 200:
                html = await response.text()
                # Percepat pengecekan dengan mencari string sebelum parsing HTML penuh
                if NISN_ANAK not in html:
                    return None
                
                soup = BeautifulSoup(html, 'html.parser')
                baris_tabel = soup.find_all('tr')
                for baris in baris_tabel:
                    if NISN_ANAK in baris.text:
                        kolom = baris.find_all('td')
                        if len(kolom) >= 5:
                            try:
                                nomor_urut = int(kolom[0].text.strip())
                            except:
                                nomor_urut = 999
                            status_jurnal = kolom[4].text.strip()
                            return {
                                "ditemukan": True, 
                                "sekolah": nama_sekolah, 
                                "kuota": kuota,
                                "peringkat": nomor_urut, 
                                "status": status_jurnal,
                                "url": url_target
                            }
    except Exception as e:
        logging.error(f"Error Async di {nama_sekolah} hal {halaman}: {e}")
    return None

async def cari_semua_sekolah_async():
    hasil_akhir = None
    async with aiohttp.ClientSession() as session:
        tasks = []
        # Menembakkan 75 request serentak ke server
        for npsn, data in DAFTAR_SEKOLAH.items():
            for hal in range(1, 6):
                task = asyncio.create_task(fetch_halaman(session, npsn, data["nama"], data["kuota"], hal))
                tasks.append(task)
        
        # Begitu ketemu 1, sisa 74 request lainnya langsung dibatalkan (Super Fast)
        for future in asyncio.as_completed(tasks):
            hasil = await future
            if hasil and hasil.get("ditemukan"):
                hasil_akhir = hasil
                for t in tasks:
                    t.cancel()
                break
                
    return hasil_akhir

# =====================================================================
# 📱 MANAJEMEN PESAN TELEGRAM
# =====================================================================
def kirim_telegram(pesan):
    for chat_id in DAFTAR_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id, 
            "text": pesan, 
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        try:
            requests.post(url_tele, json=payload, timeout=10)
        except Exception as e:
            logging.error(f"Gagal kirim Telegram ke {chat_id}: {e}")

def buat_pesan_dashboard(tipe, sekolah_sekarang, kuota, nomor_urut, status, sekolah_sblm, peringkat_sblm, url):
    waktu = dapatkan_waktu_wib()
    label_zona, pesan_psiko = analisa_zona(nomor_urut, kuota)
    
    garis_atas = "╔══════════════════════════╗"
    garis_bawah = "╚══════════════════════════╝"
    pembatas = "┠──────────────────────────┨"
    
    if tipe == "pindah":
        ikon = "🚨"
        judul = "  STATUS: PINDAH SEKOLAH!   "
        detail = f"🔄 Terlempar dari <i>{sekolah_sblm}</i>\n➡ Masuk di <b>{sekolah_sekarang}</b>"
    elif tipe == "aman":
        ikon = "🛡️"
        judul = "  STATUS: POSISI BERTAHAN   "
        detail = "📌 Tidak ada pergeseran peringkat dari memori terakhir."
    elif tipe == "turun":
        selisih = nomor_urut - peringkat_sblm
        ikon = "📉"
        judul = "   STATUS: POSISI TURUN     "
        detail = f"🔻 Turun <b>{selisih} posisi</b> dari {peringkat_sblm}."
    elif tipe == "naik":
        selisih = peringkat_sblm - nomor_urut
        ikon = "🚀"
        judul = "   STATUS: POSISI NAIK!     "
        detail = f"🟩 Naik <b>{selisih} posisi</b> dari {peringkat_sblm}."
    elif tipe == "baru":
        ikon = "✨"
        judul = " STATUS: DATA DITEMUKAN     "
        detail = "🎯 Baru masuk ke dalam sistem SPMB."

    return f"""{garis_atas}
{ikon} <b>{judul}</b>
{garis_bawah}
👨‍🎓 <b>Siswa NISN:</b> <code>{NISN_ANAK}</code>
{pembatas}
🏢 <b>Diterima di:</b> 
<code>{sekolah_sekarang}</code>

📊 <b>Peringkat:</b> <b>{nomor_urut}</b> / {kuota} Kuota
🚥 <b>Keamanan:</b> {label_zona}
💬 <i>"{pesan_psiko}"</i>
{pembatas}
📋 <b>Detail Pergerakan:</b>
{detail}

🏷 <b>Status Jurnal:</b> <i>{status}</i>
{pembatas}
⏱️ <i>{waktu} WIB</i>
🔗 <a href='{url}'>[ Buka Halaman Web Resmi ]</a>"""

# =====================================================================
# 🧠 LOGIKA UTAMA PEMANTAUAN
# =====================================================================
def jalankan_cek_web_sinkron():
    # Setup loop baru untuk asyncio agar aman di dalam threading
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(proses_cek_web())
    finally:
        loop.close()

async def proses_cek_web():
    sekolah_sblm, peringkat_sblm = ambil_data_terakhir()
    hasil = await cari_semua_sekolah_async()
    
    if hasil:
        sekolah_sekarang = hasil["sekolah"]
        kuota = hasil["kuota"]
        nomor_urut = hasil["peringkat"]
        status_jurnal = hasil["status"]
        url_target = hasil["url"]
        
        if sekolah_sblm != "" and sekolah_sekarang != sekolah_sblm:
            tipe = "pindah"
        else:
            if nomor_urut == peringkat_sblm:
                tipe = "aman"
            elif nomor_urut > peringkat_sblm:
                tipe = "turun"
            else:
                tipe = "baru" if peringkat_sblm == 999 else "naik"
                
        pesan = buat_pesan_dashboard(tipe, sekolah_sekarang, kuota, nomor_urut, status_jurnal, sekolah_sblm, peringkat_sblm, url_target)
        
        # Merekam ke history hanya jika ada perubahan angka/sekolah
        if tipe != "aman":
            simpan_ke_db(NISN_ANAK, sekolah_sekarang, nomor_urut, status_jurnal)
            
        kirim_telegram(pesan)
    else:
        waktu = dapatkan_waktu_wib()
        pesan_hilang = f"""╔══════════════════════════╗
❌ <b>PERINGATAN KRITIS: HILANG</b> ❌
╚══════════════════════════╝
👨‍🎓 <b>Siswa NISN:</b> <code>{NISN_ANAK}</code>

⚠️ <b>STATUS DARURAT KOSONG</b>
Data anak <b>TIDAK TERDETEKSI</b> di 15 pilihan SMP Negeri (Halaman 1-5).
Segera cek manual atau hubungi panitia sekolah!
┠──────────────────────────┨
⏱️ <i>{waktu} WIB</i>"""
        kirim_telegram(pesan_hilang)

# =====================================================================
# 🤖 BOT COMMAND HANDLER & POLLING
# =====================================================================
def proses_perintah(pesan_masuk, chat_id):
    pesan_masuk = pesan_masuk.lower()
    
    if pesan_masuk == "/start":
        kirim_telegram("Halo! Saya adalah Bot VIP Pemantau SPMB. Ketik /help untuk melihat menu.")
        
    elif pesan_masuk == "/help":
        menu = """📚 <b>DAFTAR PERINTAH VIP BOT</b> 📚
<code>/cek</code> - Pindai web 15 sekolah sekarang juga (Super Fast)
<code>/status</code> - Lihat posisi data terakhir yang tersimpan di memori
<code>/riwayat</code> - Lihat 5 sejarah pergerakan peringkat terakhir
<code>/ping</code> - Cek uptime server bot"""
        kirim_telegram(menu)
        
    elif pesan_masuk == "/cek":
        awal = time.time()
        kirim_telegram("⚡ <i>Mengirim 75 request serentak ke server SPMB...</i>")
        jalankan_cek_web_sinkron()
        durasi = round(time.time() - awal, 2)
        kirim_telegram(f"⏱️ <i>Pencarian Super Fast selesai dalam {durasi} detik!</i>")
        
    elif pesan_masuk == "/status":
        sek, per = ambil_data_terakhir()
        if sek:
            kirim_telegram(f"📌 <b>STATUS MEMORI TERAKHIR:</b>\nSekolah: <b>{sek}</b>\nPeringkat: <b>{per}</b>")
        else:
            kirim_telegram("Belum ada data tersimpan. Ketik /cek.")
            
    elif pesan_masuk == "/riwayat":
        riwayat = ambil_riwayat_5_terakhir()
        if riwayat:
            teks_riwayat = "📜 <b>5 RIWAYAT PERGERAKAN TERAKHIR:</b>\n\n"
            for r in riwayat:
                teks_riwayat += f"🗓️ {r[0]}\n🏫 {r[1]} - Peringkat <b>{r[2]}</b>\n\n"
            kirim_telegram(teks_riwayat)
        else:
            kirim_telegram("Belum ada sejarah pergerakan yang tersimpan di Database.")
            
    elif pesan_masuk == "/ping":
        uptime = int(time.time() - WAKTU_MULAI_SERVER)
        m, s = divmod(uptime, 60)
        h, m = divmod(m, 60)
        kirim_telegram(f"🟢 <b>Server Aktif & Sehat!</b>\nUptime: {h} jam, {m} menit, {s} detik.")

def dengar_telegram_terus_menerus():
    offset = None
    while True:
        try:
            url_get = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"timeout": 30, "offset": offset}
            response = requests.get(url_get, params=params, timeout=40).json()
            
            if response.get("ok"):
                for result in response.get("result", []):
                    offset = result["update_id"] + 1
                    
                    if "message" in result and "text" in result["message"]:
                        pesan_teks = result["message"]["text"]
                        chat_id = str(result["message"]["chat"]["id"])
                        
                        if chat_id in DAFTAR_CHAT_ID:
                            threading.Thread(target=proses_perintah, args=(pesan_teks, chat_id)).start()
        except Exception as e:
            time.sleep(5)

# =====================================================================
# 🗓️ SCHEDULER & INISIALISASI UTAMA
# =====================================================================
def jalankan_jadwal_otomatis():
    jadwal_menit = ["00:05", "15:05", "30:05", "45:05"]
    for waktu in jadwal_menit:
        schedule.every().hour.at(waktu).do(jalankan_cek_web_sinkron)

    pesan_start = """💎 <b>VIP ASYNC MONITOR AKTIF</b> 💎
Server Database & Polling berhasil dinyalakan.

⚙️ <b>Sistem Aktif:</b>
✅ 75x Async Concurrent Scraping
✅ Auto-Rotate Anti-Block Agent
✅ Database History Management

Ketik <code>/help</code> untuk daftar perintah."""
    kirim_telegram(pesan_start)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    init_db()
    
    threading.Thread(target=jalankan_jadwal_otomatis, daemon=True).start()
    threading.Thread(target=dengar_telegram_terus_menerus, daemon=True).start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)