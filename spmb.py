import requests
from bs4 import BeautifulSoup
import time
import threading
import os
import schedule
import concurrent.futures # <-- Modul baru untuk mempercepat pencarian
from flask import Flask

# ==========================================
# KONFIGURASI BOT & DATA SISWA
# ==========================================
TOKEN = "8685597392:AAGO0Ih6aL4z9krjC8iC7DJmhr2_mdIbNRE" # Segera reset token ini di BotFather ya!
DAFTAR_CHAT_ID = ["7330553314", "8552443015"] 
NISN_ANAK = "0145096765"

DAFTAR_SEKOLAH = {
    "20329531": "SMPN 1 Pekalongan",
    "20329533": "SMPN 2 Pekalongan",
    "20329534": "SMPN 3 Pekalongan",
    "20329535": "SMPN 4 Pekalongan",
    "20331635": "SMPN 5 Pekalongan",
    "20329536": "SMPN 6 Pekalongan",
    "20329547": "SMPN 7 Pekalongan",
    "20331636": "SMPN 8 Pekalongan",
    "20331637": "SMPN 9 Pekalongan",
    "20331628": "SMPN 10 Pekalongan",
    "20331629": "SMPN 11 Pekalongan",
    "20331630": "SMPN 12 Pekalongan",
    "20331631": "SMPN 13 Pekalongan",
    "20331632": "SMPN 14 Pekalongan",
    "20329532": "SMPN 15 Pekalongan"
}

FILE_CACHE = "data_cache_spmb.txt"
# ==========================================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Pemantau SPMB Super Cepat Aktif 24 Jam!"

# --- FUNGSI BACA/TULIS CACHE ---
def get_data_sebelumnya():
    if os.path.exists(FILE_CACHE):
        try:
            with open(FILE_CACHE, "r") as f:
                data = f.read().strip().split("|")
                if len(data) == 2:
                    return data[0], int(data[1])
        except:
            pass
    return "", 999 

def set_data_sebelumnya(nama_sekolah, peringkat):
    try:
        with open(FILE_CACHE, "w") as f:
            f.write(f"{nama_sekolah}|{peringkat}")
    except Exception as e:
        print("Gagal menyimpan data:", e)

def kirim_telegram(pesan):
    for chat_id in DAFTAR_CHAT_ID:
        url_tele = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"}
        try:
            requests.post(url_tele, json=payload, timeout=10)
        except Exception as e:
            pass

# --- FUNGSI PENCARIAN 1 SEKOLAH (Dijalankan Paralel) ---
def cek_satu_sekolah(npsn, nama_sekolah):
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
                            "peringkat": nomor_urut, 
                            "status": status_jurnal
                        }
        except Exception:
            continue # Abaikan error koneksi agar tidak merusak loop
    return {"ditemukan": False}

# --- FUNGSI UTAMA SCRAPING (Super Cepat) ---
def cek_web():
    sekolah_sblm, peringkat_sblm = get_data_sebelumnya()
    hasil_akhir = None
    
    # Menjalankan 15 pencarian web secara BERSAMAAN
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(cek_satu_sekolah, npsn, nama): nama for npsn, nama in DAFTAR_SEKOLAH.items()}
        
        for future in concurrent.futures.as_completed(futures):
            hasil = future.result()
            if hasil["ditemukan"]:
                hasil_akhir = hasil
                break # Begitu ketemu 1, langsung berhenti menunggu yang lain
                
    if hasil_akhir:
        sekolah_sekarang = hasil_akhir["sekolah"]
        nomor_urut = hasil_akhir["peringkat"]
        status_jurnal = hasil_akhir["status"]
        
        if sekolah_sblm != "" and sekolah_sekarang != sekolah_sblm:
            pesan = f"🔄 *PINDAH SEKOLAH TERDETEKSI!*\nNISN `{NISN_ANAK}` sekarang terdaftar di **{sekolah_sekarang}** pada peringkat **{nomor_urut}**.\n(Sebelumnya di {sekolah_sblm}).\nStatus: _{status_jurnal}_"
        else:
            if nomor_urut == peringkat_sblm:
                pesan = f"🎉 *Aman!* NISN `{NISN_ANAK}` masih *stay* di **{sekolah_sekarang}** peringkat **{nomor_urut}**.\nStatus: _{status_jurnal}_"
            elif nomor_urut > peringkat_sblm:
                selisih = nomor_urut - peringkat_sblm
                pesan = f"📉 *Turun posisi nih...*\nDi **{sekolah_sekarang}**, NISN `{NISN_ANAK}` turun **{selisih} posisi** ke peringkat **{nomor_urut}** (sebelumnya {peringkat_sblm}).\nStatus: _{status_jurnal}_"
            else:
                if peringkat_sblm == 999:
                    pesan = f"✨ *Data Baru Ditemukan!*\nNISN `{NISN_ANAK}` masuk di **{sekolah_sekarang}** peringkat **{nomor_urut}**.\nStatus: _{status_jurnal}_"
                else:
                    selisih = peringkat_sblm - nomor_urut
                    pesan = f"🚀 *Wih mantap!*\nDi **{sekolah_sekarang}**, NISN `{NISN_ANAK}` naik **{selisih} posisi** ke peringkat **{nomor_urut}** (sebelumnya {peringkat_sblm})!\nStatus: _{status_jurnal}_"
                
        set_data_sebelumnya(sekolah_sekarang, nomor_urut) 
        kirim_telegram(pesan)
    else:
        kirim_telegram(f"❌ *Peringatan!* NISN `{NISN_ANAK}` sudah tidak terdeteksi di *seluruh 15 SMP Negeri* (di 5 halaman pertama). Cek web manual sekarang!")

# --- SCHEDULER & POLLING ---
def jalankan_otomatis():
    jadwal_menit = ["00:10", "15:10", "30:10", "45:10"]
    for waktu in jadwal_menit:
        schedule.every().hour.at(waktu).do(cek_web)

    kirim_telegram("🤖 *Bot Pemantau SPMB Super Cepat Aktif!*\n- Pengecekan otomatis tiap 15 menit.\n- Ketik `/cek` untuk memantau manual.")
    
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
                        
                        if chat_id_pengirim in DAFTAR_CHAT_ID and pesan_masuk == "/cek":
                            kirim_telegram("⚡ *Sedang nge-scan 15 sekolah sekaligus...*")
                            cek_web() 
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=jalankan_otomatis, daemon=True).start()
    threading.Thread(target=dengar_perintah, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)