import requests
import time

DATASET = "vulcansiem/synthetic-syslog-1B" # Dataset
CONFIG = "default"
SPLIT = "train"
API_URL = "https://datasets-server.huggingface.co/rows"


def fetch_rows(offset: int, length: int = 100):
    params = {
        "dataset": DATASET,
        "config": CONFIG,
        "split": SPLIT,
        "offset": offset,
        "length": length,
    }
    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status() # Hata varsa
    data = resp.json()
    return [row["row"]["text"] for row in data["rows"]]


def download_sample(total_lines: int, out_path: str):
    lines = []
    offset = 0
    batch_size = 100

    while len(lines) < total_lines:
        batch = fetch_rows(offset, batch_size)
        if not batch:
            break
        lines.extend(batch)
        offset += batch_size
        print(f"{len(lines)} satir indirildi")
        time.sleep(0.3) # Diğer isteği atmadan bekle

    lines = lines[:total_lines]
    with open(out_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    print(f"Bitti: {len(lines)} satir '{out_path}' dosyasina yazildi")


if __name__ == "__main__":
    download_sample(total_lines=500, out_path="sample_data/sample_syslog.txt")