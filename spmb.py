import requests
from bs4 import BeautifulSoup
import time
import threading
import os
import schedule
from flask import Flask

# ==========================================
# KONFIGURASI BOT & DATA SISWA
# ==========================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE"
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"
URL_DASAR = "https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn=20329534"

# Nama file untuk menyimpan cache peringkat agar aman saat Render restart
FILE_PERINGKAT = "peringkat_cache.txt"
# ==========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Pemantau SPMB Aktif 24 Jam!"

# --- FUNGSI BACA/TULIS PERINGKAT ---
def get_peringkat_sebelumnya():
    if os.path.exists(FILE_PERINGKAT):
        try:
            with open(FILE_PERINGKAT, "r") as f:
                return int(f.read().strip())
        except:
            pass
    return 33 # Patokan awal jika file belum ada

def set_peringkat_sebelumnya(peringkat):
    try:
        with open(FILE_PERINGKAT, "w") as f:
            f.write(str(peringkat))
    except Exception as e:
        print("Gagal menyimpan peringkat:", e)

# --- FUNGSI TELEGRAM ---
def kirim_telegram(pesan):
    for chat_id in DAFTAR_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"}
        try:
            requests.post(url_tele, json=payload, timeout=10)
        except Exception as e:
            print(f"Gagal mengirim ke ID {chat_id}:", e)

# --- FUNGSI UTAMA SCRAPING ---
def cek_web():
    peringkat_sebelumnya = get_peringkat_sebelumnya()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    ditemukan = False
    nomor_urut = 0
    status_jurnal = ""
    
    for halaman in range(1, 6): 
        try:
            url_target = f"{URL_DASAR}&page={halaman}"
            response = requests.get(url_target, headers=headers, timeout=15)
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
                        ditemukan = True
                        break
            if ditemukan:
                break
        except Exception as e:
            print("Gagal akses web:", e)
            
    if ditemukan:
        if nomor_urut == peringkat_sebelumnya:
            pesan = f"🎉 *Yey!* NISN `{NISN_ANAK}` masih aman *stay* di peringkat **{nomor_urut}** (Jalur Prestasi) nih.\nStatus: _{status_jurnal}_"
        elif nomor_urut > peringkat_sebelumnya:
            selisih = nomor_urut - peringkat_sebelumnya
            pesan = f"📉 *Yahh udah turun nih...*\nNISN `{NISN_ANAK}` turun **{selisih} posisi** ke peringkat **{nomor_urut}** (sebelumnya {peringkat_sebelumnya}).\nStatus: _{status_jurnal}_"
        else:
            selisih = peringkat_sebelumnya - nomor_urut
            pesan = f"🚀 *Wih mantap!*\nNISN `{NISN_ANAK}` naik **{selisih} posisi** ke peringkat **{nomor_urut}** (sebelumnya {peringkat_sebelumnya})!\nStatus: _{status_jurnal}_"
            
        set_peringkat_sebelumnya(nomor_urut) 
        kirim_telegram(pesan)
    else:
        kirim_telegram(f"❌ *Waduh bahaya!* NISN `{NISN_ANAK}` sudah tidak terdeteksi di 5 halaman pertama. Cek web manual sekarang!")

# --- SCHEDULER (JADWAL OTOMATIS) ---
def jalankan_otomatis():
    # Ini jauh lebih aman dan stabil dibanding time.sleep() manual
    jadwal_menit = ["00:10", "15:10", "30:10", "45:10"]
    for waktu in jadwal_menit:
        schedule.every().hour.at(waktu).do(cek_web)

    kirim_telegram("🤖 *Bot Pemantau SPMB Aktif (Restarted/Online)!*\n- Mengecek web tiap kelipatan 15 menit (detik ke-10).\n- Ketik `/cek` untuk memantau manual.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- POLLING TELEGRAM YG DIPERBAIKI ---
def dengar_perintah():
    offset = None
    while True:
        try:
            url_get = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            # Menggunakan teknik Long-Polling yg benar: Timeout param 30s, Timeout request 40s
            params = {"timeout": 30, "offset": offset}
            response = requests.get(url_get, params=params, timeout=40).json()
            
            if response.get("ok"):
                for result in response.get("result", []):
                    offset = result["update_id"] + 1
                    
                    if "message" in result and "text" in result["message"]:
                        pesan_masuk = result["message"]["text"].lower()
                        chat_id_pengirim = str(result["message"]["chat"]["id"])
                        
                        if chat_id_pengirim in DAFTAR_CHAT_ID and pesan_masuk == "/cek":
                            kirim_telegram("🔍 *Mengecek data terbaru ke web SPMB...*")
                            cek_web() 
        except Exception as e:
            print("Koneksi polling terputus, mencoba lagi...", e)
            time.sleep(5) # Jeda sebentar jika API Telegram error agar tidak spam request

if __name__ == "__main__":
    # Menjalankan fungsi scheduler dan bot di background
    threading.Thread(target=jalankan_otomatis, daemon=True).start()
    threading.Thread(target=dengar_perintah, daemon=True).start()
    
    # Menjalankan Flask di main thread untuk UptimeRobot/Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)