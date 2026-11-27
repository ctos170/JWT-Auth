import asyncio
import pytest
from sqlalchemy import delete, func, select,update
from src.database.models.models import Session,Session_Token_Jtis,Token_Blacklist
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession

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
    test_session_factory:async_sessionmaker[AsyncSession],
    login_user_data
    ):
      "basic login scenarios"
      
      user_id = await login_user_data(
         is_active=is_active,
         email_verified=email_verified,
      )

      form_data = {
         "email": email ,
         "password": password  
      }

      async def login_request():
          return await client.post("api/auth/login",json=form_data)

      try:
        response = await login_request()

        assert response.status_code == expected_status

        async with test_session_factory() as session:
             session_count = await session.scalar(
                 select(func.count())
                 .select_from(Session)
                 .where(Session.user_id == user_id)
             )
             session_id = await session.scalar(
                 select(Session.id)
                 .where(Session.user_id == user_id)
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
               .where(Session.user_id == user_id)
            )


async def test_login_revokes_previous_sessions(
    client,
    test_session_factory:async_sessionmaker[AsyncSession],
    login_user_data):
    """
    Sequential login test with same user
    Previous sessions have to revoked.
    Active access tokens associated with previous sessions have to be added to the blacklist.
    """
    user_id = await login_user_data()
    previous_access_jti: str = ""

    form_data = {
        "email":"login-test@example.com",
        "password":"P@ssw0rd!" 
    }
    
    async def login_request():
        return await client.post("api/auth/login",json=form_data)

    try:
        first_response = await login_request()
        second_response = await login_request()

        assert first_response.status_code == 200
        assert second_response.status_code == 200

        async with test_session_factory() as session:
            session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(Session.user_id == user_id)
            )

            result = await session.scalars(
                select(Session.id)
                .where(Session.user_id == user_id)
            )

            session_ids = result.all()

            jti_count = await session.scalar(
                select(func.count())
                .select_from(Session_Token_Jtis)
                .where(Session_Token_Jtis.session_id.in_(session_ids))
            )
            
            revoke_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == user_id,
                    Session.is_revoked.is_(True)
                )
            )
            
            revoke_seession_id = await session.scalar(
                select(Session.id)
                .where(
                    Session.user_id == user_id,
                    Session.is_revoked.is_(True)
                )
            )
            
            access_jti = await session.scalar(
                select(Session_Token_Jtis.jti)
                .where(
                    Session_Token_Jtis.session_id == revoke_seession_id,
                    Session_Token_Jtis.token_type == "access"
                )
            )
            
            previous_access_jti = access_jti # type: ignore
            
            blacklisted_jti_count = await session.scalar(
              select(func.count())
              .select_from(Token_Blacklist)
              .where(
                  Token_Blacklist.jti == access_jti
              )
            )

        assert session_count == 2
        assert jti_count == 4
        assert revoke_session_count == 1
        assert blacklisted_jti_count == 1

    finally:
        async with test_session_factory.begin() as session:
            await session.execute(
                delete(Token_Blacklist)
                .where(Token_Blacklist.jti == previous_access_jti)
            )


async def test_concurrent_login_same_user(
    client,
    test_session_factory:async_sessionmaker[AsyncSession],
    login_user_data):
    """"
    3 concurrent login test with same user.
    previous sessions associated with user have to be revoked.
    Only one session should be active.
    Active access tokens associated with previous sessions have to be added to the blacklist.
    """
  
    user_id = await login_user_data()
    previous_access_jtis: list[str] = []
    
  
    form_data = {
          "email":"login-test@example.com",
          "password":"P@ssw0rd!" 
      }
      
    async def login_request():
        return await client.post("api/auth/login",json=form_data)

    try:
       responses = await asyncio.gather(
           login_request(),
           login_request(),
           login_request(),
           return_exceptions=True
       )

       assert [response.status_code for response in responses] == [200, 200, 200] # type:ignore

       async with test_session_factory() as session:
           session_count = await session.scalar(
               select(func.count())
               .select_from(Session)
               .where(Session.user_id == user_id)
           )
          
           active_session_count = await session.scalar(
               select(func.count())
               .select_from(Session)
               .where(
                   Session.user_id == user_id,
                   Session.is_revoked.is_(False),
                )
           )

           revoke_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == user_id,
                    Session.is_revoked.is_(True),
                )
            )
           
           result = await session.scalars(
                select(Session.id)
                .where(Session.user_id == user_id)
            )
           
           session_ids = result.all()

           jti_count = await session.scalar(
               select(func.count())
               .select_from(Session_Token_Jtis)
               .where(Session_Token_Jtis.session_id.in_(session_ids))
           )

           revoke_session_result = await session.scalars(
               select(Session.id)
               .where(
                   Session.user_id == user_id,
                   Session.is_revoked.is_(True)
               )
           )
           
           revoke_session_ids = revoke_session_result.all()

           revoke_access_result = await session.scalars(
               select(Session_Token_Jtis.jti)
               .where(
                   Session_Token_Jtis.session_id.in_(revoke_session_ids),
                   Session_Token_Jtis.token_type == "access"
                )
           )
          
           revoke_access_jtis = revoke_access_result.all()

           previous_access_jtis = list(revoke_access_jtis)

           blacklisted_jti_count = await session.scalar(
               select(func.count())
               .select_from(Token_Blacklist)
               .where(Token_Blacklist.jti.in_(revoke_access_jtis))
           )

       assert session_count == 3   
       assert active_session_count == 1
       assert revoke_session_count == 2
       assert jti_count == 6
       assert blacklisted_jti_count == 2

    finally:
        async with test_session_factory.begin() as session:
            await session.execute(
                delete(Token_Blacklist)
                .where(Token_Blacklist.jti.in_(previous_access_jtis))
            )


async def test_concurrent_login_with_different_users(
    login_users_data,
    client,
    test_session_factory:async_sessionmaker[AsyncSession]
    ):
        """
        conncurrent login test with different users
        """
        first_user_id,second_user_id = await login_users_data()
        user_ids= [first_user_id,second_user_id]
    
        password="P@ssw0rd"
        first_users_email="testUser@example.com"
        second_users_email = "login-test@example.com"
    
        async def login_request(form_data):
           return await client.post("/api/auth/login",json=form_data)

        responses = await asyncio.gather(
          login_request({"email":first_users_email,"password":password}),
          login_request({"email":second_users_email,"password":password}),
          return_exceptions=True
        )

        assert [response.status_code for response in responses] == [200,200] #type:ignore

        async with test_session_factory() as session:
            first_user_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(Session.user_id == first_user_id)
            )

            second_user_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(Session.user_id == second_user_id)
            )

            first_user_active_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == first_user_id,
                    Session.is_revoked.is_(False)
                )
            )

            second_user_active_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == second_user_id,
                    Session.is_revoked.is_(False)
                )
            )

            first_user_revoke_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == first_user_id,
                    Session.is_revoked.is_(True)
                )
            )

            second_user_revoke_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(
                    Session.user_id == second_user_id,
                    Session.is_revoked.is_(True)
                )
            )
      
            total_session_count = await session.scalar(
                select(func.count())
                .select_from(Session)
                .where(Session.user_id.in_(user_ids))
            )

            result = await session.scalars(
                select(Session.id)
                .where(Session.user_id.in_(user_ids))
            ) 

            session_ids = result.all()

            total_jti_count = await session.scalar(
                select(func.count())
                .select_from(Session_Token_Jtis)
                .where(Session_Token_Jtis.session_id.in_(session_ids))  
            )

        assert total_session_count == 2    
        assert total_jti_count == 4

        assert first_user_session_count == 1
        assert second_user_session_count == 1
        assert first_user_active_session_count == 1
        assert second_user_active_session_count == 1
        assert first_user_revoke_session_count == 0
        assert second_user_revoke_session_count == 0

  
    





