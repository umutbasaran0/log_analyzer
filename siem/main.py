"""
Tum modulleri sirasiyla calistiran ve projeyi komut satiri aracina donusturen ana modul

"""

import argparse
import json
import os
from .syslog_parser import parse_file
from .analyzer import analyze_records
from .aggregator import build_final_report
from .qa import answer_question
from .llm_client import LLMClient
from .cost_tracker import CostTracker


def build_arg_parser(): # Terminalden girilen argümanları yapılandırır
    parser = argparse.ArgumentParser(description="LLM ile syslog analiz pipeline'ı")
    parser.add_argument("--input", default="sample_data/sample_syslog.txt", help="Girdi log dosyasının yolu")
    parser.add_argument("--limit", type=int, default=None, help="En fazla kaç satır okunacak (test için)")
    parser.add_argument("--window-minutes", type=float, default=5, help="Zaman penceresi boyutu (dakika)")
    parser.add_argument("--max-tokens-per-chunk", type=int, default=4000, help="Alt-chunk başına token bütçesi")
    parser.add_argument("--mock", action="store_true", help="LLM çağrılarını mock modda çalıştır")
    parser.add_argument("--ask", default=None, help="Rapor sonrası sorulacak doğal dil sorusu")
    parser.add_argument("--output", default="output/report.json", help="Rapor çıktısının yazılacağı dosya")
    return parser


def run(args): # Pipeline çalıştırır
    print(f"[main] Dosya okunuyor: {args.input} (limit={args.limit})")

    # Log dosyasını oku ve LogRecord nesnelerine dönüştür
    records = list(parse_file(args.input, limit=args.limit))
    print(f"[main] {len(records)} kayıt ayrıştırıldı.")

    if not records: # Dosya boşsa veya okunamadıysa çıkış yap
        print("[main] Hiç kayıt okunamadı, çıkılıyor.")
        return

    # İstemciyi ve maliyet takipçisini oluştur.
    client = LLMClient(mock=args.mock)
    print(f"[main] LLM istemcisi hazır (mock={client.mock})")
    cost_tracker = CostTracker()

    print("[main] Analiz ediliyor (map adımı)...")
    chunk_results = analyze_records( # Logları zaman pencerelerine bölüp parçalar halinde özetlet
        records, client, cost_tracker,
        window_minutes=args.window_minutes,
        max_tokens_per_chunk=args.max_tokens_per_chunk,
    )
    print(f"[main] {len(chunk_results)} zaman penceresi analiz edildi.")

    print("[main] Genel rapor oluşturuluyor (reduce adımı)...")
    final_report = build_final_report(chunk_results, client, cost_tracker) # Parça analizleri tek bir ana yönetici özetinde birleştir

    if args.ask: # Kullanıcı argüman olarak bir soru sorduysa 
        print(f"[main] Soru cevaplanıyor: {args.ask}")
        qa_result = answer_question(args.ask, records, client, cost_tracker, final_report=final_report)
        final_report["qa"] = {"question": args.ask, "result": qa_result}

    os.makedirs(os.path.dirname(args.output), exist_ok=True) # Dosyaya yazma
    with open(args.output, "w", encoding="utf-8") as f: # Raporu JSON formatında diske kaydet
        json.dump(final_report, f, ensure_ascii=False, indent=2)
    print(f"[main] Rapor yazıldı: {args.output}")

    summary = cost_tracker.summary() # Programın çalışması boyunca harcanan API maliyetini ekrana bas
    print("[main] Maliyet özeti:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    return final_report


if __name__ == "__main__":
    arg_parser = build_arg_parser()
    parsed_args = arg_parser.parse_args()
    run(parsed_args)