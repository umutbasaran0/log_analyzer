# Sistem Mimarisi

## Problem

Sentetik syslog veri seti doğrudan LLM'e gönderilemez — hem token maliyeti hem de
context window sınırı buna izin vermez. Bu yüzden veri, LLM'e ulaşmadan önce çok aşamalı bir
pipeline'dan geçirilerek küçültülür.

## Yaklaşım

- **Şablonlama:** Tekrarlayan loglar (IP/sayı maskelenip) gruplanır, LLM'e her satır değil, "bu
  şablon N kez tekrarlandı" özeti gider.
- **Map-Reduce:** Veri zaman pencerelerine bölünüp ayrı ayrı analiz edilir (map), sonuçlar kademeli
  olarak (20'şerli gruplar halinde) tek bir genel rapora indirgenir (reduce).
- **RAG:** Kullanıcı sorusu önce filtrelere çevrilir, ilgili kayıtlar lokal olarak süzülür, sadece bu
  küçük alt küme LLM'e gönderilir — tüm veri değil.
- **Bellek verimliliği:** Dosya tamamı belleğe alınmadan, generator (`yield`) ile satır satır okunur;
  böylece veri boyutu ne olursa olsun (teorik olarak) sabit ve düşük bellek kullanımı korunur — bu,
  yalnızca LLM tarafındaki değil, dosya okuma tarafındaki ölçeklenebilirliği de sağlar.
- **Sınıflandırma, ilişkilendirme, anomali tespiti ve önceliklendirme:** Her log kaydı uygulama,
  kaynak (host/IP), önem derecesi (severity) ve mesaj içeriğine (şablon) göre sınıflandırılır; LLM
  ayrıca birbiriyle ilişkili kayıt gruplarını (`clusters`) belirler, şüpheli/anormal kayıtları tespit
  eder ve bulguları önem derecesine (CRITICAL → HIGH → MEDIUM → LOW) göre sıralı olarak raporlar.

## Pipeline Akışı

`Ham log → syslog_parser (LogRecord'a ayrıştır) → chunker (zaman penceresi) → templater (şablonla+grupla)
→ chunker (token bütçesine böl) → analyzer (map, LLM analiz) → aggregator (reduce, genel rapor) → main.py (CLI)`

Soru-cevap: `Soru → qa.py (filtrelere çevir → ilgili kayıtları süz → LLM'e sor) → Cevap`

## Önemli Tasarım Kararları

- Toplam kayıt sayısı, zaman aralığı gibi **kesin** veriler LLM'e tahmin ettirilmez, kod tarafından
  hesaplanıp rapora eklenir (halüsinasyon riskini azaltmak için).
- Kullanıcı adları bilinçli olarak maskelenmez — güvenlik analizinde "kim" bilgisi değerlidir (bu,
  sıkıştırma oranını bir miktar düşüren ama bilinçli bir tercih; detay: `04_problems_and_improvements.md`).
- Hem mock (API'siz, ücretsiz test) hem gerçek DeepSeek API modu destekleniyor; API key `.env`
  dosyasından otomatik yükleniyor.
- Tüm LLM çağrılarının maliyeti tek bir merkezi `CostTracker` ile takip ediliyor.
- Analiz sonucu hem insan tarafından okunabilir bir özet (`chunk_summary`, `overall_summary`) hem de
  yapılandırılmış JSON şeması olarak üretilir — ikisi de aynı LLM çağrısının çıktısı.

## Kullanılan Teknolojiler

Python 3.11, DeepSeek Flash v4 (`deepseek-v4-flash`, OpenAI-uyumlu API), `requests`, `python-dotenv`.
Veri seti: `vulcansiem/synthetic-syslog-1B` (Hugging Face, MIT lisanslı, ~75M satır).