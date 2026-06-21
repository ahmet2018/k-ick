# Kick Viewer Discord Bot

Bu bot, `sa.py` (Kick Viewer Bot) kodunun Discord botuna dönüştürülmüş halidir. Render.com gibi platformlarda sorunsuz çalışması için tasarlanmıştır.

## Özellikler
- **Discord Entegrasyonu:** `!baslat`, `!durum`, `!durdur` komutları ile yönetim.
- **Keep-Alive:** Render'da botun uyumasını engelleyen web sunucusu (Port 8080).
- **Gelişmiş İstatistikler:** Discord üzerinden canlı veri takibi.

## Kurulum

1. **Gerekli Kütüphaneleri Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Discord Token Ayarı:**
   Botun çalışması için bir Discord Bot Token'ına ihtiyacınız var. Bunu bir çevresel değişken (Environment Variable) olarak ekleyin:
   - **Windows:** `set DISCORD_TOKEN=senin_tokenin`
   - **Linux/Render:** Çevresel değişken ayarlarına `DISCORD_TOKEN` anahtarını ve token değerinizi ekleyin.

3. **Çalıştırma:**
   ```bash
   python bot.py
   ```

## Discord Komutları
- `!baslat [kanal_adi] [izleyici_sayisi]`: Botu belirtilen kanal için başlatır.
- `!durum`: Çalışan botun anlık istatistiklerini gösterir.
- `!durdur`: Çalışan botu durdurur.

## Render.com Notu
Render'da "Web Service" olarak oluşturun. Bot otomatik olarak 8080 portunda bir web sayfası açacak ve botu aktif tutacaktır.
