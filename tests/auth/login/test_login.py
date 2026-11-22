import asyncio
from uuid import uuid4 
import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy import exc
from src.auth import service
from src.database.models.models import User, User_Credential,Session,Session_Token_Jtis



pytestmark = pytest.mark.anyio


async def test_create_user(client:AsyncClient,test_session_factory):
    "Test Kullanıcısı oluşturma"
    form_data = {
        "name": "TestUser",
        "surname": "TestUserSurname",
        "email": "login-test@example.com",
        "phone_number":"+90 532 123 45 67",
        "age": 21,
        "password": "P@ssw0rd!",
    }

    async def request():
        return await client.post("/api/auth/register",json=form_data)

    reponse = await request()

    assert reponse.status_code == 201

    async with test_session_factory() as session:
        saved_count = await session.scalar(
            select(func.count())
            .select_from(User_Credential)
            .where(User_Credential.email == form_data["email"])
        )
              
    assert saved_count == 1



async def test_successful_login(client,test_session_factory):
    "Başarılı giriş testi"
    form_data = {
       "email": "login-test@example.com"  ,
       "password": "P@ssw0rd!"  
    }

    async def login_request():
        return await client.post("api/auth/login",json=form_data)

    try:
        response = await login_request()

        assert response.status_code == 200

        async with test_session_factory() as session:
             user_id = await session.scalar(
                select(User_Credential.user_id)
                .where(User_Credential.email == form_data["email"])
             )
             session_count = await session.scalar(
                 select(func.count())
                 .select_from(Session)
                 .where(Session.user_id == user_id)
             )
             session_id =  await session.scalar(
                 select(Session.id)
                 .where(Session.user_id == user_id)
             )

             jti_count = await session.scalar(
                 select(func.count())
                 .select_from(Session_Token_Jtis)
                 .where(Session_Token_Jtis.session_id == session_id)
             )

        assert session_count == 1     
        assert jti_count == 2
        
    finally:
       async with test_session_factory.begin() as session :
        user_id  = await session.scalar(
            select(User_Credential.user_id)
            .where(User_Credential.email==form_data["email"])
        )  

        await session.execute(
            delete(Session)
            .where(Session.user_id == user_id)
        )













