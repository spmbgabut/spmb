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
CHAT_ID = "7330553314"
NISN_ANAK = "0145096765"
URL_DASAR = "https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn=20329534"
# ==========================================

# Setup Flask Server (Syarat wajib untuk Render)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Pemantau SPMB Sedang Berjalan 24 Jam!"

def kirim_telegram(pesan):
    url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}
    try:
        requests.post(url_tele, json=payload)
    except:
        pass

def cek_web():
    headers = {'User-Agent': 'Mozilla/5.0'}
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

# Fungsi ini yang akan berjalan terus di background
def jalankan_bot():
    kirim_telegram("🤖 *Bot Pindah ke Cloud (Render)!*\nSistem berjalan nonstop 24 jam.")
    while True:
        cek_web()
        time.sleep(1800)

if __name__ == "__main__":
    # 1. Jalankan bot pengecek web di jalur (thread) terpisah
    bot_thread = threading.Thread(target=jalankan_bot)
    bot_thread.start()
    
    # 2. Jalankan server web mini agar Render tidak mematikan program
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)