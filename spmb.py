import requests
from bs4 import BeautifulSoup
import time
import threading
import os
import datetime
from flask import Flask

# ==========================================
# KONFIGURASI BOT & DATA SISWA
# ==========================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE"
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"
URL_DASAR = "https://spmb.dindik.pekalongankota.go.id/smp/jurnal/default/detail?npsn=20329534"

# Variabel untuk mengingat posisi terakhir (patokan awal)
peringkat_sebelumnya = 33 
# ==========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Pemantau SPMB Aktif 24 Jam!"

def kirim_telegram(pesan):
    for chat_id in DAFTAR_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"}
        try:
            requests.post(url_tele, json=payload)
        except Exception as e:
            print(f"Gagal mengirim ke ID {chat_id}:", e)

def cek_web():
    global peringkat_sebelumnya
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
        # LOGIKA PERBANDINGAN PERINGKAT (KHUSUS JALUR PRESTASI)
        if nomor_urut == peringkat_sebelumnya:
            pesan = f"🎉 *Yey!* NISN `{NISN_ANAK}` masih aman *stay* di peringkat **{nomor_urut}** (Jalur Prestasi) nih. Poin kita masih kuat menahan pendaftar baru.\nStatus: _{status_jurnal}_"
            
        elif nomor_urut > peringkat_sebelumnya:
            selisih = nomor_urut - peringkat_sebelumnya
            pesan = f"📉 *Yahh udah turun nih...*\nNISN `{NISN_ANAK}` turun **{selisih} posisi** ke peringkat **{nomor_urut}** (sebelumnya peringkat {peringkat_sebelumnya}).\nPasti ada pendaftar baru di Jalur Prestasi dengan total poin/nilai yang lebih tinggi geser posisi kita.\nStatus: _{status_jurnal}_"
            
        else:
            selisih = peringkat_sebelumnya - nomor_urut
            pesan = f"🚀 *Wih mantap!*\nNISN `{NISN_ANAK}` malah naik **{selisih} posisi** ke peringkat **{nomor_urut}** (sebelumnya peringkat {peringkat_sebelumnya})! \nKayaknya ada pendaftar Jalur Prestasi di atas kita yang cabut berkas atau pindah jalur.\nStatus: _{status_jurnal}_"
            
        # Update patokan peringkat untuk 15 menit ke depan
        peringkat_sebelumnya = nomor_urut 
        kirim_telegram(pesan)
    else:
        kirim_telegram(f"❌ *Waduh bahaya!* NISN `{NISN_ANAK}` sudah tidak terdeteksi di 5 halaman pertama. Segera cek web manual, takutnya terlempar dari kuota Jalur Prestasi!")

def tunggu_sampai_jadwal_berikutnya():
    sekarang = datetime.datetime.now()
    
    # Mencari target waktu kelipatan 15 terdekat di detik ke-10
    for target_menit in [0, 15, 30, 45]:
        target_waktu = sekarang.replace(minute=0, second=10, microsecond=0)
        
        if target_menit == 0:
            if sekarang.minute >= 45:
                target_waktu = target_waktu + datetime.timedelta(hours=1)
        else:
            target_waktu = target_waktu.replace(minute=target_menit)
            
        selisih = (target_waktu - sekarang).total_seconds()
        
        if selisih > 0:
            print(f"Menunggu {int(selisih)} detik sampai {target_waktu.strftime('%H:%M:%S')}...")
            time.sleep(selisih)
            return

def jalankan_otomatis():
    kirim_telegram("🤖 *Bot Pemantau SPMB (Jalur Prestasi) Aktif!*\n- Mengecek web setiap 15 menit, persis di detik ke-10.\n- Ketik `/cek` kalau mau lihat update sekarang juga.")
    while True:
        tunggu_sampai_jadwal_berikutnya()
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
                        
                        if chat_id_pengirim in DAFTAR_CHAT_ID and pesan_masuk == "/cek":
                            kirim_telegram("🔍 *Siap! Mengecek data Jalur Prestasi langsung ke web sekarang...*")
                            cek_web() 
        except Exception as e:
            time.sleep(5)

if __name__ == "__main__":
    thread_otomatis = threading.Thread(target=jalankan_otomatis)
    thread_otomatis.daemon = True
    thread_otomatis.start()
    
    thread_perintah = threading.Thread(target=dengar_perintah)
    thread_perintah.daemon = True
    thread_perintah.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)