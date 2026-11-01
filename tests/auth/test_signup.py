import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import delete, func, select

from src.database.models.models import User, User_Credential


pytestmark = pytest.mark.anyio



async def test_successful_registration(client: AsyncClient, test_session_factory):
    # İki istekte de farklı e-posta kullanarak ikisinin başarılı olmasını bekliyoruz.
    first_requests_email = f"testuser-{uuid4().hex}@example.com"
    second_requests_email = f"testuser-{uuid4().hex}@example.com"
    emails = [first_requests_email, second_requests_email]

    first_request_data = {
        "name": "TestUser",
        "surname": "TestUserSurname",
        "email": first_requests_email,
        "age": 21,
        "password": "P@ssw0rd!",
    }

    second_request_data = {
        "name": "TestUser2",
        "surname": "TestUserSurname2",
        "email": second_requests_email,
        "age": 21,
        "password": "P@ssw0rd!",
    }

    async def register_request(form_data):
        # Her çağrı ayrı bir HTTP kayıt isteği gönderir.
        return await client.post("/auth/register", json=form_data)

    try:
        # İki kayıt isteğini aynı anda gönder ve yanıtlarını aynı sırada al.
        responses = await asyncio.gather(
            register_request(first_request_data),
            register_request(second_request_data),
            return_exceptions=True,
        )

        # İsteklerden biri beklenmeyen bir istisna verdiyse bunu test hatası olarak göster.
        assert all(not isinstance(response, Exception) for response in responses), responses

        # Her iki HTTP isteğinin de başarılı kayıt yanıtı verdiğini doğrula.
        assert [response.status_code for response in responses] == [201, 201] # type: ignore
        assert all(response.json()["status_code"] == 201 for response in responses) # type: ignore

        # * Konsolda yanıt gövdelerini inceleyebilmek için yazdır.
        for response in responses:
            print(f"HTTP {response.status_code}: {response.json()}") # type: ignore

        # * HTTP yanıtlarının yanında iki kaydın da test veritabanına yazıldığını doğrula.
        async with test_session_factory() as session:
            saved_count = await session.scalar(
                select(func.count())
                .select_from(User_Credential)
                .where(User_Credential.email.in_(emails))
            )

        assert saved_count == 2
    finally:
        # * Yalnızca bu testin oluşturduğu kullanıcıları sil; diğer test verilerine dokunma.
        async with test_session_factory.begin() as session:
            user_ids = select(User_Credential.user_id).where(
                User_Credential.email.in_(emails)
            )
            await session.execute(delete(User).where(User.id.in_(user_ids)))



async def test_previously_registered_email(client:AsyncClient,test_session_factory):
    "Önceden kayıtlı e-posta testi"
    email = f"testuser-{uuid4().hex}@example.com"
    form_data = {
            "name": "TestUser",
            "surname": "TestUserSurname",
            "email": email,
            "age": 21,
            "password": "P@ssw0rd!",
        } 

    async def register():       
       return await client.post("/auth/register",json=form_data)

    try:
      successful_response = await register()
      assert successful_response.status_code == 201

      conflict_response = await register()
      assert conflict_response.status_code == 409
      assert conflict_response.json()["detail"] == "Bu e-posta adresi zaten kullanımda."

      print(f"başarılı cevap : {successful_response.json()} : status code : {successful_response.status_code}")
      print(f"başarısız cevap : {conflict_response.json()} : status code : {conflict_response.status_code}")

      async with test_session_factory() as session:
            saved_count = await session.scalar(
                select(func.count())
                .select_from(User_Credential)
                .where(User_Credential.email == email)
            )
      
      assert saved_count == 1
    finally:
        async with test_session_factory.begin() as session :
           stmt = select(User_Credential.user_id).where(User_Credential.email==email)
           user_id = await session.scalar(stmt)
           
           await session.execute(delete(User).where(User.id == user_id))

    
    
