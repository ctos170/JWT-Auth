import asyncio
import pytest
from sqlalchemy import delete, func, select,update
from sqlalchemy import exc
from src.auth import service
from src.database.models.models import User, User_Credential,Session,Session_Token_Jtis



pytestmark = pytest.mark.anyio

test_params = (
"email,password,expected_status,expected_session_count,expected_jti_count,is_active,email_verified"
)

test_data=[
    ("login-test@example.com","P@ssw0rd!",200,1,2,True,True),# * Başarılı giriş
    ("wrong@example.com","P@ssw0rd!",400,0,0,True,True),# * Olmayan eposta
    ("login-test@example.com","WrongPass",400,0,0,True,True),# * Hatalı parola
    ("login-test@example","P@ssd!",422,0,0,True,True), # * Geçersiz istek verisi
    ("login-test@example.com","P@ssw0rd!",403,0,0,False,True), # * Devre dışı hesap
    ("login-test@example.com","P@ssw0rd!",403,0,0,True,False),# * Doğrulanmamış eposta
]

@pytest.mark.parametrize(
test_params,        
test_data
)
async def test_login(
    email,
    password,
    expected_status,
    expected_session_count,
    expected_jti_count,
    is_active,
    email_verified,
    client,
    test_session_factory,
    login_user_data
    ):
      
      
      form_data = {
         "email": email ,
         "password": password  
      }

      async with test_session_factory.begin() as session:
          await session.execute(
              update(User)
              .where(User.id == login_user_data)
              .values(is_active=is_active,email_verified=email_verified)
          )

      async def login_request():
          return await client.post("api/auth/login",json=form_data)

      try:
        response = await login_request()

        assert response.status_code == expected_status

        async with test_session_factory() as session:
             session_count = await session.scalar(
                 select(func.count())
                 .select_from(Session)
                 .where(Session.user_id == login_user_data)
             )
             session_id = await session.scalar(
                 select(Session.id)
                 .where(Session.user_id == login_user_data)
             )
             jti_count = await session.scalar(
                 select(func.count())
                 .select_from(Session_Token_Jtis)
                 .where(Session_Token_Jtis.session_id == session_id)
             )

        assert session_count == expected_session_count
        assert jti_count == expected_jti_count
        
      finally:
         async with test_session_factory.begin() as session :
            await session.execute(
               delete(Session)
               .where(Session.user_id == login_user_data)
            )















