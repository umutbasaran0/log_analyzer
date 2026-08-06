# Log Analyzer — LLM ile Syslog Analiz Sistemi

🇬🇧 [Read in English](README.en.md)

Büyük hacimli syslog verilerini, LLM (DeepSeek Flash v4) yardımıyla analiz eden bir prototip.
Şablonlama, zaman/token bazlı chunking ve RAG-benzeri retrieval kullanarak, milyonlarca satırlık
veriyi doğrudan modele göndermeden, ölçeklenebilir ve maliyet-etkin şekilde analiz eder.

Detaylı mimari açıklaması için [docs/01_architecture.md](docs/01_architecture.md).

## Gereksinimler

- Python 3.11+
- (Gerçek analiz için) DeepSeek API anahtarı — https://platform.deepseek.com/

## Kurulum

​```powershell
git clone https://github.com/umutbasaran0/log_analyzer.git
cd log_analyzer
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
​```

### API Anahtarını Ayarlama

Gerçek DeepSeek API ile çalışmak için, proje kök dizininde bir `.env` dosyası gerekir:

​```powershell
"DEEPSEEK_API_KEY=sk-senin-gercek-keyin" | Set-Content -NoNewline -Encoding ascii .env
​```

`.env` dosyası `.gitignore` ile korunuyor, asla repoya commit'lenmez. Bu dosya yoksa (veya
`--mock` bayrağı verilirse) sistem otomatik olarak mock moda geçer — DeepSeek'e gerçek istek
atmaz, ücretsiz test için kural tabanlı sahte JSON döner.

## Örnek Veri İndirme

Proje, [vulcansiem/synthetic-syslog-1B](https://huggingface.co/datasets/vulcansiem/synthetic-syslog-1B)
veri setinin  küçük bir alt kümesiyle çalışır — prototip amaçlı 500 ile 50.000 satır arasında farklı boyutlarda test edilmiştir:

​```powershell
python scripts\download_sample.py 500 sample_data\sample_syslog.txt
​```

## Çalıştırma

### Mock modda (API anahtarı gerekmez, ücretsiz test için)

​```powershell
python -m siem.main --input sample_data\sample_syslog.txt --limit 500 --mock
​```

### Gerçek DeepSeek API ile

`.env` dosyası ayarlandıysa, `--mock` bayrağı verilmeden çalıştırılması yeterlidir:

​```powershell
python -m siem.main --input sample_data\sample_syslog.txt --limit 500
​```

### Doğal dil soru sorma (RAG)

Analiz bittikten sonra `--ask` ile soru sorulabilir; sistem önce soruyu filtrelere çevirir (query
understanding), ilgili kayıtları yerel olarak süzer (retrieval), sonra sadece bu alt kümeyi LLM'e
göndererek cevap üretir:

​```powershell
python -m siem.main --input sample_data\sample_syslog.txt --limit 500 --ask "en sık karşılaşılan hata türleri nelerdir?"
​```

### Tüm parametreler

| Parametre | Varsayılan | Açıklama |
|---|---|---|
| `--input` | `sample_data/sample_syslog.txt` | Girdi log dosyası |
| `--limit` | (yok, tüm dosya) | En fazla kaç satır okunacak |
| `--window-minutes` | `5` | Zaman penceresi boyutu (dakika) |
| `--max-tokens-per-chunk` | `4000` | Alt-chunk başına token bütçesi |
| `--mock` | kapalı | LLM çağrılarını mock modda çalıştır |
| `--ask` | (yok) | Rapor sonrası sorulacak doğal dil sorusu |
| `--output` | `output/report.json` | Rapor çıktısının yazılacağı dosya |

## Çıktı

Çalıştırma sonunda `output/report.json` içinde genel analiz raporu (özet, anomaliler, hata
kategorileri, güvenlik sinyalleri) ve konsolda maliyet özeti (token sayıları, dolar tutarı) üretilir.

## Proje Yapısı

```text
log_analyzer/
├── siem/
│   ├── __init__.py
│   ├── syslog_parser.py    # Ham log satırlarını LogRecord nesnelerine ayrıştırır
│   ├── templater.py        # Logları şablonlayıp gruplar
│   ├── chunker.py          # Zaman penceresi + token bütçesi bazlı bölme
│   ├── cost_tracker.py     # LLM çağrı maliyeti takibi
│   ├── prompts.py          # Tüm LLM system promptları
│   ├── llm_client.py       # DeepSeek API istemcisi
│   ├── analyzer.py         # Map adımı: pencere bazlı LLM analizi
│   ├── aggregator.py       # Reduce adımı: kademeli özet birleştirme
│   ├── qa.py               # RAG-benzeri doğal dil soru-cevap
│   └── main.py             # CLI giriş noktası
├── scripts/
│   └── download_sample.py  # Hugging Face'ten örnek veri indirme aracı
├── prompts/
│   ├── 01_chunk_analysis_system_prompt.txt
│   ├── 02_reduce_system_prompt.txt
│   ├── 03_qa_system_prompt.txt
│   └── 04_query_understanding_system_prompt.txt
├── docs/
├── sample_data/
├── requirements.txt
├── .gitignore
└── README.md
```

## Dokümantasyon

- **Mimari ve tasarım kararları:** [docs/01_architecture.md](docs/01_architecture.md)
- **Örnek analiz sonuçları:** [docs/02_sample_results.md](docs/02_sample_results.md)
- **Performans ve API maliyeti ölçümleri:** [docs/03_performance_and_cost.md](docs/03_performance_and_cost.md)
- **Karşılaşılan problemler ve geliştirme önerileri:** [docs/04_problems_and_improvements.md](docs/04_problems_and_improvements.md)