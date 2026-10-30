from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status,Request
from src.database.models.models import User,Session_Token_Jtis,Token_Blacklist
from fastapi.exceptions import HTTPException
from src.core.decorators import handle_service_errors
from .schemas import Register_Request,Login_Request
from .repository import (
   get_user_by_email_or_phone_number,
   create_user,
   revoke_sessions,
   create_session,add_blacklist,
   get_active_session,
   get_revoke_sessions_ids,
   get_revoke_sessions_access_token,
   create_session_token_jti,
   get_jti_from_blacklist,
   get_refresh_jti,
   get_access_token_by_jti,
   get_active_access_token_jti
)
from src.core.security import hash_password,verify_password,create_access_token,create_refresh_token,create_random_token
from datetime import datetime,timezone,timedelta
from src.core.config import settings
from typing import Any



@handle_service_errors
async def register_user(form_data:Register_Request,session:AsyncSession):
  
    user = await get_user_by_email_or_phone_number(
        session,
        form_data.email,
        phone_number=form_data.phone_number
    )

    if user :
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu e-posta adresi zaten kullanımda."
        )

 
    hashed_password = hash_password(form_data.password)

    user_dict = form_data.model_dump(include={"name","surname","age"})

    credential_dict = form_data.model_dump(include={"email","phone_number"})

    credential_dict["password_hash"] = hashed_password   

    await create_user(user_dict,credential_dict,session)

    return {"message":"Kayıt başarlı.Giriş yapabilirsiniz."}


@handle_service_errors
async def user_login(form_data:Login_Request,req:Request,session:AsyncSession):
    # * Transaction sorgudan önce başlar; sorgu önce çalışırsa SQLAlchemy autobegin
    # * yapar ve ardından session.begin() çağrısı zaten başlamış transaction hatası verir.
    
    # * Reading Phase
    async with session.begin():
       user = await get_user_by_email_or_phone_number(session,form_data.email)
       if not user:
          raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hatalı eposta veya şifre"
       )
       
       user_id = user.user_id
       password_hash = user.password_hash
    
    is_match = verify_password(form_data.password,password_hash)
    if not is_match:
        print(1)
        DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$42aXpYemRzeWRzZ2RzZ2RzZ2Q$FakeHashToPreventTimingAttacks"
        verify_password(form_data.password,DUMMY_HASH)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hatalı eposta veya şifre"
    )
    
    # * Writing Phase
    async with session.begin():
        # * Başarılı login'in tüm DB değişiklikleri aynı transaction içinde yapılır.
        now=datetime.now(timezone.utc)

        await revoke_sessions(session,user_id)
        revoke_session_ids = await get_revoke_sessions_ids(session,user_id)
        live_access_rows = await get_revoke_sessions_access_token(session,revoke_session_ids)

        live_access_jtis = [ token_row.jti for token_row in live_access_rows]
 
        blacklisted_jtis = set(await get_jti_from_blacklist(session,live_access_jtis))

        for access_row in live_access_rows:
            if access_row.jti not in blacklisted_jtis:
                blacklist_dict = {
                "jti": access_row.jti,
                "revoked_at": now,
                "expires_at": access_row.expires_at
                }
                await add_blacklist(session,blacklist_dict)

        # * Yeni oturum ve tokenlar; transaction sonunda birlikte kaydedilir.
        refresh_jti = create_random_token()
        access_jti = create_random_token()
        access_token = create_access_token(str(user_id),access_jti)
        refresh_token = create_refresh_token(str(user_id),refresh_jti)

        session_dict = {
            "user_id":user_id,
            "refresh_token_jti": refresh_jti,
            "device_info": req.headers.get("user-agent", "unknown"),
            "ip_address": req.client.host if req.client else "unknown",
            "expires_at": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        }

        user_session = await create_session(session,session_dict)
        session_id = user_session.id

        access_jti_dict = {
            "jti":access_jti,
            "session_id":session_id,
            "token_type":"access",
            "expires_at":now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        }

        refresh_jti_dict = {
            "jti":refresh_jti,
            "session_id":session_id,
            "token_type":"refresh",
            "expires_at":now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        }

        await create_session_token_jti(
            session,
            access_jti_dict=access_jti_dict,
            refresh_jti_dict=refresh_jti_dict,
        )

    # * begin bloğundan normal çıkış commit edildi; tokenları endpoint'e dön.
    return {"access_token":access_token,"refresh_token":refresh_token}


@handle_service_errors
async def refresh_tokens(session:AsyncSession,jti:str):
  replay_detected = False
  session_detected = False
  session_refresh_token_detected = False

  now=datetime.now(timezone.utc)

  async with session.begin():
      active_session = await get_active_session(session,jti=jti)

      session_refresh_token = await get_refresh_jti(session,jti)

      # * Kullanılmış eski refresh token tekrar geldiyse, bağlı olduğu oturumu kapat.
      # * Bu, saldırganın rotation sırasında aldığı yeni refresh token'ı da geçersiz kılar.
      if not active_session:
        if session_refresh_token and session_refresh_token.used_at:
            # * Tekrar kullanılmaya çalışılan refresh jtiye ait oturum.
            replayed_session = session_refresh_token.session

            # * Eski/revoke edilmiş bir oturumun tokenı yeni oturumu etkilememeli.
            if replayed_session and not replayed_session.is_revoked:
                replay_detected = True
                replayed_session.is_revoked = True

                live_access_rows = [
                    token_row for token_row in replayed_session.session_jtis
                    if token_row.token_type == "access" and token_row.expires_at > now
                ]

                live_access_jtis = [ token_row.jti for token_row in live_access_rows]
                
                already_blacklisted = set(
                    await get_jti_from_blacklist(session, live_access_jtis)
                ) if live_access_jtis else set()
                
                # * Oturumun token geçmişini revoke olarak işaretle; access JTI'lerini
                # * yalnızca blacklist'te yoklarsa ekle (JTI blacklist'te primary key).
                for token_row in replayed_session.session_jtis:
                    token_row.revoked_at = now

                for token_row in live_access_rows:
                    if token_row.jti not in already_blacklisted:
                        session.add(Token_Blacklist(
                            jti=token_row.jti,
                            revoked_at=now,
                            expires_at=token_row.expires_at,
                        ))

      elif not session_refresh_token :  
        # *  Aktif oturum bulunduysa JTI geçmiş kaydı da olmalı ve ilk kullanım olmalı.
        session_refresh_token_detected = False
           
      elif session_refresh_token.used_at:  
          replay_detected = True
          # * Tutarsız durumda da aynı oturumun token ailesini güvenli biçimde kapat.
          active_session.is_revoked = True
          for token_row in active_session.session_jtis:
              token_row.revoked_at = now
          access_rows = [
              token_row for token_row in active_session.session_jtis
              if token_row.token_type == "access" and token_row.expires_at > now
          ]
          existing = set(await get_jti_from_blacklist(
              session, [token_row.jti for token_row in access_rows]
          )) if access_rows else set()
          for token_row in access_rows:
            if token_row.jti not in existing:
                session.add(Token_Blacklist(
                    jti=token_row.jti,
                    revoked_at=now,
                    expires_at=token_row.expires_at,
                ))
      
      else:
       replay_detected = False  
       session_detected = True 
       session_refresh_token_detected = True

       user_id = active_session.user_id

       refresh_jti = create_random_token()
       access_jti = create_random_token()
       access_token = create_access_token(str(user_id),access_jti)
       refresh_token = create_refresh_token(str(user_id),refresh_jti)

       # * Eski refresh JTI geçmişte kalır (used_at dolar); oturum yeni JTI'ye geçer.
       session_refresh_token.used_at = now
       active_session.refresh_token_jti = refresh_jti # * mevcut oturumdaki refresh jti değişti
       active_session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
       active_session.updated_at = now

        # *  Yeni access ve refresh JTI'lerini aynı oturumun geçmişine ekle.
       session.add_all([
        Session_Token_Jtis(
            jti=access_jti,
            session_id=active_session.id,
            token_type="access",
            expires_at=now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
        Session_Token_Jtis(
            jti=refresh_jti,
            session_id=active_session.id,
            token_type="refresh",
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ),
    ])
  
  # * Exeptionlar transaction dışında alındı
  if replay_detected:
         raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Daha önce kullanılmış refresh token tespit edildi. Lütfen tekrar giriş yapın."
          )   

  if not session_detected :
       raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Aktif oturum bulunamadı.Oturumunuzun süresi dolmuş veya çıkış yapılmış.Lütfen tekrar giriş yapın."
        )
 
  if not session_refresh_token_detected :
       raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token oturum kaydı bulunamadı. Lütfen tekrar giriş yapın."
        )    


  
  return {"access_token": access_token, "refresh_token": refresh_token}
    

@handle_service_errors
async def user_logout(session:AsyncSession,payload:dict[str,Any]):
    user_id = payload["sub"]
    access_jti = payload["jti"] 
    expires = payload["exp"]

    async with session.begin() :
       access_token_jti = await get_access_token_by_jti(access_jti,session)
       
       if access_token_jti :
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail="Oturumunuz zaten kapalıdır.Lütfen tekrar giriş yapınız."
       )
    

       active_token = await get_active_access_token_jti(access_jti,session)
    
       if not active_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Aktif oturum bulunamadı.Oturumunuzun süresi dolmuş veya çıkış yapılmış.Lütfen tekrar giriş yapın."
        )

       active_session =  active_token.session
       active_session.is_revoked = True
    
       now = datetime.now(timezone.utc)

       expires_at = datetime.fromtimestamp(expires, tz=timezone.utc)
    
       blacklist_dict = {
        "jti" : access_jti,
        "revoked_at":now,
        "expires_at":expires_at
        }

       await add_blacklist(session,blacklist_dict)

    return {"message":"Çıkış başarılı"}
         
