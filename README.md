# JWT Auth API

FastAPI, PostgreSQL ve asenkron SQLAlchemy ile geliştirilen JWT tabanlı kimlik doğrulama ve oturum yönetimi projesi. Proje geliştirme aşamasındadır; test kapsamı ve bazı dağıtım ayrıntıları tamamlanacaktır.

## Özellikler

- Argon2 ile parola hashleme
- Kısa ömürlü access token ve HttpOnly refresh token cookie
- Refresh token rotation ve eski refresh tokenın tekrar kullanımını tespit etme
- Veritabanında oturum ve token JTI takibi
- Logout, parola değiştirme ve yeni girişte eski oturumları geçersiz kılma
- E-posta ile tek kullanımlık parola sıfırlama
- Alembic veritabanı migration'ları

## Teknolojiler

- Python, FastAPI, Pydantic Settings
- PostgreSQL, SQLAlchemy Async, asyncpg
- Alembic
- PyJWT, pwdlib/Argon2
- FastAPI-Mail
- pytest

## Kurulum

Python sanal ortamı oluşturup bağımlılıkları yükleyin:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`.env.example` dosyasını inceleyip kendi ortamınıza uygun değerlerle `.env` oluşturun. Var olan `.env` dosyanızın üzerine kopyalamayın. PostgreSQL'de uygulama için bir veritabanı oluşturun ve `DATABASE_URL` değerini bu veritabanına göre düzenleyin. Örnekteki `jwt_auth` ve `test_db` yalnızca örnek veritabanı adıdır.

SMTP ayarlarını e-posta sağlayıcınızın istediği şekilde girin. Örnek ayarlar 587 portunda STARTTLS kullanır. Parola sıfırlama e-postasındaki bağlantı `FRONTEND_BASE_URL` üzerinden oluşturulur; adres, ön yüzünüzün gerçek adresi olmalıdır.

Migration'ları uygulayın ve API'yi başlatın:

```powershell
alembic upgrade head
uvicorn src.main:app --reload
```

Swagger arayüzü `http://127.0.0.1:8000/docs` adresinde açılır.

## Ortam ayarları

| Değişken | Açıklama |
| --- | --- |
| `SECRET_KEY` | JWT imzalama anahtarı. Dağıtımda uzun ve rastgele bir değer kullanın. |
| `DATABASE_URL` | Uygulama PostgreSQL bağlantısı; `postgresql+asyncpg://...` biçimindedir. |
| `TEST_DATABASE_URL` | Testler için ayrı PostgreSQL veritabanı bağlantısı. |
| `DB_ECHO` | SQL sorgularını loglar. Yerelde inceleme için açılabilir; dağıtımda `false` bırakın. |
| `MAIL_*` | SMTP sunucusu, hesap ve TLS seçenekleri. |
| `FRONTEND_BASE_URL` | Parola sıfırlama bağlantısının yönleneceği ön yüz adresi. |
| `REFRESH_COOKIE_SECURE` | HTTPS dağıtımında `true` olmalı; yerel HTTP geliştirmesinde `false` kullanılır. |
| `REFRESH_COOKIE_SAMESITE` | `lax`, `strict` veya `none`. `none` kullanımı HTTPS ve `Secure` gerektirir. |
| `REFRESH_COOKIE_DOMAIN` | İsteğe bağlı cookie alan adı. Boş bırakıldığında cookie API alan adına özgüdür. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token ömrü (varsayılan 15 dakika). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token ve oturum ömrü (varsayılan 7 gün). |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Parola sıfırlama tokenı ömrü (varsayılan 15 dakika). |

`.env.example` dağıtım için daha güvenli örnek değerler içerir. HTTPS kullanmayan yerel geliştirmede `REFRESH_COOKIE_SECURE=false` ve `FRONTEND_BASE_URL=http://localhost:5173` ayarlarını yerel `.env` dosyanızda kullanın. Üretimde `DB_ECHO=false`, TLS sertifika doğrulaması açık ve HTTPS cookie ayarları etkin olmalıdır. Ön yüz ve API farklı sitelerdeyse cookie için `SameSite` ve CORS yapılandırması ayrıca uyumlu hale getirilmelidir.

## API uçları

| Metot | Uç | Açıklama |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Kullanıcı kaydı |
| `POST` | `/api/auth/login` | Giriş; access token gövdede, refresh token HttpOnly cookie'de döner |
| `POST` | `/api/auth/refresh` | Refresh cookie ile tokenları yenileme |
| `POST` | `/api/auth/logout` | Oturumu kapatma |
| `POST` | `/api/auth/forgot-password` | E-posta ile parola sıfırlama talebi |
| `POST` | `/api/auth/reset-password` | Tek kullanımlık token ile yeni parola belirleme |
| `GET` | `/api/users/me` | Giriş yapan kullanıcının profili; Bearer access token gerektirir |

## Testler

Testler için uygulama veritabanından ayrı bir PostgreSQL veritabanı oluşturun ve `TEST_DATABASE_URL` değerini ona yönlendirin. Migration dosyaları `DATABASE_URL` üzerinden çalıştığı için migration öncesinde bu değişkeni test veritabanına yönlendirin; böylece uygulama veritabanına test şeması uygulamazsınız. Ardından:

```powershell
$env:DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/jwt_auth_test"
alembic upgrade head
pytest
```

Mevcut otomatik test aynı e-posta ile eşzamanlı kayıt girişiminde tek kaydın oluşturulmasını ve diğer isteğin `409 Conflict` almasını kontrol ediyor. Diğer auth akışları ve parola sıfırlama senaryoları için testler geliştirme planındadır.
