import json
from datetime import datetime, timedelta

from .prompts import QA_SYSTEM_PROMPT, QUERY_UNDERSTANDING_SYSTEM_PROMPT
from .cost_tracker import CostTracker

def _parse_ts(ts): 
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def retrieve(records, filters, dataset_end_ts, max_records=300): # Log kayıtlarını verilen filtrelere göre süzer

    time_filter_minutes = filters.get("time_filter_minutes")
    severities = set(filters.get("severity_filter") or [])  # O(1) arama hızı için listeleri set yapısına çevirir
    keywords = [k.lower() for k in (filters.get("keyword_filter") or [])]
    apps = set(filters.get("app_filter") or [])

    cutoff = None
    if time_filter_minutes:
        cutoff = dataset_end_ts - timedelta(minutes=time_filter_minutes)

    hits = []
    for rec in records:
        if cutoff and _parse_ts(rec.timestamp) < cutoff: # Zaman filtresi
            continue
        
        if severities and rec.severity not in severities: # Hata seviyesi filtresi
            continue
        
        if apps and rec.app not in apps: # Uygulama filtresi
            continue
        
        if keywords: # Anahtar kelime filtresi
            haystack = (rec.message + " " + rec.app + " " + json.dumps(rec.meta)).lower() # Aranan kelimelerin bulunacağı haystack i oluştur
            if not any(k in haystack for k in keywords): # Eğer kelimelerden hiçbiri yoksa atla
                continue
        
        hits.append(rec.to_dict()) # Tüm filtrelerden çıkan kaydı eşleşenler listesine ekle
        if len(hits) >= max_records: # LLM in context limit kontrolü
            break
            
    return hits

# Doğal dil sorusunu anlar ilgili logları çeker ve LLM ile cevap üretir
def answer_question(question: str, records: list, llm_client, cost_tracker: CostTracker, final_report: dict = None, max_records=300): 
    
    filters, usage = llm_client.chat_json(QUERY_UNDERSTANDING_SYSTEM_PROMPT, question, stage="query_understanding") # Soruyu yapılandırılmış filtrelere çevir
    cost_tracker.record("query_understanding", usage)

    dataset_end_ts = _parse_ts(records[-1].timestamp) if records else datetime.utcnow() # Filtrelere uyan kayıtları veri setinden çek
    retrieved = retrieve(records, filters, dataset_end_ts, max_records=max_records)

    context = { # LLM e gönderilecek veri bağlamını hazırla
        "question": question,
        "extracted_filters": filters,
        "retrieved_record_count": len(retrieved),
        "retrieved_records_sample": retrieved[:max_records],
    }
    
    if not retrieved and final_report is not None: # Kayıt bulunamazsa genel raporu bağlama ekle
        context["fallback_general_report"] = final_report

    result, usage2 = llm_client.chat_json(QA_SYSTEM_PROMPT, json.dumps(context, ensure_ascii=False), stage="qa") # Bağlamı LLM e gönderip son cevabı üret
    cost_tracker.record("qa", usage2)

    # Arka plan metriklerini sonuca ekle
    result["_debug_retrieved_record_count"] = len(retrieved)
    result["_debug_filters_used"] = filters

    return result