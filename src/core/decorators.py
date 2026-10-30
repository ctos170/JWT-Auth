from functools import wraps
from fastapi import HTTPException, status
from typing import Callable
from sqlalchemy.exc import IntegrityError, OperationalError, DataError, SQLAlchemyError


def _get_constraint_name(error: BaseException) -> str | None:
    """Sürücü istisnası zincirinden PostgreSQL kısıt adını bulur."""
    pending = [error]
    checked = set()

    while pending:
        current = pending.pop()
        if id(current) in checked:
            continue
        checked.add(id(current))

        constraint_name = getattr(current, "constraint_name", None)
        if constraint_name:
            return constraint_name

        diagnostic = getattr(current, "diag", None)
        constraint_name = getattr(diagnostic, "constraint_name", None)
        if constraint_name:
            return constraint_name

        # SQLAlchemy async sürücü hatalarını bazen orig/cause/context içine sarar.
        for attribute in ("orig", "__cause__", "__context__"):
            nested_error = getattr(current, attribute, None)
            if nested_error is not None:
                pending.append(nested_error)

    return None


def handle_service_errors(func: Callable):
    """
    Service metodlarını DB ve beklenmedik sistem hatalarından korur.
    Hatayı türüne göre sınıflandırarak istemciye anlamlı yanıtlar döner.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            
            return await func(*args, **kwargs)
        except HTTPException:
            # FastAPI'nin kendi fırlattığı veya servis içinde bilerek 
            # fırlattığımız HTTP istisnaları doğrudan geçer, dokunmuyoruz.
            raise
        
        except IntegrityError as e:
            # PostgreSQL sürücü hatası SQLAlchemy tarafından sarılmış olabilir.
            # Kısıt adını istisna zincirinin tamamında ara.
            constraint_name = _get_constraint_name(e)
            if constraint_name == "ix_user_credentials_email":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Bu e-posta adresi zaten kullanımda.",
                ) from e

            # Diğer bütünlük ihlalleri genel hata mesajıyla dönmeye devam eder.
            print(f"⚠️ Integrity Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Girilen bilgiler veri tabanındaki kısıtlamaları ihlal ediyor (Benzersiz veri çakışması veya geçersiz referans)."
            )
            
        except OperationalError as e:
            # Gerçek veri tabanı bağlantı veya sunucu çökme hataları
            print(f"❌ Operational Error (DB Bağlantısı koptu veya ulaşılamıyor): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Veritabanı sunucusuna şu an ulaşılamıyor. Lütfen daha sonra tekrar deneyin."
            )
            
        except DataError as e:
            # Veri tipi uyuşmazlıkları (Örn: String alana çok uzun veri basmak, int alana uygunsuz veri yollamak)
            print(f"⚠️ Data Error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Veritabanına gönderilen verilerin formatı veya boyutu geçersiz."
            )
            
        except SQLAlchemyError as e:
            # Yukarıdakilere uymayan diğer genel SQLAlchemy/Veri tabanı hataları
            print(f"💥 Genel DB Hatası ({type(e).__name__}): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Veritabanı üzerinde işlem gerçekleştirilirken sistemsel bir hata oluştu."
            )
            
        except Exception as e:
            # Veri tabanı dışındaki tamamen yazılımsal beklenmedik hatalar (ValueError, KeyError, AttributeError vb.)
            print(f"🚨 Beklenmedik Sistem Hatası ({type(e).__name__}): {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Sunucu içi beklenmedik bir sistem hatası oluştu."
            )
    
    return wrapper
