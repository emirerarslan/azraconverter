# Güncelleme kurulumu

1. `update_config.json` içindeki `SUNUCU_ADRESINIZ` alanını sunucunuzun erişilebilir adresiyle değiştirin. Örnek: `http://azra.example.com:8765/version.json`.
2. Modeminizde TCP `8765` portunu bu bilgisayarın yerel IP adresine yönlendirin ve Windows Güvenlik Duvarı'nda bu porta izin verin.
3. Bu bilgisayarda `py update_server.py` komutunu çalıştırın. Bilgisayar açık kaldığı sürece güncelleme dosyaları erişilebilir olur.
4. Dağıtacağınız kurulum `.exe` dosyasını `updates` klasörüne koyun.
5. `updates/version.json` içindeki `version`, `download_url` ve `notes` alanlarını her yeni sürümde güncelleyin. `download_url` dosya adıyla aynı olmalıdır.

İstemci bilgisayarlarda uygulamanın yanında aynı `update_config.json` bulunmalıdır. Uygulamadaki **Hakkında > Güncellemeleri Kontrol Et** düğmesi bu dosyadaki adresi kullanır.

Önemli: İnternete doğrudan açılan ev bağlantılarında sabit IP veya dinamik DNS gerekir. Bu adres değişirse yalnızca `update_config.json` dosyasındaki adresi güncellemeniz yeterlidir.
