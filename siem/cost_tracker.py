"""
DeepSeek API maliyetlerini ve token kullanimlarini takip eden modul.

"""

# 1 Milyon Token Başına Fiyatlandırma 
PRICE_PER_M_INPUT = 0.14
PRICE_PER_M_OUTPUT = 0.28

class CostTracker:
    def __init__(self):
        self.calls = []

    def record(self, stage: str, usage: dict):
        prompt_tokens = usage.get("prompt_tokens", 0) # Gerçek veriyi alamazsa 0 olarak varsay
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = (prompt_tokens / 1_000_000 * PRICE_PER_M_INPUT + completion_tokens / 1_000_000 * PRICE_PER_M_OUTPUT)
        
        self.calls.append({ # Kayıtları listeye ekle
            "stage": stage,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": round(cost, 6), # 6 ondalık basamağa yuvarla
        })
        
        return cost

    def summary(self):
        # Genel toplamlarını hesapla
        total_prompt = sum(c["prompt_tokens"] for c in self.calls)
        total_completion = sum(c["completion_tokens"] for c in self.calls)
        total_cost = sum(c["cost_usd"] for c in self.calls)

        # Aşama bazında özet oluştur
        by_stage = {}
        for c in self.calls:
            s = by_stage.setdefault(c["stage"], {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0})
            # Toplamlarını güncelle
            s["calls"] += 1
            s["prompt_tokens"] += c["prompt_tokens"]
            s["completion_tokens"] += c["completion_tokens"]
            s["cost_usd"] += c["cost_usd"]
            
        return { # Toplam özet bilgileri
            "total_calls": len(self.calls),
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_cost_usd": round(total_cost, 6),
            "by_stage": {k: {**v, "cost_usd": round(v["cost_usd"], 6)} for k, v in by_stage.items()}, 
        }