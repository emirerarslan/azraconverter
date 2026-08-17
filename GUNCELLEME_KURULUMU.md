# Güncelleme yayını

1. Uygulama sürümünü ve Inno Setup sürümünü aynı değere yükseltin.
2. Değişiklikleri `main` dalına gönderin.
3. Aynı sürümle bir Git etiketi oluşturup gönderin: `git tag v1.1.0` ve `git push origin v1.1.0`.
4. `.github/workflows/release.yml` Windows uygulamasını, ilk kurulum EXE'sini ve program içi güncelleme ZIP'ini üretir.
5. İş akışı EXE/ZIP SHA-256 değerlerini içeren `version.json` dosyasını GitHub Release'e yükler.

İstemci sırasıyla GitHub Release manifestini, GitHub Releases API'yi ve Raw manifesti dener. Böylece tek bir servisin `429` veya geçici bağlantı hatası güncellemeyi durdurmaz.

`1.1.1` ve sonraki sürümlerde uygulama `package_url` paketini indirir, SHA-256 değerini doğrular, güvenli geçici klasöre açar, uygulama kapandıktan sonra dosyaları yerinde değiştirir ve programı yeniden başlatır. Kurulum EXE'si yalnızca ilk kurulum ve eski sürümlerden geçiş için tutulur.

Eski `1.0.x` kurulumlarında yalnızca Raw adresi bulunduğundan bir kereliğine yeni kurulum paketini elle yüklemek veya uygulama klasöründeki `update_config.json` dosyasını güncellemek gerekebilir.
