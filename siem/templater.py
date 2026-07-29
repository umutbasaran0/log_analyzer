import re
from collections import defaultdict

IP_RE = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b") # IP adreslerini eşleştir
NUM_RE = re.compile(r"\b\d+\b") # Sayıları eşleştir


def templatize(message: str) -> str:
    t = IP_RE.sub("<IP>", message) # Önce IP leri değiştir
    t = NUM_RE.sub("<NUM>", t) # Sonra sayıları değiştir
    return t

def group_records(records):
    groups = defaultdict(lambda: { # Yeni bir grup oluştur 
        "count": 0, "hosts": set(), "src_ips": set(), "example_raw": None,
        "example_meta": None, "app": None, "severity": None, "template": None,
        "first_ts": None, "last_ts": None,
    })

    for rec in records:
        template = templatize(rec.message)
        key = (rec.app, rec.severity, template) # Gruplama anahtarı oluştur

        g = groups[key]
        g["count"] += 1
        g["hosts"].add(rec.hostname)
        if "src_ip" in rec.meta:
            g["src_ips"].add(rec.meta["src_ip"])

        if g["example_raw"] is None: # Eğer örnek yoksa ilk kaydı örnek olarak al
            g["example_raw"] = rec.raw
            g["example_meta"] = rec.meta
            g["app"] = rec.app
            g["severity"] = rec.severity
            g["template"] = template

        g["first_ts"] = g["first_ts"] or rec.timestamp # İlk zamanı al
        g["last_ts"] = rec.timestamp # Son zaman damgasını güncelle

    out = []
    for g in groups.values():
        out.append({
            "app": g["app"],
            "severity": g["severity"],
            "template": g["template"],
            "count": g["count"],
            "distinct_hosts": len(g["hosts"]), # Kaç farklı log var
            "distinct_src_ips": len(g["src_ips"]),
            "example_raw": g["example_raw"],
            "example_meta": g["example_meta"],
            "first_ts": g["first_ts"],
            "last_ts": g["last_ts"],
        })
    out.sort(key=lambda x: (-x["count"])) # En çok tekrarlananı üste koy
    return out

def compression_stats(raw_count: int, grouped: list):
    return {
        "raw_record_count": raw_count,
        "unique_template_count": len(grouped),
        "compression_ratio": round(raw_count / max(len(grouped), 1), 2),
    }