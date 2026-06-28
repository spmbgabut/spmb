import requests
from bs4 import BeautifulSoup
import time
import threading
import os
import schedule
import concurrent.futures
from flask import Flask
from datetime import datetime
import pytz

# ==========================================
# 💎 KONFIGURASI BOT & DATA SISWA VIP 💎
# ==========================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE" # Reset token di BotFather!
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"

# Tambahkan Kuota (Daya Tampung) tiap sekolah untuk fitur "Zona Aman"
# Angka 200 ini cuma contoh, silakan ganti dengan kuota asli tiap sekolah
DAFTAR_SEKOLAH = {
    "20329531": {"nama": "SMPN 1 Pekalongan", "kuota": 200},
    "20329533": {"nama": "SMPN 2 Pekalongan", "kuota": 256},
    "20329534": {"nama": "SMPN 3 Pekalongan", "kuota": 200},
    "20329535": {"nama": "SMPN 4 Pekalongan", "kuota": 220},
    "20331635": {"nama": "SMPN 5 Pekalongan", "kuota": 200},
    "20329536": {"nama": "SMPN 6 Pekalongan", "kuota": 200},
    "20329547": {"nama": "SMPN 7 Pekalongan", "kuota": 200},
    "20331636": {"nama": "SMPN 8 Pekalongan", "kuota": 200},
    "20331637": {"nama": "SMPN 9 Pekalongan", "kuota": 200},
    "20331628": {"nama": "SMPN 10 Pekalongan", "kuota": 200},
    "20331629": {"nama": "SMPN 11 Pekalongan", "kuota": 200},
    "20331630": {"nama": "SMPN 12 Pekalongan", "kuota": 200},
    "20331631": {"nama": "SMPN 13 Pekalongan", "kuota": 200},
    "20331632": {"nama": "SMPN 14 Pekalongan", "kuota": 200},
    "20329532": {"nama": "SMPN 15 Pekalongan", "kuota": 200}
}

FILE_CACHE = "data_cache_spmb.txt"
# ==========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 VIP SPMB Monitor is Running!"

# --- FUNGSI WAKTU & ZONA ---
def dapatkan_waktu_wib():
    tz = pytz.timezone('Asia/Jakarta')
    return datetime.now(tz).strftime("%d %b %Y | %H:%M:%S WIB")

def analisa_zona(peringkat, kuota):
    persentase = (peringkat / kuota) * 100
    if persentase <= 50:
        return "🟢 <b>AMAN</b>", "Bisa tidur nyenyak! Posisi sangat solid. ☕"
    elif persentase <= 85:
        return "🟡 <b>WASPADA</b>", "Masih di dalam kuota, tapi pantau pergerakan! 👀"
    elif persentase <= 100:
        return "🔴 <b>KRITIS</b>", "Rawan tergeser! Siapkan rencana cadangan. 🚨"
    else:
        return "⚫ <b>TERLEMPAR</b>", "Sudah melewati batas kuota penerimaan! 😭"

# --- FUNGSI CACHE ---
def get_data_sebelumnya():
    if os.path.exists(FILE_CACHE):
        try:
            with open(FILE_CACHE, "r") as f:
                data = f.read().strip().split("|")
                if len(data) == 2:
                    return data[0], int(data[1])
        except Exception:
            pass
    return "", 999 

def set_data_sebelumnya(nama_sekolah, peringkat):
    try:
        with open(FILE_CACHE, "w") as f:
            f.write(f"{nama_sekolah}|{peringkat}")
    except Exception as e:
        print("Gagal menyimpan data:", e)

# --- FUNGSI KIRIM TELEGRAM ---
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
            print(f"Gagal kirim: {e}")

# --- FUNGSI PENCARIAN 1 SEKOLAH ---
def cek_satu_sekolah(npsn, data_sekolah):
    nama_sekolah = data_sekolah["nama"]
    kuota = data_sekolah["kuota"]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for halaman in range(1, 6): 
        try:
            url_target = f"https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn={npsn}&page={halaman}"
            response = requests.get(url_target, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
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
        except Exception:
            continue
    return {"ditemukan": False}

# --- TEMPLATE PESAN DASHBOARD PREMIUM ---
def buat_pesan(tipe, nisn, sekolah_sekarang, kuota, nomor_urut, status, sekolah_sblm, peringkat_sblm, url):
    waktu = dapatkan_waktu_wib()
    label_zona, pesan_psikologis = analisa_zona(nomor_urut, kuota)
    
    # Elemen Desain
    garis_atas = "╔══════════════════════════╗"
    garis_bawah = "╚══════════════════════════╝"
    pembatas = "┠──────────────────────────┨"
    
    # Logika Header & Konten
    if tipe == "pindah":
        ikon = "🚨"
        judul = "  STATUS: PINDAH SEKOLAH!   "
        detail_perubahan = f"🔄 Terlempar dari <i>{sekolah_sblm}</i>\n➡ Sekarang masuk di <b>{sekolah_sekarang}</b>"
    elif tipe == "aman":
        ikon = "🛡️"
        judul = "  STATUS: POSISI BERTAHAN   "
        detail_perubahan = "📌 Tidak ada pergeseran peringkat sejak pengecekan terakhir."
    elif tipe == "turun":
        selisih = nomor_urut - peringkat_sblm
        ikon = "📉"
        judul = "   STATUS: POSISI TURUN     "
        detail_perubahan = f"🔻 Turun <b>{selisih} peringkat</b> dari posisi {peringkat_sblm}."
    elif tipe == "naik":
        selisih = peringkat_sblm - nomor_urut
        ikon = "🚀"
        judul = "   STATUS: POSISI NAIK!     "
        detail_perubahan = f"🟩 Naik <b>{selisih} peringkat</b> dari posisi {peringkat_sblm}."
    elif tipe == "baru":
        ikon = "✨"
        judul = " STATUS: DATA DITEMUKAN     "
        detail_perubahan = "🎯 Data baru saja masuk ke dalam sistem SPMB."

    # Menyusun String HTML
    pesan_final = f"""{garis_atas}
{ikon} <b>{judul}</b>
{garis_bawah}
👨‍🎓 <b>Siswa NISN:</b> <code>{nisn}</code>
{pembatas}
🏢 <b>Diterima di:</b> 
<code>{sekolah_sekarang}</code>

📊 <b>Peringkat:</b> <b>{nomor_urut}</b> / {kuota} Kuota
🚥 <b>Zona Keamanan:</b> {label_zona}
💬 <i>"{pesan_psikologis}"</i>

{pembatas}
📋 <b>Detail Pergerakan:</b>
{detail_perubahan}

🏷 <b>Status Jurnal:</b> <i>{status}</i>
{pembatas}
⏱️ <i>Update: {waktu}</i>
🔗 <a href='{url}'>[Buka Halaman Web Resmi]</a>"""

    return pesan_final

# --- FUNGSI UTAMA SCRAPING ---
def cek_web():
    sekolah_sblm, peringkat_sblm = get_data_sebelumnya()
    hasil_akhir = None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(cek_satu_sekolah, npsn, data): data["nama"] for npsn, data in DAFTAR_SEKOLAH.items()}
        
        for future in concurrent.futures.as_completed(futures):
            hasil = future.result()
            if hasil["ditemukan"]:
                hasil_akhir = hasil
                break
                
    if hasil_akhir:
        sekolah_sekarang = hasil_akhir["sekolah"]
        kuota = hasil_akhir["kuota"]
        nomor_urut = hasil_akhir["peringkat"]
        status_jurnal = hasil_akhir["status"]
        url_target = hasil_akhir["url"]
        
        if sekolah_sblm != "" and sekolah_sekarang != sekolah_sblm:
            pesan = buat_pesan("pindah", NISN_ANAK, sekolah_sekarang, kuota, nomor_urut, status_jurnal, sekolah_sblm, peringkat_sblm, url_target)
        else:
            if nomor_urut == peringkat_sblm:
                pesan = buat_pesan("aman", NISN_ANAK, sekolah_sekarang, kuota, nomor_urut, status_jurnal, sekolah_sblm, peringkat_sblm, url_target)
            elif nomor_urut > peringkat_sblm:
                pesan = buat_pesan("turun", NISN_ANAK, sekolah_sekarang, kuota, nomor_urut, status_jurnal, sekolah_sblm, peringkat_sblm, url_target)
            else:
                if peringkat_sblm == 999:
                    pesan = buat_pesan("baru", NISN_ANAK, sekolah_sekarang, kuota, nomor_urut, status_jurnal, sekolah_sblm, peringkat_sblm, url_target)
                else:
                    pesan = buat_pesan("naik", NISN_ANAK, sekolah_sekarang, kuota, nomor_urut, status_jurnal, sekolah_sblm, peringkat_sblm, url_target)
                
        set_data_sebelumnya(sekolah_sekarang, nomor_urut) 
        kirim_telegram(pesan)
    else:
        waktu = dapatkan_waktu_wib()
        pesan_hilang = f"""╔══════════════════════════╗
❌ <b>PERINGATAN KRITIS: HILANG</b> ❌
╚══════════════════════════╝
👨‍🎓 <b>Siswa NISN:</b> <code>{NISN_ANAK}</code>

⚠️ <b>STATUS DARURAT</b>
Data anak sudah <b>TIDAK TERDETEKSI</b> di seluruh 15 pilihan SMP Negeri (di 5 halaman pertama).
Segera lakukan pengecekan manual atau hubungi panitia sekolah!
┠──────────────────────────┨
⏱️ <i>Update: {waktu}</i>"""
        kirim_telegram(pesan_hilang)

# --- SCHEDULER & POLLING ---
def jalankan_otomatis():
    jadwal_menit = ["00:10", "15:10", "30:10", "45:10"]
    for waktu in jadwal_menit:
        schedule.every().hour.at(waktu).do(cek_web)

    pesan_start = f"""💎 <b>VIP SPMB MONITOR AKTIF</b> 💎
Sistem pemantauan cerdas telah menyala.

⚙️ <b>Fitur Berjalan:</b>
• Cek Otomatis tiap 15 menit
• Analisis Zona Kuota
• Deteksi Pergeseran Peringkat

🕹️ <b>Menu Perintah:</b>
<code>/cek</code> - Pindai web saat ini juga
<code>/status</code> - Lihat posisi terakhir tersimpan"""
    kirim_telegram(pesan_start)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

def dengar_perintah():
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
                        pesan_masuk = result["message"]["text"].lower()
                        chat_id_pengirim = str(result["message"]["chat"]["id"])
                        
                        if chat_id_pengirim in DAFTAR_CHAT_ID:
                            if pesan_masuk == "/cek":
                                kirim_telegram(f"🔍 <i>Memulai pemindaian super cepat ke 15 sekolah...</i>")
                                cek_web() 
                            elif pesan_masuk == "/status":
                                sek, per = get_data_sebelumnya()
                                if sek:
                                    kirim_telegram(f"📌 <b>DATA TERAKHIR TERSIMPAN:</b>\nSekolah: {sek}\nPeringkat: {per}\n\n<i>Ketik /cek untuk mengupdate data ini dari web.</i>")
                                else:
                                    kirim_telegram("Belum ada data yang tersimpan di memori. Ketik <code>/cek</code> untuk memulai scan.")
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=jalankan_otomatis, daemon=True).start()
    threading.Thread(target=dengar_perintah, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)