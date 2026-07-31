"""
DeepSeek LLM API istemcisi. Hem gercek HTTP isteklerini yonetir hem de cevrimdisi testler icin Mock mod sunar.

"""

import json
import os
import random
import requests

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

class LLMClient:
    def __init__(self, api_key: str = None, mock: bool = None):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY") # API anahtarını parametreden veya çevre değişkenlerinden al
        self.mock = mock if mock is not None else (self.api_key is None) # Mock parametresi verilmediyse anahtara göre otomatik karar ver


    def _mock_qa(self, payload): # API anahtarı olmadığında sahte QA yanıtı üretir
        return {
            "answer": "[MOCK] API anahtari olmadan uretilen basit bir cevaptir. Gercek DEEPSEEK_API_KEY ile calistirildiginda burada context'teki kayitlara dayanan gerçek bir LLM cevabi olacak.",
            "evidence": ["mock modda gercek cikarim yapilmaz pipeline'in calistigi gosterilir"],
        }


    def _mock_query_understanding(self, question_text: str): # Soruyu kural tabanlı taramayla filtre parametrelerine çevirir
        q = question_text.lower()
        severity_filter = []
        
        for s in ["error", "critical", "warning", "hata", "kritik"]:
            if s in q:
                severity_filter.append({ "hata": "ERROR", "error": "ERROR", "critical": "CRITICAL", "kritik": "CRITICAL", "warning": "WARNING" }[s])
                
        time_filter = 60 if ("son bir saat" in q or "son 1 saat" in q) else None
        keyword_filter = []
        
        for kw in ["ssh", "brute", "güvenlik", "security", "drop", "firewall"]:
            if kw in q:
                keyword_filter.append(kw)
                
        return {
            "time_filter_minutes": time_filter,
            "severity_filter": list(set(severity_filter)), # set ile tekrar edilen kayıtlar temizlenir
            "keyword_filter": keyword_filter,
            "app_filter": ["sshd"] if "ssh" in q else [],
        }


    def _mock_chunk_analysis(self, groups: list): # Grupları inceleyerek sahte bir chunk analizi üretir
        severity_breakdown = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        top_categories = []
        clusters_by_app = {}
        anomalies = []

        CATEGORY_MAP = { # Uygulama adlarını güvenlik kategorileriyle eşleştirir
            "sshd": "ssh_auth",
            "kernel": "firewall_net",
            "nginx": "http_traffic",
            "sudo": "privileged_command",
            "cron": "cron_job",
        }

        for g in groups:
            sev = g.get("severity", "UNKNOWN")
            if sev in severity_breakdown:
                severity_breakdown[sev] += g.get("count", 0) # Grup tekrar sayısını severity breakdowna ekle

            category = CATEGORY_MAP.get(g.get("app"), g.get("app", "unknown")) # Uygulama adı haritada yoksa çökmesini engeller
            top_categories.append({"category": category, "template": g.get("template"), "count": g.get("count", 0)})

            clusters_by_app.setdefault(category, []).append(g.get("template"))

            if sev == "CRITICAL": # Kayıt seviyesi CRITICAL ise anomali listesine doğrudan ekle
                anomalies.append({
                    "description": f"CRITICAL seviyeli olay: {g.get('template')}",
                    "severity": "CRITICAL",
                    "evidence_template": g.get("template"),
                    "reason": "Severity=CRITICAL olarak isaretlenmis kayit tespit edildi.",
                })
            
            if (g.get("app") == "sshd" and "Failed password" in (g.get("template") or "") # SSH başarısız giriş denemelerini tespit et ve anomali olarak ekle
            and g.get("count", 0) >= 10 and g.get("distinct_src_ips", 99) <= 2):
                anomalies.append({
                    "description": f"Tek/az sayida IP'den {g['count']} kez başarisiz ssh girişi denemesi",
                    "severity": "HIGH",
                    "evidence_template": g.get("template"),
                    "reason": "Az sayida kaynak IP'den yüksek sayida basarisiz kimlik dogrulama olabilir.",
                })

        top_categories.sort(key=lambda x: -x["count"]) # En çok tekrar edenden en aza doğru sırala
        clusters = [{"cluster_label": k, "related_templates": list(set(v))[:5], "reason": "ayni uygulama kaynakli iliskili kayitlar"} 
                    for k, v in clusters_by_app.items()]

        return {
            "chunk_summary": (f"[MOCK] Bu pencerede {sum(severity_breakdown.values())} kayit (sablonlanmis "
                              f"{len(groups)} benzersiz desen) analiz edildi. En sik kategori: "
                              f"{top_categories[0]['category'] if top_categories else 'yok'}."),
            "severity_breakdown": severity_breakdown,
            "top_categories": top_categories[:10],  # En sık görülen ilk 10 kategori
            "clusters": clusters,
            "anomalies": anomalies,
        }


    def _mock_reduce(self, chunk_summaries): # Birden fazla chunk analiz ozetini birlestirerek tek bir genel rapor uretir
        if not isinstance(chunk_summaries, list):
            chunk_summaries = []
            
        total_sev = {"DEBUG": 0, "INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
        all_anomalies = []
        all_categories = {}
        
        for c in chunk_summaries:
            for k, v in c.get("severity_breakdown", {}).items():
                total_sev[k] = total_sev.get(k, 0) + v

            all_anomalies.extend(c.get("anomalies", []))

            for cat in c.get("top_categories", []):
                all_categories[cat["category"]] = all_categories.get(cat["category"], 0) + cat["count"]

        sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3} # Kritiklik derecesine göre anomali sıralama
        all_anomalies.sort(key=lambda a: sev_order.get(a.get("severity", "LOW"), 3))

        top_error_types = sorted(
            [{"category": k, "total_count": v, "note": "toplam gozlem sayisi"} for k, v in all_categories.items()],
            key=lambda x: -x["total_count"]
        )[:10]

        return {
            "total_chunks_analyzed": len(chunk_summaries),
            "overall_summary": (f"[MOCK] {len(chunk_summaries)} zaman penceresi analiz edildi. "
                                f"Toplam {sum(total_sev.values())} kayit islendi. "
                                f"{len(all_anomalies)} potansiyel anomali sinyali tespit edildi."),
            "top_error_types": top_error_types,
            "recurring_patterns": [
                {
                    "pattern": k, 
                    "chunks_seen_in": sum(1 for c in chunk_summaries if any(cc['category'] == k for cc in c.get('top_categories', [])))
                }
                for k in list(all_categories.keys())[:10]
            ],
            "anomalies_ranked": all_anomalies,
            "security_signals": [
                a for a in all_anomalies 
                if "ssh" in a.get("description", "").lower() or "brute" in a.get("reason", "").lower()
            ],
            "severity_breakdown_total": total_sev,
        }


    def _mock_response(self, stage: str, user_content: str): # Mock modda gelen isteğin türüne göre uygun sahte yanıtı ve tahmini token kullanımını üretir
        try:
            payload = json.loads(user_content) # Gelen içeriğin JSON formatında olup olmadığını kontrol et
        except Exception:
            payload = None

        prompt_tokens = max(1, len(user_content) // 4) # Tahmini token sayısı 

        if stage == "chunk_analysis" and isinstance(payload, list):
            result = self._mock_chunk_analysis(payload)
        elif stage == "reduce":
            result = self._mock_reduce(payload)
        elif stage == "qa":
            result = self._mock_qa(payload)
        elif stage == "query_understanding":
            result = self._mock_query_understanding(user_content)
        else:
            result = {"note": "mock mode: tanınmayan stage"}

        completion_tokens = max(1, len(json.dumps(result)) // 4) # Tahmini token sayısı
        return result, {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens}


    def chat_json(self, system_prompt: str, user_content: str, stage: str = "generic"): # DeepSeek LLM API'sine istek atar. mock mod aktifse yerel mock yanıtlarını döner
        if self.mock: # Eğer mock mod açıksa 
            return self._mock_response(stage, user_content)

        resp = requests.post( # Gerçek DeepSeek API sunucusuna HTTPS POST isteği gönder
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}", # API anahtarı 
            },
            json={
                "model": DEEPSEEK_MODEL, 
                "temperature": 0.2, # Yaratıcılığı düşür ve tutarlı sonuçlar ver
                "response_format": {"type": "json_object"}, # JSON nesnesi olarak yanıt al
                "messages": [
                    {"role": "system", "content": system_prompt}, # Yapay zekaya rolü ve kuralları veren talimat
                    {"role": "user", "content": user_content}, # Yapay zekaya analiz için gönderilen veri-soru
                ],
            },
            timeout=120, # Yanıt için en fazla 120 saniye bekle
        )
        resp.raise_for_status() # İstekte bir hata varsa programı durdurup hata fırlat
        data = resp.json()
        content = data["choices"][0]["message"]["content"] # Yapay zekanın yazdığı metin içeriği
        usage = data.get("usage", {}) # Harcanan gerçek token bilgileri
        try:
            parsed = json.loads(content) # Metin geçerli bir JSON mı
        except json.JSONDecodeError:
            parsed = {"raw_unparsed_response": content} # Bozulduysa ham metni sakla
        return parsed, {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }