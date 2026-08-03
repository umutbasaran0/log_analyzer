import json
from .prompts import REDUCE_SYSTEM_PROMPT
from .cost_tracker import CostTracker

REDUCE_BATCH_SIZE = 20 # LLM e tek seferde gönderilecek maksimum analiz sayısı

def _reduce_batch(analyses: list, llm_client, cost_tracker: CostTracker):
    
    user_content = json.dumps(analyses, ensure_ascii=False)  # Analiz listesini LLM in okuyabilmesi için JSON a çevir
    result, usage = llm_client.chat_json(REDUCE_SYSTEM_PROMPT, user_content, stage="reduce")
    cost_tracker.record("reduce", usage) # Harcanan token miktarını kaydet
    return result

def build_final_report(chunk_results: list, llm_client, cost_tracker: CostTracker):
   
    analyses = [c["analysis"] for c in chunk_results] # Her bir zaman penceresinin sonucundan sadece özet ksımını al
    
    while len(analyses) > REDUCE_BATCH_SIZE: # Analiz sayısı tek seferde gönderebileceğimiz sınırın üzerindeyse
        batches = [analyses[i:i + REDUCE_BATCH_SIZE] for i in range(0, len(analyses), REDUCE_BATCH_SIZE)] # Analizleri alt gruplara ayır
        analyses = [_reduce_batch(b, llm_client, cost_tracker) for b in batches] # Her grubu LLM e gönderip tek bir özet haline getir 

    final = _reduce_batch(analyses, llm_client, cost_tracker) if len(analyses) > 1 else (analyses[0] if analyses else {})

    if chunk_results: # LLM in ürettiği rapora kesin meta bilgilerini ekle
        final["time_range"] = {
            "start": chunk_results[0]["window_start"], # İlk pencerenin başlangıcı
            "end": chunk_results[-1]["window_end"], # Son pencerenin bitişi
        }
    
    final["total_raw_records"] = sum(c["record_count"] for c in chunk_results) # Satır sayılarını topla
    final["total_windows"] = len(chunk_results)
    
    return final        
