from sqlalchemy import select,or_,update
from sqlalchemy.orm import selectinload,joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.models import User,User_Credential,Session,Token_Blacklist,Session_Token_Jtis
from datetime import datetime,timezone,timedelta
from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from typing import Optional,Any
from uuid import UUID
from typing import Sequence



async def get_user_by_email_or_phone_number(session:AsyncSession,email:str,phone_number:Optional[str]=None):

    expressions = []

    expressions.append(User_Credential.email == email)

    if phone_number:
        expressions.append(User_Credential.phone_number == phone_number)    

    
    stmt = (
            select(User_Credential)
            .options(joinedload(User_Credential.user))
            .where(
                or_(*expressions)
                )
            )
    
    result = await session.scalars(stmt)
        
    return result.unique().one_or_none()


async def create_user(user_dict:dict[str,Any],credential_dict:dict[str,Any],session:AsyncSession):

    user = User(**user_dict)

    session.add(user)

    await session.flush()

    credential_dict["user_id"] = user.id

    credential = User_Credential(**credential_dict)

    session.add(credential)

    return user


async def revoke_sessions(session:AsyncSession,user_id:UUID):
    stmt = update(Session).where(Session.user_id == user_id).values(is_revoked=True)

    await session.execute(stmt)


async def create_session(session:AsyncSession,session_dict:dict[str,Any]):
   user_session = Session(**session_dict)

   session.add(user_session)
   await session.flush()
   
   return user_session   


async def get_active_session(
        session:AsyncSession,
        jti:Optional[str]=None,
        user_id:Optional[UUID]=None):
    
    "id veya jti'ye göre aktif oturum bulma"
    now = datetime.now(timezone.utc)
    expressions = []

    if jti :
        expressions.append(Session.refresh_token_jti == jti)

    if user_id:
        expressions.append(Session.user_id == user_id)
    
    stmt = select(Session).options(selectinload(Session.session_jtis)).where(
        *expressions,
        Session.is_revoked == False,
        Session.expires_at > now
    ).with_for_update()

    result = await session.scalars(stmt)

    return result.one_or_none()       


async def add_blacklist(session:AsyncSession,blacklist_dict:dict[str,Any]):
    stmt = Token_Blacklist(**blacklist_dict)

    session.add(stmt)
    

async def get_jti_from_blacklist(session:AsyncSession,jtis:Sequence[str]):
    
    stmt = select(Token_Blacklist.jti).where(Token_Blacklist.jti.in_(jtis))

    result = await session.scalars(stmt)

    return result.all() 

                   
async def get_revoke_sessions_access_token(session:AsyncSession,session_ids:Sequence[UUID]):
    "iptal edilen oturumlara ait süresi geçerli access token jtilerini döndüren metod"
    now = datetime.now(timezone.utc)

    stmt = select(Session_Token_Jtis).where(
        Session_Token_Jtis.session_id.in_(session_ids),
        Session_Token_Jtis.token_type == "access",
        Session_Token_Jtis.expires_at > now
    )  

    result = await session.scalars(stmt)

    return result.all()


async def get_refresh_jti(session:AsyncSession,jti:str):
 
    now = datetime.now(timezone.utc)

    stmt = select(Session_Token_Jtis).options(
        # Replay tespitinde JTI'nin bağlı olduğu oturum ve token geçmişi de gerekir.
        selectinload(Session_Token_Jtis.session).selectinload(Session.session_jtis)
    ).where(
        Session_Token_Jtis.jti == jti,
        Session_Token_Jtis.token_type == "refresh",
        Session_Token_Jtis.expires_at > now,
    ).with_for_update()

    result = await session.scalars(stmt)

    return result.one_or_none()


async def create_session_token_jti(
    session:AsyncSession,
    access_jti_dict: Optional[dict[str,Any]]=None,
    refresh_jti_dict:Optional[dict[str,Any]]=None
    ):


    if access_jti_dict:
     session_access_token_jti = Session_Token_Jtis(**access_jti_dict)
     session.add(session_access_token_jti)
     
    if refresh_jti_dict:
     session_refresh_token_jti = Session_Token_Jtis(**refresh_jti_dict)
     session.add(session_refresh_token_jti)
        
    
async def get_revoke_sessions_ids(session:AsyncSession,user_id:UUID):
    "iptal edilen oturumların idlerini bulma"

    stmt = select(Session.id).where(Session.user_id == user_id,Session.is_revoked == True)

    result = await session.scalars(stmt)      

    return result.all()         


async def get_access_token_by_jti(jti:str,session:AsyncSession):
    "Blacklist tablosundan jtiye göre access token bulma" 
    stmt = select(Token_Blacklist).where(Token_Blacklist.jti == jti)  
    result = await session.scalars(stmt)

    return result.one_or_none()


async def get_active_access_token_jti(jti: str, session: AsyncSession):
    """Return an unrevoked access-token record and its session, if still active."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Session_Token_Jtis)
        .options(joinedload(Session_Token_Jtis.session))
        .where(
            Session_Token_Jtis.jti == jti,
            Session_Token_Jtis.token_type == "access",
            Session_Token_Jtis.revoked_at.is_(None),
            Session_Token_Jtis.expires_at > now,
            Session.is_revoked.is_(False),
            Session.expires_at > now,
        )
        .join(Session_Token_Jtis.session)
    )

    result = await session.scalars(stmt)
    return result.unique().one_or_none()
