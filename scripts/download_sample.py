import os
import time
import requests

DATASET = "vulcansiem/synthetic-syslog-1B"
CONFIG = "default"
SPLIT = "train"
API_URL = "https://datasets-server.huggingface.co/rows"


def fetch_rows(offset: int, length: int = 100, max_retries: int = 6):
    params = {
        "dataset": DATASET,
        "config": CONFIG,
        "split": SPLIT,
        "offset": offset,
        "length": length,
    }
    wait = 5
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(API_URL, params=params, timeout=60)
        except requests.exceptions.RequestException as e: # Sunucuya ulaşılmazsa 
            print(f"  [!] Ag hatasi ({type(e).__name__}). {wait} sn bekleyip tekrar deneniyor... ({attempt}/{max_retries})")
            time.sleep(wait)
            wait = min(wait * 2, 60)
            continue

        if resp.status_code in (429, 500, 502, 503, 504): # Sunucu hatası veya çok fazla istek gönderilirse
            print(f"  [!] (HTTP {resp.status_code}). {wait} sn bekleyip tekrar deneniyor... ({attempt}/{max_retries})")
            time.sleep(wait)
            wait = min(wait * 2, 60)
            continue

        resp.raise_for_status() 
        data = resp.json()
        return [row["row"]["text"] for row in data["rows"]]

    raise RuntimeError(f"Sunucu {max_retries} denemeden sonra hala cevap vermiyor (offset={offset}).")


def _existing_line_count(out_path: str) -> int: # Dosya varsa içindeki satır sayısını döndürür
    if not os.path.exists(out_path):
        return 0
    with open(out_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def download_sample(total_lines: int, out_path: str, batch_size: int = 100):
    existing = _existing_line_count(out_path)

    if existing >= total_lines: # İstenen satır sayısı zaten mevcutsa
        print(f"{existing} satir var (istenen {total_lines})")
        return

    if existing > 0: 
        print(f"{existing} satir zaten mevcut, oradan devam ediliyor...")

    downloaded = existing
    offset = existing  # Kaldığı yerden devam edebilmesi için offseti mevcut satır sayısına eşitle

    with open(out_path, "a", encoding="utf-8") as f: # Dosyayı ekleme modunda aç
        while downloaded < total_lines:
            remaining = total_lines - downloaded
            length = min(batch_size, remaining)
            batch = fetch_rows(offset, length)
            if not batch: # Sunucudan veri gelmezse döngüyü kır
                break
            for line in batch: # Satırları dosyaya yaz
                f.write(line + "\n")
            f.flush()

            downloaded += len(batch)
            offset += batch_size
            print(f"{downloaded} satir indirildi ve diske yazildi")
            time.sleep(0.3)

    print(f"Bitti: {downloaded} satir '{out_path}' dosyasina yazildi")


if __name__ == "__main__":
    import sys
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 500 # Varsayılan olarak 500 satır indirilecek
    out_path = sys.argv[2] if len(sys.argv) > 2 else "sample_data/sample_syslog.txt" 
    download_sample(total_lines=total, out_path=out_path)