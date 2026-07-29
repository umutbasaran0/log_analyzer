import re
from dataclasses import dataclass, field
from typing import Optional

HEADER_RE = re.compile(
    r"^<(?P<pri>\d+)>(?P<version>\d+)\s+"
    r"(?P<timestamp>\S+)\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<app>\S+)\s+"
    r"(?P<procid>\S+)\s+"
    r"(?P<msgid>\S+)\s+"
    r"(?P<rest>.*)$"
)

SD_BLOCK_RE = re.compile(r"\[(?P<name>\w+)(?P<body>[^\]]*)\]") # Köşeli parantezler için
SD_KV_RE = re.compile(r'(\w+)="([^"]*)"') # Blokların içindeki key-value için


@dataclass
class LogRecord:
    raw: str
    timestamp: str
    hostname: str
    app: str
    procid: str
    severity: str = "UNKNOWN"
    meta: dict = field(default_factory=dict) # Her nesne için temiz bir dict oluştur
    message: str = ""

    def to_dict(self): # LogRecord nesnesin dict formatına çevir
        return {
            "timestamp": self.timestamp,
            "hostname": self.hostname,
            "app": self.app,
            "procid": self.procid,
            "severity": self.severity,
            "meta": self.meta,
            "message": self.message,
        }

def parse_line(line: str)-> Optional[LogRecord]:
    line = line.strip() # Satırın baş ve sonundaki boşlukları temizle
    if not line:
        return None
    
    m = HEADER_RE.match(line)
    if not m: # Eğer kalıp eşleşmezse 
        return None

    rest = m.group("rest")

    meta = {}
    pos = 0
    while True:
        block_match = SD_BLOCK_RE.match(rest, pos)
        if not block_match:
            break
        for k, v in SD_KV_RE.findall(block_match.group("body")): # Eşleşenleri bul
            meta[k] = v # Kaydet
        pos = block_match.end()

    message = rest[pos:].strip()
    severity = meta.pop("severity", "UNKNOWN").upper() 

    # Ayrılanları nesnelerine ata
    return LogRecord(
        raw=line,
        timestamp=m.group("timestamp"),
        hostname=m.group("hostname"),
        app=m.group("app"),
        procid=m.group("procid"),
        severity=severity,
        message=message,
        meta=meta
    )

def parse_file(path: str, limit: Optional[int] = None):
    parsed = 0
    unparsed = 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f: # Satır satır oku
            if limit is not None and parsed >= limit:
                break
            rec = parse_line(line)

            if rec is None: # Satır parse edilmezse
                unparsed += 1
                continue

            parsed += 1
            yield rec # Satırla iş bittiğinde nesneyi o anda döndür

    if unparsed:
        print(f"[syslog_parser] Uyari: {unparsed} satir ayristirilamadi ve atlandi")

if __name__ == "__main__":
    import sys
    for i, rec in enumerate(parse_file(sys.argv[1] if len(sys.argv) > 1 else "sample_data/sample_syslog.txt", limit=5)):
        print(rec.to_dict())