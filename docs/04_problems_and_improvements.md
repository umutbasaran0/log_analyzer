# Karşılaşılan Problemler ve Mimari Kararlar

## Parser (Ayrıştırıcı) Kararları

- **Risk:** Gerçek dünya log verilerinde format dışı satırların ayrıştırma sırasında exception
  fırlatıp pipeline'ı durdurması.
  **Çözüm:** `parse_line` fonksiyonu defensive yazıldı — regex eşleşmezse `None` döner, `parse_file`
  bu satırı atlayıp sayaca ekler, işleme devam eder.

- **Risk:** 1B satırlık veri setinin tamamının belleğe alınmaya çalışılması durumunda bellek
  taşması.
  **Çözüm:** Dosya `readlines()` ile değil, `yield` tabanlı generator ile satır satır okunuyor;
  bellekte aynı anda yalnızca tek bir satır tutuluyor.

## Templater (Şablonlayıcı) Kararları

- **Tasarım kararı (regex sınırları):** `IP_RE` ve `NUM_RE` desenlerine `\b` (kelime sınırı)
  eklendi, böylece örneğin bir versiyon numarasının (`v1.2.3.4` gibi) yanlışlıkla IP olarak
  maskelenmesi engellendi.
- **Tasarım kararı (sıralama):** `templatize` içinde önce IP'ler, sonra sayılar maskeleniyor. Sıra
  tersine çevrilirse IP'nin oktetleri ayrı ayrı `<NUM>`'a dönüşür ve template kırılır (ör.
  `<NUM>.<NUM>.<NUM>.<NUM>` yerine `<IP>` beklenir).
- **Tasarım kararı (kullanıcı adları maskelenmiyor):** `alice`, `admin` gibi kullanıcı adları
  template'ten çıkarılmadı. Bunun sonucu, aynı olayın farklı kullanıcılarla gerçekleşmesi
  durumunda (ör. "Failed password for alice" ve "Failed password for admin") bu iki kaydın
  **farklı gruplara** düşmesidir. Bu bilinçli bir tercih: "kim" bilgisi güvenlik analizinde
  değerli. Ama bunun bir maliyeti var — sıkıştırma oranı, kullanıcı adı da maskelenseydi
  olacağından daha düşük çıkıyor. Bu, gerçek ölçümlerle de doğrulandı: 500 satırda 2.94x, 50.000
  satırda 3.65x — veri büyüdükçe oran iyileşiyor (beklenen yönde), ama kullanıcı adı maskelemesi
  olmadığı için tavan daha düşük kalıyor.
  **Alternatif geliştirme:** kullanıcı adını ayrı bir `<USER>` yer tutucusuyla maskeleyip, gerçek
  kullanıcı adlarını grup içinde ayrı bir `distinct_users` seti olarak tutmak (host/IP'de yapıldığı
  gibi) — böylece hem sıkıştırma iyileşir hem de "kaç farklı kullanıcı etkilendi" bilgisi
  kaybolmaz.

## Chunker Kararları

- **Sorun:** Loglardaki zaman damgalarının standart string formatında gelmesi ve Python'un bazı
  sürümlerinde ISO formatındaki Zulu Time (`Z`) harfinin `fromisoformat` tarafından hata
  fırlatması.
  **Çözüm:** `_parse_ts` fonksiyonunda `Z` harfi `+00:00` offset'i ile değiştirilip metinler
  karşılaştırılabilir `datetime` objelerine dönüştürüldü.
- **Sorun:** Yoğun trafik olan anlarda tek bir zaman penceresinin LLM token sınırını aşma riski.
  **Çözüm:** `split_by_token_budget` algoritmasıyla, her alt-parçanın toplam token maliyeti
  (`4 karakter ≈ 1 token` kaba tahmini) hesaplanarak veriler güvenli boyutlardaki alt-paketlere
  bölündü.

## Cost Tracker Kararları

- **Sorun:** API'den dönen JSON yanıtlarında, ağ/sunucu kaynaklı bir hatadan dolayı
  `prompt_tokens` gibi anahtarların eksik gelmesi durumunda `KeyError` ile çökme riski.
  **Çözüm:** `.get(key, 0)` kullanılarak, eksik anahtarlarda maliyetin `0` varsayılıp sistemin
  güvenle çalışmaya devam etmesi sağlandı.
- **Sorun:** Çok sayıda API çağrısından dönen küsuratlı maliyetlerin toplanmasında kayan nokta
  (floating-point) hassasiyet sapmaları.
  **Çözüm:** `setdefault` ile stage bazlı biriktirme yapıldıktan sonra, her toplam `round(cost, 6)`
  ile temizlenip sunuma hazır hale getirildi.

## Prompt Mühendisliği ve Halüsinasyon Önlemleri

- **Sorun:** LLM'in güvenlik loglarında var olmayan IP/host uydurması ve her pencerede zorla
  anomali üretme eğilimi.
  **Çözüm:** Prompt seviyesinde net kurallar (`"Veride olmayan bir şeyi UYDURMA"`, `"Sadece
  gerçekten dikkat çekici bir şey varsa anomalies doldur"`) ile gürültü ve yanlış alarmlar minimuma
  indirildi.
- **Sorun:** RAG tabanlı soru-cevapta, yeterli veri bulunamadığında modelin yanıltıcı/uydurma cevap
  verme riski.
  **Çözüm:** `QA_SYSTEM_PROMPT`'a *"Eğer cevap için yeterli veri yoksa bunu açıkça belirt"* kuralı
  eklendi.

## LLM İstemcisi Mimarisi Kararları

- **Sorun:** Geliştirme/test sırasında her API çağrısının hem maliyet yaratması hem de internet
  bağımlılığı nedeniyle testleri yavaşlatması.
  **Çözüm:** `api_key is None` kontrolüyle otomatik mod seçimi kuruldu; anahtar yoksa tamamen
  çevrimdışı, kural tabanlı Mock altyapısı devreye giriyor — maliyetsiz, anında uçtan uca test
  imkanı sağlıyor.
- **Sorun:** Mock modda gerçek `usage` verisi gelmediği için `CostTracker`'ın hata verme ihtimali.
  **Çözüm:** Mock cevaplarda karakter uzunluğuna dayalı tahmini token hesabı (`len(user_content)
  // 4`) kullanılarak maliyet takibi mock modda da kesintisiz çalıştırıldı.
- **Sorun:** Gerçek API çağrılarında ağ kesintisi (`ChunkedEncodingError`, `ReadTimeout`) yaşanması
  — 5.000 satırlık ilk gerçek test bu yüzden tamamlanamadan çöktü.
  **Çözüm:** `chat_json`'a `try/except requests.exceptions.RequestException` ile retry +
  exponential backoff (5sn → 60sn tavan) eklendi. Sonraki deneme (5.000 satır, gerçek API) hiç
  hataya uğramadan tamamlandı.

## Analyzer (Map) Aşaması Kararları

- **Sorun:** Yoğun trafikli pencerelerin LLM'in tek seferde analiz edemeyeceği kadar büyük olması.
  **Çözüm:** `split_by_token_budget` ile alt-parçalara bölünüp her biri ayrı LLM çağrısına
  gönderildi.
- **Sorun:** LLM'den dönen çoklu JSON yanıtları listelere eklenirken iç içe (nested) liste oluşması
  riski.
  **Çözüm:** `.append()` yerine `.extend()` kullanılarak düz (flat) listeler korundu.
- **Sorun:** Severity sözlükleri toplanırken eksik anahtarların `KeyError` vermesi.
  **Çözüm:** `.get(k, 0)` ile güvenli toplama yapıldı.
- **Sorun:** `datetime` nesnelerinin doğrudan JSON'a serileştirilememesi.
  **Çözüm:** `window_start`/`window_end` `str()` ile metne çevrildi.

## Aggregator (Reduce) Aşaması Kararları

- **Sorun:** Binlerce chunk oluştuğunda hepsinin tek seferde LLM'e gönderilmesinin context limitini
  aşması.
  **Çözüm:** `build_final_report` içinde `while` döngüsüyle hiyerarşik (kademeli) özetleme
  kuruldu — 20'şerli gruplar halinde, analiz sayısı 20'nin altına inene kadar tekrar tekrar
  özetleniyor.
- **Sorun:** Hiyerarşik reduce'ta, bir katmanın çıktı şeması
  (`REDUCE_SYSTEM_PROMPT`'un ürettiği `severity_breakdown_total`, `top_error_types` gibi alanlar)
  bir sonraki katmanın **girdi olarak beklediği** şemayla (`chunk_analysis`'in `severity_breakdown`,
  `top_categories` alanları) uyuşmuyordu. Bu, mock modda 20+ pencereli (ör. 50.000 satır, 134
  pencere) çalıştırmalarda tüm istatistiklerin (`0` kayıt, `[]` anomali) sıfırlanmasına yol
  açıyordu — `docs/evidence/report_50000_mock.json`'da gözlemlendi (düzeltme öncesi hali,
  `total_chunks_analyzed: 7`, `overall_summary: "Toplam 0 kayit islendi"`).
  **Çözüm:** `_mock_reduce`, girdinin hem `chunk_analysis` şemasından (`severity_breakdown`,
  `anomalies`, `top_categories`) hem de önceki bir reduce çıktısından (`severity_breakdown_total`,
  `anomalies_ranked`, `top_error_types`) gelebileceğini varsayıp, `or` zinciriyle her iki alan
  ismini de okuyacak şekilde güncellendi. Düzeltme sonrası `severity_breakdown_total` ve
  `overall_summary` artık gerçek toplamları (50.000 kayıt) doğru yansıtıyor.
  **Bilinen kalan tutarsızlık:** `total_chunks_analyzed` alanı, hiyerarşik yapının **son
  katmanındaki** batch sayısını (7) gösteriyor, gerçek pencere sayısını (134) değil — bu bilgi
  aynı raporun `total_windows` alanında **doğru** olarak zaten mevcut (kod tarafından, LLM'den
  bağımsız hesaplanıyor). İleride `total_chunks_analyzed`'in ya kaldırılması ya da `total_windows`
  ile birleştirilmesi önerilir.
  **Not:** Bu sorun yalnızca mock modu etkiliyordu — gerçek LLM, JSON'u bağlamsal olarak
  yorumladığı için (katı dict-key araması yapmadığı için) gerçek API çıktıları hiç etkilenmedi.
- **Sorun:** Tek pencereli, düşük yoğunluklu dosyalarda veriyi tekrar LLM'e göndermenin gereksiz
  maliyet/zaman kaybı yaratması.
  **Çözüm:** `if len(analyses) > 1` koşuluyla, tek analiz kalmışsa reduce çağrısı atlanıp doğrudan
  mevcut analiz nihai rapor olarak kullanılıyor (%50'ye varan tasarruf, gözlemlenen senaryo: 150
  satırlık tek pencereli test).
- **Sorun:** Boş log dosyalarında `analyses[0]`'a erişmenin `IndexError` fırlatması.
  **Çözüm:** `analyses[0] if analyses else {}` ile boş veri setlerinde güvenli, boş bir rapor
  dönülüyor.

## QA (Soru-Cevap) Aşaması Kararları

- **Sorun:** Kullanıcı özel bir soru sorduğunda tüm log dosyasının LLM'e gönderilmesinin token
  sınırını aşması ve aşırı maliyetli olması.
  **Çözüm:** RAG mimarisi kuruldu — soru önce filtrelere çevrildi, veriler Python'da lokal olarak
  filtrelendi, sadece ilgili alt küme LLM'e gönderildi.
- **Sorun:** Liste üzerinde arama yapmanın `O(n)` maliyeti.
  **Çözüm:** Filtreleme aşamasında `set()` kullanılarak arama `O(1)`'e indirildi; çoklu alan
  taramasında "haystack" + `any()` kalıbı kullanıldı.
- **Sorun:** Hiçbir kayıt eşleşmediğinde LLM'in halüsinasyon görme riski.
  **Çözüm:** `fallback_general_report` mekanizmasıyla, eşleşme yoksa genel özet bağlama yedek
  olarak eklenip modelin elleri boş kalmıyor.
- **Technical debt:** `_parse_ts` fonksiyonu hem `chunker.py` hem `qa.py`'de ayrı ayrı tanımlı.
  Ortak bir `utils.py` modülüne taşınabilir.

## CLI (main.py) Kararları

- **Sorun:** `analyzer`, `aggregator`, `qa` modüllerinin kendi başlarına API çağrısı yapması
  durumunda toplam bütçenin merkezi takip edilememesi.
  **Çözüm:** Tek bir `CostTracker` ve `LLMClient` nesnesi `main.py`'de oluşturulup tüm modüllere
  parametre olarak paslandı (dependency injection) — uçtan uca tek, kesin bir maliyet tablosu elde
  edildi.
- **Sorun:** Boş/yanlış dosya yolu verildiğinde pipeline'ın gereksiz yere çalışıp hata fırlatması.
  **Çözüm:** `if not records: return` ile erken çıkış — API hiç çağrılmadan zarifçe durur.

## Veri İndirme (download_sample.py) — Dayanıklılık Kararları

50.000+ satırlık veri indirirken karşılaşılan sorunlar, üç aşamada çözülerek tam dayanıklı bir
yapı kuruldu:

- **Faz 1 — Veri Kaybı:** İlk yapıda veriler bellekte biriktirilip en son diske yazılıyordu; bir
  hatada script çöküyor, o ana kadar indirilen tüm veri (ör. 20.000+ satır) kayboluyordu.
  **Çözüm:** Her 100 satırlık batch anında diske yazılıp `f.flush()` ile kalıcı hale getirildi.
- **Faz 2 — API Limitleri:** `429 Too Many Requests` ve `5xx` hatalarında betik duruyordu.
  **Çözüm:** HTTP hata kodları yakalanıp retry + exponential backoff eklendi.
- **Faz 3 — Ağ Kesintileri ve Baştan Başlama:** HTTP cevabı hiç gelmeden yaşanan bağlantı kopmaları
  (`ReadTimeout`) HTTP durum kodu oluşmadığı için yakalanamıyordu, betik yine çöküyor, tekrar
  çalıştırıldığında da baştan başlıyordu.
  **Çözüm:** `requests.exceptions.RequestException` ile ağ seviyesi hatalar da retry'a dahil
  edildi; dosyadaki mevcut satır sayısı sayılıp `offset` buna göre ayarlanarak "kaldığı yerden
  devam etme" (resume) yeteneği kazandırıldı — script artık asla baştan başlamıyor.

## Mock vs Gerçek API — Anomali Tespitinde Kalite Farkı

Mock modda 500 satır için 34, 5.000 satır için 279 "anomali" tespit edilirken, gerçek DeepSeek
API'de aynı verilerde sırasıyla 6 ve 7 anomali tespit edildi. Bu beklenen bir
davranış: mock, basit bir kural (`severity == CRITICAL` ise anomali say) kullanırken, gerçek LLM
prompttaki "sıradan trafiği anomaly olarak işaretleme" talimatını uygulayarak rutin olayları (ör.
`sshd started` CRITICAL etiketlenmiş olsa bile) ayrı, daha az öncelikli bir bulgu (severity
etiketleme tutarsızlığı) olarak sınıflandırıyor, gerçek güvenlik sinyallerine odaklanıyor. Bu,
LLM'in kural tabanlı bir sisteme göre sağladığı bağlamsal muhakeme avantajının somut bir kanıtıdır.

## Gelecek Geliştirme Fikirleri

- **Kullanıcı adı maskeleme (opsiyonel):** `<USER>` yer tutucusu + `distinct_users` seti — sıkıştırma
  oranını artırabilir, "kim" bilgisini kaybetmeden.
- **Retrieval'ın tavana takılma sorununun incelenmesi:** `query_understanding` filtrelerinin
  gerçekten daraltıp daraltmadığının doğrulanması.
- **`_parse_ts` kod tekrarının giderilmesi:** ortak `utils.py` modülüne taşınması.
- **İngilizce Prompt A/B Testi:** mevcut Türkçe promptların İngilizce versiyonlarıyla token
  maliyeti ve şema tutarlılığı karşılaştırması.
- **Paralel LLM çağrıları:** `analyzer.py`'deki sıralı `for sub in sub_chunks` döngüsünün
  `asyncio` ile paralelleştirilmesi, büyük veri setlerinde toplam süreyi kısaltabilir.
- **50.000+ satırlık veride gerçek API testi:** bu ölçekte tam çalıştırma yapılmadı (tahmini ~10
  saat), 500/5.000 satırlık gerçek ölçümlere dayanan ekstrapolasyon kullanıldı (bkz.
  `03_performance_and_cost.md`).