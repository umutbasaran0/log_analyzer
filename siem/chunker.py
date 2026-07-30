"""
Log kayitlarini kronolojik zaman pencerelerine ve LLM token butcesine gore alt paketlere bolen modul

"""

from datetime import datetime

def _parse_ts(ts: str) -> datetime:
    ts = ts.replace("Z", "+00:00") # Zulu time yerine 00:00 koy
    return datetime.fromisoformat(ts) # İki zamanı birbirinden çıkarabilmek için datetime nesnesine dönüştür

def time_windows(records, window_minutes: int = 5):
    windows = [] # Tamamlananları tutmak için liste
    current = [] # O anki pencereyi tutmak için liste
    window_start = None

    for rec in records:
        ts = _parse_ts(rec.timestamp)
        if window_start is None:
            window_start = ts
            
        if (ts - window_start).total_seconds() > window_minutes * 60: # Eğer süre dolmuşsa 
            windows.append((window_start, ts, current))
            current = []
            window_start = ts # Başlangıç zamanını güncelle
            
        current.append(rec) # O anki pencereye kaydı ekle

    if current: # En sonda kalan kayıtları da ekle
        windows.append((window_start, _parse_ts(current[-1].timestamp), current))
        
    return windows

def estimate_tokens(text: str) -> int: # 4 karakter başına 1 token varsay
    return max(1, len(text) // 4) # En az 1 token say


def split_by_token_budget(grouped_templates: list, max_tokens: int = 4000):
    chunks = [] # Tamamlanan chunkları tutmak için liste
    current = [] # O anki chunk
    current_tokens = 0 
    
    for g in grouped_templates:
        approx = estimate_tokens(str(g))
        
        if current and current_tokens + approx > max_tokens: # Eğer token sınırını aşarsa
            chunks.append(current) # Mevcut bloğu tamamla
            current, current_tokens = [], 0 # Yeni bir chunk başlat ve token sayısını sıfırla
            
        current.append(g) 
        current_tokens += approx
        
    if current: # En sonda kalan chunkı da ekle
        chunks.append(current)
        
    return chunks