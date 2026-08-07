# Performans ve Maliyet Ölçümleri

Test ortamı: DeepSeek Flash v4 (`deepseek-v4-flash`), `window_minutes=5`, `max_tokens_per_chunk=4000`
(aksi belirtilmedikçe varsayılan ayarlar).

## 1. Kademeli Ölçüm: 500 / 5.000 / 50.000 Satır

### Mock Mod (LLM çağrısı yapılmadan, sadece pipeline mekaniği)

| Kayıt Sayısı | Süre (sn) | Pencere Sayısı | LLM Çağrı Sayısı | Sıkıştırma Oranı |
|---|---|---|---|---|
| 500     | 0.26 | 2   | 8   | 2.94 |
| 5.000   | 0.25 | 14  | 56  | 3.57 |
| 50.000  | 0.78 | 134 | 543 | 3.65 |

### Gerçek API (DeepSeek Flash v4)

| Kayıt Sayısı | Süre (sn) | LLM Çağrı Sayısı | Toplam Token | Maliyet (USD) |
|---|---|---|---|---|
| 500     | 515.90   | 8  | 106.756 | $0.023351 |
| 5.000   | 3693.97  | 56 | 824.115 | $0.177968 |
| 50.000  | ~35.816* (~9sa 57dk) | 543* | — | ~$1.73* |

\* 50.000 satır gerçek API'de tam çalıştırılmadı (~10 saat sürecekti, tek oturumda pratik değil).
Aşağıdaki ekstrapolasyon, 500 ve 5.000 satırlık gerçek ölçümlere dayanmaktadır.

**Ekstrapolasyon yöntemi:**
- Ortalama çağrı süresi (5.000 satır gerçek testinden): `3693.97 / 56 = 65.96 sn/çağrı`
- Ortalama çağrı maliyeti (aynı testten): `0.177968 / 56 = $0.003178/çağrı`
- 50.000 satır için gereken çağrı sayısı (543), mock testinden biliniyor — chunking mekanizması
  deterministik olduğu için bu sayı LLM modundan (mock/gerçek) bağımsızdır.
- `543 × 65.96 sn ≈ 35.816 sn` , `543 × $0.003178 ≈ $1.73`

### Gözlemler

- Süre ve maliyet, veri boyutuyla kabaca doğrusal artıyor (LLM çağrı sayısı ana belirleyici).
- Sıkıştırma oranı veri büyüdükçe iyileşiyor (2.94 → 3.65) — beklenen yönde, daha büyük veride
  tekrarlayan pattern'lerin görülme sıklığı artıyor. Oranın çok daha yüksek çıkmamasının sebebi,
  `templater.py`'nin kullanıcı adlarını bilinçli olarak maskelememesi (detay:
  `04_problems_and_improvements.md`).
- Mock ile gerçek API arasındaki fark (500 satırda 0.26 sn'ye karşı 515.9 sn, ~2000x) geliştirme
  sırasında mock modun neden vazgeçilmez olduğunu somut olarak gösteriyor.

## 2. Erken Doğrulama Testleri (Prototip Aşaması)

Prototipin ilk uçtan uca çalıştırmalarında, küçük veri dilimleriyle yapılan ve sistemin temel
davranışını doğrulayan testler:

**100 satır (map aşaması, tek başına):**
3 alt-parçaya bölünmüş, `15.454` prompt + `15.908` completion token, toplam **$0.006618**.
Model, akıcı ve anomali tespitleri içeren chunk özetleri üretmeyi 1 sentin altında bir maliyetle
başarmıştır.

**150 satır (map-reduce bütünleşmesi, tek pencereye sığan senaryo):**
Kayıtlar 3 alt-parçaya ayrılmış, toplam maliyet **~$0.002**. Veri tek bir zaman penceresine
sığdığı için `aggregator.py`'nin "akıllı bypass" mekanizması devreye
girmiş, gereksiz bir reduce çağrısı yapılmadan doğrudan map çıktısı nihai rapor olarak kullanılmış
— bu senaryoda maliyet %50 tasarruf etmiştir.

**300 satır (RAG / soru-cevap):**
"En sık karşılaşılan hata türleri nelerdir?" sorusu, query understanding + retrieval + QA
adımlarından geçirilmiş, toplam maliyet **$0.003138**. Bu, RAG mimarisinin değerini somut olarak
gösteriyor: filtreleme olmasaydı tüm veri LLM'e gönderilir, hem context limiti aşılır hem maliyet
katlanarak artardı.

## 3. RAG (Soru-Cevap) Maliyet Detayı

Bölüm 1'deki kademeli tabloya ek olarak, `qa.py`'nin bağımsız maliyeti önemli — çünkü bir kere
analiz raporu üretildikten sonra, kullanıcı istediği kadar soru sorabilir, her soru **tam analizin
değil, sadece retrieval+QA'nın maliyetini** taşır (~$0.0058/soru, bkz.
`02_sample_results.md`'deki 6 örnek soru). Bu, tekrarlayan sorgulamalarda pipeline'ın en
maliyet-etkin kısmı.