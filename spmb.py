import requests
from bs4 import BeautifulSoup
import time
import threading
import os
from flask import Flask

# ==========================================
# KONFIGURASI BOT & DATA SISWA
# ==========================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE"
# Gunakan list [...] untuk memasukkan lebih dari 1 ID
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"
URL_DASAR = "https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn=20329534"
# ==========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Pemantau SPMB Aktif 24 Jam untuk 2 Pengguna!"

def kirim_telegram(pesan):
    # Looping: Kirim pesan satu per satu ke setiap ID yang terdaftar
    for chat_id in DAFTAR_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"}
        try:
            requests.post(url_tele, json=payload)
        except Exception as e:
            print(f"Gagal mengirim ke ID {chat_id}:", e)

def cek_web():
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
        except:
            pass
            
    if ditemukan:
        if nomor_urut <= 45:
            pesan = f"✅ *STATUS AMAN!*\nNISN `{NISN_ANAK}` berada di **Peringkat {nomor_urut}**.\nStatus: *{status_jurnal}*."
            kirim_telegram(pesan)
        else:
            pesan = f"⚠️ *PERINGATAN CADANGAN!*\nPosisi NISN `{NISN_ANAK}` turun ke **Peringkat {nomor_urut}**!\nStatus: *{status_jurnal}*.\n🚨 Hati-hati tergeser dari kuota aman!"
            kirim_telegram(pesan)
    else:
        kirim_telegram(f"❌ *BAHAYA!*\nNISN `{NISN_ANAK}` tidak terdeteksi. Segera cek web manual!")

def jalankan_otomatis():
    kirim_telegram("🤖 *Bot Pemantau SPMB (Multi-User) Aktif!*\n- Laporan masuk ke 2 akun setiap 30 menit.\n- Ketik `/cek` jika ingin mengecek sekarang.")
    while True:
        time.sleep(1800)
        cek_web()

def dengar_perintah():
    offset = None
    while True:
        try:
            url_get = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
            params = {"timeout": 10, "offset": offset}
            response = requests.get(url_get, params=params, timeout=15).json()
            
            if response.get("ok"):
                for result in response.get("result", []):
                    offset = result["update_id"] + 1
                    
                    if "message" in result and "text" in result["message"]:
                        pesan_masuk = result["message"]["text"].lower()
                        chat_id_pengirim = str(result["message"]["chat"]["id"])
                        
                        # Cek apakah pengirim adalah salah satu dari ID terdaftar
                        if chat_id_pengirim in DAFTAR_CHAT_ID and pesan_masuk == "/cek":
                            # Memberitahu secara spesifik siapa yang meminta pengecekan
                            kirim_telegram(f"🔍 *Seseorang meminta pengecekan. Sedang menarik data terbaru...*")
                            cek_web() 
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    thread_otomatis = threading.Thread(target=jalankan_otomatis)
    thread_otomatis.start()
    
    thread_perintah = threading.Thread(target=dengar_perintah)
    thread_perintah.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)