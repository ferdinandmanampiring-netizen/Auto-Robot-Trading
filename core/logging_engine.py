import datetime
import os

def log(msg):
    """
    Sistem logging terpusat: Terminal + File Log.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    
    # 1. Tampilkan di terminal (Output VS Code)
    print(full_msg)
    
    # 2. Simpan ke file sniper_system.log
    try:
        log_file = "sniper_system.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(full_msg + "\n")
    except Exception as e:
        print(f"❌ Gagal menulis log ke file: {e}")
