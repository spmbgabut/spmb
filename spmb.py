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

# Matikan warning SSL karena server Render sering menolak web .go.id
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================================================
# 💎 ULTRA VIP KONFIGURASI SISTEM 💎
# =====================================================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE" # Wajib ganti/reset nanti di BotFather!
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"

# Kuota Daya Tampung Asli Sekolah
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
# 🗄️ MANAJEMEN DATABASE SQLITE
# =====================================================================
def get_db_connection():
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
# 🕰️ UTILS: WAKTU, ZONA & UI TAMBAHAN
# =====================================================================
def dapatkan_waktu_wib():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz).strftime("%d %b %Y | %H:%M:%S")

def get_random_header():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
    ]
    return {'User-Agent': random.choice(user_agents)}

def analisa_zona(peringkat, kuota):
    if peringkat == 999:
        return "⚫ <b>ZONA HITAM</b>", "Data hilang dari radar!"
        
    persentase = (peringkat / kuota) * 100
    if persentase <= 50:
        return "🟢 <b>AMAN TENTARAM</b>", "Bisa tidur nyenyak! Posisi solid. ☕"
    elif persentase <= 85:
        return "🟡 <b>WASPADA</b>", "Mulai terkejar, terus pantau pergerakan! 👀"
    elif persentase <= 100:
        return "🔴 <b>KRITIS DARURAT</b>", "Sangat rawan tergeser! Siapkan cabut berkas. 🚨"
    else:
        return "⚫ <b>TERLEMPAR</b>", "Sudah melewati batas kuota penerimaan! 😭"

def buat_progress_bar(peringkat, kuota):
    persen = (peringkat / kuota) * 100
    if persen > 100: persen = 100
    blok_isi = int(persen // 10)
    blok_kosong = 10 - blok_isi
    bar = "█" * blok_isi + "░" * blok_kosong
    return f"<code>[{bar}]</code> {persen:.1f}%"

def kalkulasi_waktu_sinkron():
    tz = pytz.timezone('Asia/Jakarta')
    now = datetime.now(tz)
    # Membulatkan ke bawah ke interval 15 menit terdekat
    menit_terakhir = (now.minute // 15) * 15
    waktu_terakhir = now.replace(minute=menit_terakhir, second=0, microsecond=0)
    waktu_berikutnya = waktu_terakhir + timedelta(minutes=15)
    
    terakhir_str = waktu_terakhir.strftime("%H:%M:00")
    berikutnya_str = waktu_berikutnya.strftime("%H:%M:00")
    sync_bot_str = waktu_berikutnya.replace(second=10).strftime("%H:%M:10")
    
    return terakhir_str, berikutnya_str, sync_bot_str

# =====================================================================
# 🚀 CORE ENGINE: SUPER FAST ASYNC SCRAPER
# =====================================================================
async def fetch_halaman(session, npsn, nama_sekolah, kuota, halaman):
    url_target = f"https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn={npsn}&page={halaman}"
    try:
        async with session.get(url_target, headers=get_random_header(), timeout=15) as response:
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
                        except:
                            nomor_urut = 999
                            
                        # Aman: Coba ambil data ekstra jika kolomnya ada
                        nama_siswa = kolom[2].text.strip() if len(kolom) > 2 else "Tidak Terdeteksi"
                        asal_sd = kolom[3].text.strip() if len(kolom) > 3 else "-"
                        status_jurnal = kolom[4].text.strip() if len(kolom) > 4 else "Terjurnal"
                        jarak = kolom[7].text.strip() if len(kolom) > 7 else "-"
                        usia = kolom[8].text.strip() if len(kolom) > 8 else "-"

                        return {
                            "ditemukan": True, 
                            "nama_siswa": nama_siswa,
                            "asal_sd": asal_sd,
                            "jarak": jarak,
                            "usia": usia,
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
    # WAJIB verify_ssl=False untuk server Render
    connector = aiohttp.TCPConnector(verify_ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for npsn, data in DAFTAR_SEKOLAH.items():
            for hal in range(1, 6):
                task = asyncio.create_task(fetch_halaman(session, npsn, data["nama"], data["kuota"], hal))
                tasks.append(task)
        
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
            requests.post(url_tele, json=payload, verify=False, timeout=10)
        except Exception as e:
            logging.error(f"Gagal kirim Telegram ke {chat_id}: {e}")

def buat_pesan_dashboard(tipe, data_scraping, sekolah_sblm, peringkat_sblm):
    terakhir, berikutnya, sync_bot = kalkulasi_waktu_sinkron()
    peringkat = data_scraping["peringkat"]
    kuota = data_scraping["kuota"]
    
    label_zona, pesan_psiko = analisa_zona(peringkat, kuota)
    progress_bar = buat_progress_bar(peringkat, kuota)
    
    if tipe == "pindah":
        ikon_judul = "🚨 <b>STATUS: PINDAH SEKOLAH!</b>"
        tren = f"🔄 Terlempar dari <i>{sekolah_sblm}</i>\n➡️ Masuk di <b>{data_scraping['sekolah']}</b>"
    elif tipe == "aman":
        ikon_judul = "🛡️ <b>STATUS: POSISI BERTAHAN</b>"
        tren = "📌 Tidak ada pergeseran peringkat dari memori terakhir."
    elif tipe == "turun":
        selisih = peringkat - peringkat_sblm
        ikon_judul = "📉 <b>STATUS: POSISI TURUN</b>"
        tren = f"🔻 Turun <b>{selisih} posisi</b> dari {peringkat_sblm}."
    elif tipe == "naik":
        selisih = peringkat_sblm - peringkat
        ikon_judul = "🚀 <b>STATUS: POSISI NAIK!</b>"
        tren = f"🟩 Naik <b>{selisih} posisi</b> dari {peringkat_sblm}."
    else:
        ikon_judul = "✨ <b>STATUS: DATA DITEMUKAN</b>"
        tren = "🎯 Baru masuk ke dalam sistem SPMB."

    return f"""🏆 <b>SPMB VIP MONITOR</b> 🏆
━━━━━━━━━━━━━━━━━━━━━━━━━━
{ikon_judul}

👤 <b>Profil Siswa</b>
├ <b>Nama:</b> {data_scraping.get('nama_siswa', 'Tidak diketahui')}
├ <b>NISN:</b> <code>{NISN_ANAK}</code>
├ <b>Asal:</b> {data_scraping.get('asal_sd', '-')}
├ <b>Usia:</b> {data_scraping.get('usia', '-')}
└ <b>Jarak:</b> {data_scraping.get('jarak', '-')}

🏫 <b>Status Penerimaan</b>
├ <b>Diterima di:</b> {data_scraping['sekolah']}
├ <b>Status:</b> {data_scraping['status']}
└ <b>Peringkat:</b> <b>{peringkat}</b> / {kuota} Kuota

📊 <b>Analisis Kompetisi</b>
├ <b>Keamanan:</b> {label_zona}
├ <b>Tren:</b> {tren}
└ <b>Kuota:</b> {progress_bar}

💬 <i>"{pesan_psiko}"</i>
━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>SINKRONISASI SERVER:</b>
▪️ Update Web Terakhir: <b>{terakhir} WIB</b>
▪️ Update Web Berikutnya: <b>{berikutnya} WIB</b>
🤖 <i>Bot Auto-Scrape: <b>{sync_bot} WIB</b></i>

🔗 <a href='{data_scraping["url"]}'>Buka Halaman Web Resmi</a>"""

# =====================================================================
# 🧠 LOGIKA UTAMA PEMANTAUAN
# =====================================================================
def jalankan_cek_web_sinkron():
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
        nomor_urut = hasil["peringkat"]
        status_jurnal = hasil["status"]
        
        if sekolah_sblm != "" and sekolah_sekarang != sekolah_sblm:
            tipe = "pindah"
        else:
            if nomor_urut == peringkat_sblm:
                tipe = "aman"
            elif nomor_urut > peringkat_sblm:
                tipe = "turun"
            else:
                tipe = "baru" if peringkat_sblm == 999 else "naik"
                
        pesan = buat_pesan_dashboard(tipe, hasil, sekolah_sblm, peringkat_sblm)
        
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
            # verify=False ditambahkan agar Render tidak memblokir request Telegram
            response = requests.get(url_get, params=params, verify=False, timeout=40).json()
            
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
    # Menjadwalkan bot di detik ke-10 (MM:SS) setiap interval 15 menit
    jadwal_menit_detik = ["00:10", "15:10", "30:10", "45:10"]
    for waktu in jadwal_menit_detik:
        schedule.every().hour.at(waktu).do(jalankan_cek_web_sinkron)

    pesan_start = """💎 <b>VIP ASYNC MONITOR AKTIF</b> 💎
Server Database & Polling berhasil dinyalakan.

⚙️ <b>Sistem Aktif:</b>
✅ 75x Async Concurrent Scraping
✅ Auto-Rotate Anti-Block Agent
✅ Database History Management
✅ Delay 10 Detik Sync Mode

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