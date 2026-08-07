# Örnek Analiz Sonuçları

## 1. Genel Analiz Raporu

Aşağıdaki sonuçlar, `sample_data/sample_5000.txt` (5.000 satır, gerçek DeepSeek API) üzerinde
şu komutla üretilmiştir:

​```powershell
python -m siem.main --input sample_data\sample_5000.txt --window-minutes 5 --output output\report_5000_real.json
​```

### Genel Özet

> Across the 14 analyzed chunks, the logs reveal sustained network and authentication activity
> over an approximately one-hour window. There were over 1,100 successful SSH logins and more
> than 200 failed password attempts, with root, admin, and service accounts heavily targeted.
> Kernel firewall events (ACCEPT/DROP/REJECT) dominated network logs, while service start
> messages and HTTP requests to admin/login endpoints appeared frequently. A notable systemic
> issue is the inconsistent assignment of severity levels, with routine events such as successful
> logins and service starts marked as CRITICAL or ERROR, which may indicate misconfiguration or
> deliberate obfuscation. Overall, the pattern suggests possible SSH brute-force attempts, 
> unauthorized privileged access, and web application probing, warranting immediate investigation.

### Öne Çıkan Hata Kategorileri

| Kategori | Toplam Sayı | Not |
|---|---|---|
| firewall_reject | 485 | Yüksek frekans tarama/politika ihlaline işaret edebilir |
| firewall_drop | 468 | Çok sayıda farklı kaynak IP'den, tüm host'larda görüldü |
| ssh_auth_failure | 229 | Muhtemel brute-force |
| http_5xx_error | 33 | login/admin endpoint'lerinde, olası zafiyet taraması |

### En Kritik Anomaliler

1. **CRITICAL** — Çok sayıda başarısız denemeden sonra dışarıdan bir IP'den root hesabıyla
   başarılı SSH girişi. *Gerekçe: root, en yetkili hesap; başarısız denemelerin ardından gelen
   başarı, kimlik bilgisi ele geçirme ihtimalini gösteriyor.*
2. **HIGH** — root, admin, service, alice, bob hesaplarına karşı, tüm 14 pencerede dağıtık
   SSH brute-force paterni.
3. **HIGH** — Birden fazla kaynak IP'den, tutarsız CRITICAL/ERROR seviyeleriyle işaretlenmiş,
   yetkili hesap girişleri.

### Sıkıştırma İstatistikleri

- Ham kayıt sayısı: 5.000
- Benzersiz şablon sayısı (14 pencere toplamı): 1.400
- Ortalama sıkıştırma oranı: **3.57x**

Tam JSON çıktısı için bkz. [docs/evidence/report_5000_real.json](./evidence/report_5000_real.json).

## 2. Doğal Dil Soru-Cevap Örnekleri

6 örnek soru, aynı 5.000 satırlık veri seti üzerinde, RAG mimarisi (query
understanding → retrieval → QA) üzerinden test edilmiştir. 6 sorunun **toplam** maliyeti
**$0.034571** (~ortalama $0.0058/soru) — bu, tam analiz raporunun (~$0.18) çok altında, çünkü RAG
sadece ilgili alt kümeyi LLM'e gönderir, tüm veriyi değil.

**Gözlem:** 6 sorunun hepsinde retrieval sonucu tam `max_records=300` tavanına ulaştı. Bu, kodun
context taşmasını önleme mekanizmasının (bilinçli olarak konan üst sınır) beklendiği gibi devreye
girdiğini gösteriyor — bir hata değil. Ancak şu an sistem, tavana **kaç kaydın gerçekten** eşleştiğini
(300'ün üzerinde ne kadar fazla olduğunu) loglamıyor; bu bilgi eklenirse, filtrelerin ne kadar
daraltıcı olduğu daha net ölçülebilir (ileride geliştirilebilecek bir gözlemlenebilirlik eksiği).

### Soru 1: En sık karşılaşılan hata türleri nelerdir?

> Verilen log örneklerine göre en sık karşılaşılan hata türleri şunlardır: (1) Kernel kaynaklı ağ
> bağlantı engelleme mesajları ('Connection DROP' ve 'Connection REJECT'), (2) SSH kimlik
> doğrulama hataları ('Failed password' mesajları), (3) HTTP hata kodları (nginx 500 Internal
> Server Error ve 404 Not Found). Bu değerlendirme yalnızca sağlanan örnek kayıtlara
> dayanmaktadır; 300 kaydın tamamı incelenmemiştir.

**Kanıtlar:**
- Çok sayıda kernel mesajı: 'Connection DROP 10.147.175.85 -> 10.206.133.182' ve 'Connection
  REJECT 10.180.18.232 -> 10.130.174.115' gibi engelleme kayıtları.
- sshd hataları tekrarlıyor: 'Failed password for service from 215.150.6.105', 'Failed password
  for bob from 157.147.182.10'.
- nginx hata kodları gözlemlendi: 'POST / 500', 'GET /login 404', 'POST /admin 500'.
- Bazı CRITICAL seviyeli kayıtlar ('cron started', 'nginx started') hata içermiyor; bu yüzden
  hata türü sayılmadı.

### Soru 2: Son bir saat içerisinde hangi kritik olaylar gerçekleşti?

> İncelenen kayıtlara göre son bir saat içinde (örnek zaman aralığı 07:09-07:31 UTC) kritik
> olaylar şunlardır: çok sayıda SSH başarısız giriş denemesi (admin, root, alice, bob, service
> hesapları için), çok sayıda ağ bağlantısı DROP/REJECT olayı, HTTP 500 ve 404 yanıtları
> (özellikle /admin ve /login yollarında) ve servis başlangıç mesajları (kernel, nginx, sshd,
> cron, sudo). Tüm kayıtlar CRITICAL etiketli olsa da asıl kritik görünenler başarısız kimlik
> doğrulama girişimleri ve ağ trafiği engelleme/reddetme olaylarıdır.

**Kanıtlar:**
- Failed password for admin from 10.108.163.111 (host8)
- Failed password for root from 12.80.121.30 (host3)
- Connection DROP 10.156.10.90 -> 10.166.139.155 (host9)
- Connection REJECT 4.211.187.85 -> 10.133.33.190 (host1)
- POST /admin 500 (host6)

### Soru 3: Birbiriyle ilişkili olabilecek log kayıtları hangileridir?

> Verilen loglarda birbiriyle ilişkili olabilecek birkaç grup öne çıkıyor. Öncelikle SSH (sshd)
> loglarında aynı kullanıcı hedefli çok sayıda başarısız giriş denemesi var; özellikle 'root',
> 'alice' ve 'admin' kullanıcıları için farklı IP'lerden gelen 'Failed password' kayıtları bir
> brute-force/deneme saldırısına işaret edebilir. İkinci olarak nginx loglarında aynı path'e
> (çoğunlukla 'POST /admin' veya 'POST /') dönen tekrarlayan 500 hataları, bir uygulama veya
> sunucu kaynaklı hatayla ilişkili olabilir. Üçüncü olarak kernel loglarında aynı zaman
> aralığında çok sayıda DROP ve REJECT aksiyonu var; bu, güvenlik duvarı veya ağ politikası
> tarafından engellenen bağlantılarla ilgili bir örüntü oluşturuyor. Ayrıca aynı uygulamaların
> (cron, sshd, kernel, nginx) birçok hostta kısa süre içinde 'started' mesajı vermesi, toplu bir
> servis başlatma/yeniden başlatma durumunu gösterebilir. Son olarak 'Accepted password'
> loglarında aynı kullanıcıların farklı host ve IP'lerden ardışık giriş yapması, dağıtık erişim
> veya otomasyon kaynaklı bir ilişkiye işaret edebilir.

**Kanıtlar:**
- 07:03-07:07 arasında sshd'de 'Failed password' kayıtları: root için 07:03:40 (10.242.36.89),
  07:03:48 (119.180.107.8), 07:05:05 (134.104.124.86), 07:06:30 (58.57.132.238), 07:06:32
  (10.176.107.18); alice için 07:04:22, 07:06:24, 07:06:39, 07:06:41 gibi çok sayıda örnek var.
- nginx loglarında tekrarlayan hatalar: 07:03:08'de host4 ve host6'da 'POST / 500', 07:03:15'te
  host4'te 'POST / 500', 07:03:30'da host4'te 'POST /admin 500', 07:04:02'de host1'de 'POST
  /admin 500', 07:06:02'de host7'de 'POST /admin 500', 07:06:12'de host4'te 'POST /admin 500'.
- Kernel loglarında DROP/REJECT yoğunluğu: 07:03:02, 07:03:03, 07:03:04, 07:03:10, 07:03:11,
  07:03:13, 07:03:23, 07:03:31, 07:04:11, 07:04:14, 07:04:19, 07:05:06, 07:05:07, 07:05:21 gibi
  birçok zaman damgasında DROP veya REJECT eylemi var.
- Birden çok hostta 'started' mesajları: 07:03:02'de cron, 07:03:07'de kernel, 07:03:21'de
  kernel, 07:03:25'te sudo, 07:03:28'de cron, 07:03:35'te nginx, 07:03:46'da nginx, 07:03:54'te
  sshd, 07:04:11'de kernel, 07:04:12'de sshd, 07:04:16'da nginx, 07:04:29'da kernel, 07:05:02'de
  kernel, 07:05:09'da kernel, 07:06:04'te cron vb. Aynı zaman penceresinde yoğun başlatma kaydı
  var.
- Aynı kullanıcı için 'Accepted password' logları: alice 07:03:06 (host9), 07:03:22 (host2),
  07:03:24 (host6), 07:03:29 (host1), 07:03:35 (host9), 07:03:57 (host7), 07:03:58 (host3),
  07:04:13 (host7), 07:04:51 (host3), 07:05:45 (host7) gibi farklı host ve IP'lerden görülüyor.

### Soru 4: Belirli bir cihaz veya servis üzerinde tekrarlayan bir problem var mı?

> Evet, tekrarlayan bir sorun görülüyor: Özellikle nginx servisinde çok sayıda HTTP 500 hatası
> var. Bu hatalar farklı ana bilgisayarlarda (host3, host4, host6, host7, host9, host10) ve
> farklı yollar üzerinde tekrarlıyor. Ayrıca cron, kernel, sshd, nginx ve sudo gibi servislerin
> çok sık "started" mesajıyla yeniden başlatıldığı dikkat çekiyor. Ancak bu yeniden başlatmalar
> ve hatalar belirli bir cihaza özgü değil; genel bir eğilim söz konusu. Tek bir cihazda
> yoğunlaşan bir sorun tespit edilmedi, ancak nginx servisi özelinde tekrarlayan bir hata
> paterni mevcut.

**Kanıtlar:**
- Örnek loglarda nginx uygulamasında toplam 12 adet HTTP 500 yanıtı tespit edildi (örn. host4:
  POST / 500, host7: POST /admin 500, host9: POST / 500).
- Birden fazla host'ta (host5, host2, host10, host7, host8, host9) cron, kernel, sshd, nginx ve
  sudo servislerinin sık sık "started" logu görülüyor; bu, tekrarlayan yeniden başlatmalara
  işaret ediyor.
- nginx 500 hataları tek bir kaynak IP'den değil, farklı iç ve dış IP'lerden geliyor; bu da
  yaygın bir sunucu tarafı sorununa işaret ediyor.
- sshd için başarısız parola denemeleri farklı kullanıcılar ve IP adresleri üzerinden dağılmış
  durumda; belirli bir cihaz veya kaynak öne çıkmıyor.
- Kernel DROP/REJECT olayları çok sayıda farklı kaynak IP'den geliyor; tekrarlayan bir kaynak
  yok.

### Soru 5: Normal davranıştan farklı görünen kayıtlar hangileridir?

> Bu log örnekleminde normal davranıştan farklı görünen kayıtlar, özellikle olay türüyle
> uyumsuz/olağandışı şiddet (severity) seviyeleri ve alışılmadık kaynak portları içerenlerdir.
> Rutin 'started' mesajları, başarılı SSH girişleri ve bazı bağlantı kabul/red kayıtları
> CRITICAL/ERROR gibi yüksek seviyelerle loglanmış; ayrıca SSH oturumlarında kaynak portu olarak
> 53/80/443 gibi sabit servis portları görülmektedir.

**Kanıtlar:**
- Rutin başlangıç mesajları CRITICAL seviyesinde: 07:03:28.500Z cron 'cron started' CRITICAL,
  07:05:33.621Z kernel 'kernel started' CRITICAL, 07:04:24.699Z nginx 'GET /admin 200' CRITICAL.
- Başarılı SSH oturumları yüksek seviyeli: 07:03:38.014Z 'Accepted password for admin' CRITICAL,
  07:03:47.212Z 'Accepted password for admin' ERROR, 07:04:17.661Z 'Accepted password for
  service' CRITICAL.
- SSH bağlantılarında kaynak portu olarak 53, 80, 443 gibi sabit portlar kullanılmış:
  07:03:29.325Z root sshd src_port=53, 07:03:47.212Z admin sshd src_port=80, 07:04:26.080Z alice
  sshd src_port=80.
- HTTP yanıtları ile severity uyumsuz: 07:03:08.611Z 'POST / 500' CRITICAL, 07:04:24.699Z 'GET
  /admin 200' CRITICAL, 07:05:47.813976Z 'GET /login 200' ERROR.
- Kernel bağlantı loglarında ACCEPT/REJECT/DROP işlemleri tutarsız severity içeriyor:
  07:03:42.582Z 'Connection ACCEPT' CRITICAL, 07:04:03.007Z 'Connection ACCEPT' CRITICAL,
  07:03:32.852Z 'Connection REJECT' WARNING.

### Soru 6: Olası bir güvenlik olayına işaret eden loglar var mı?

> Evet, örnek log kayıtlarında potansiyel bir güvenlik olayına işaret edebilecek bazı bulgular
> mevcut. Özellikle SSH hizmetinde çok sayıda başarısız parola denemesi ve bazı harici IP
> adreslerinden root/admin gibi ayrıcalıklı hesaplara yapılan başarılı girişler dikkat çekiyor.
> Ayrıca kernel tarafında çok sayıda bağlantı DROP/REJECT işlemi görülüyor; bunlar olası bir
> tarama veya saldırı girişiminin engellendiği şeklinde yorumlanabilir. Nginx üzerinde de /admin
> ve /login yollarına yoğunlaşan 500 ve 404 hataları, olası bir keşif veya istismar denemesinin
> belirtisi olabilir. Ancak bu örneklem üzerinden kesin bir sonuca varmak için daha kapsamlı
> analiz ve bağlam (ör. IP adreslerinin bilinirliği, zaman aralığı, kullanıcı davranışları)
> gereklidir.

**Kanıtlar:**
- Çok sayıda 'Failed password' SSH olayı: örn. service, bob, root, admin, alice kullanıcıları
  için farklı IP'lerden başarısız denemeler (215.150.6.105, 157.147.182.10, 212.242.175.225,
  vb.)
- Harici IP adreslerinden root/admin hesaplarına başarılı SSH girişleri: örn. 185.52.79.113
  (root), 135.94.199.199 (root), 30.229.253.155 (admin) gibi.
- Kernel günlüklerinde çok sayıda 'Connection DROP' ve 'Connection REJECT' olayı: çeşitli iç ve
  dış IP'ler arasında engellenen bağlantılar.
- Nginx günlüklerinde /admin ve /login yollarına yapılan isteklerde 500 ve 404 hataları: örn.
  'POST /admin 500', 'GET /login 404' gibi.
- Ayrıca sshd, nginx, cron ve sudo servislerinin sık sık başlatılması, olası bir kesinti veya
  yeniden başlatma faaliyetine işaret edebilir.