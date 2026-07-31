import json
from . import chunker, templater
from .prompts import CHUNK_ANALYSIS_SYSTEM_PROMPT
from .cost_tracker import CostTracker

def analyze_records(records, llm_client, cost_tracker: CostTracker, window_minutes: int = 5, max_tokens_per_chunk: int = 4000):
    windows = chunker.time_windows(records, window_minutes=window_minutes) # Zaman pencerelerine göre kayıtları grupla
    chunk_results = []

    for window_start, window_end, window_records in windows: # Her bir zaman penceresi için
        grouped = templater.group_records(window_records) # Kayıtları grupla
        comp_stats = templater.compression_stats(len(window_records), grouped) # Sıkıştırma istatistiklerini hesapla

        # Gruplanmış kayıtları token bütçesine göre alt parçalara ayır
        sub_chunks = chunker.split_by_token_budget(grouped, max_tokens=max_tokens_per_chunk)    

        # O pencere için analiz sonuçlarını birleştir
        merged_analysis = {"top_categories": [], "clusters": [], "anomalies": [], "severity_breakdown": {}, "chunk_summary": ""}

        for sub in sub_chunks: # Her bir alt parçayı analiz et
            user_content = json.dumps(sub, ensure_ascii=False) # LLM e göndermek için JSON formatına çevir
            result, usage = llm_client.chat_json(CHUNK_ANALYSIS_SYSTEM_PROMPT, user_content, stage="chunk_analysis")
            cost_tracker.record("chunk_analysis", usage) # Harcanan tokenleri kaydet

            # Birleştirilmiş analiz sonuçlarını güncelle
            merged_analysis["top_categories"].extend(result.get("top_categories", []))
            merged_analysis["clusters"].extend(result.get("clusters", []))
            merged_analysis["anomalies"].extend(result.get("anomalies", []))

            for k, v in result.get("severity_breakdown", {}).items(): # Hata seviyelerini topla
                merged_analysis["severity_breakdown"][k] = merged_analysis["severity_breakdown"].get(k, 0) + v

            if result.get("chunk_summary"): # Eğer özet geldiyse 
                merged_analysis["chunk_summary"] += (" " if merged_analysis["chunk_summary"] else "") + result["chunk_summary"]

        chunk_results.append({ # Pencere için sonuçları kaydet
            "window_start": str(window_start),
            "window_end": str(window_end),
            "record_count": len(window_records),
            "compression": comp_stats,
            "analysis": merged_analysis,
        })

    return chunk_results