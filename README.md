# SIEM-LLM-Analyzer

LLM (DeepSeek) kullanılarak büyük hacimli syslog verilerinin analiz edildiği bir prototip sistem. Veri setinin tamamını modele göndermek yerine ön işleme → şablonlama/gruplama → zaman penceresine bölme → LLM ile analiz (map) → sonuçları birleştirme (reduce) adımlarından oluşan bir pipeline kullanır.

Veri kaynağı: [vulcansiem/synthetic-syslog-1B](https://huggingface.co/datasets/vulcansiem/synthetic-syslog-1B)

## Kurulum

```
git clone <repo-url>
cd log_analyzer
python -m venv venv
venv\Scripts\activate   # Windows için (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt

```

## Proje Yapısı

```
log_analyzer/              
├── scripts/
│   └── download_sample.py     
├── siem/                      
│   ├── __init__.py
│   ├── syslog_parser.py
│   └── templater.py
├── .gitignore
├── README.md
└── requirements.txt

```