import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.db import get_db
from src.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from src.database.models.models import  User_Credential,User
from src.core.security import hash_password_async


# Load the project .env so the test suite can read TEST_DATABASE_URL.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must be set before running tests.")


@pytest.fixture
def anyio_backend():
    # asyncpg and asyncio.gather in these tests use the asyncio backend.
    return "asyncio"


@pytest.fixture
async def test_session_factory(anyio_backend):
    # Each test gets its own engine; concurrent tasks get separate sessions
    # from this shared factory.
    engine = create_async_engine(str(TEST_DATABASE_URL), echo=False)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        yield session_factory
    finally:
        await engine.dispose()


@pytest.fixture
async def client(test_session_factory):

    async def override_get_db():
        async with test_session_factory() as session:
            yield session
            
    app.dependency_overrides[get_db] = override_get_db        

    try:
        async with AsyncClient(
            transport=ASGITransport(app),
            base_url="http://127.0.0.1:8000"
        ) as client :
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def login_user_data(test_session_factory): 
    """
    Giriş testleri için test kullanıcısı oluşturan ve
    sonrasında silen fixture
    """
    created_user_ids = []
    
    async def create_user(is_active=True, email_verified=True):
       user_dict={
         "name": "TestUser",
         "surname": "TestUserSurname",
         "age": 21,
         "is_active":is_active,
         "email_verified":email_verified
       }
   
       credential_dict = {
         "email": "login-test@example.com",
         "phone_number":"+90 532 123 45 67",
       }

       password_hash = await hash_password_async("P@ssw0rd!")

       async with test_session_factory.begin() as session:
          user = User(**user_dict)
          session.add(user)
          
          await session.flush()
          user_id = user.id
          
          credential_dict["user_id"] = user_id # type:ignore
          credential_dict["password_hash"] = password_hash
          credential = User_Credential(**credential_dict)
  
          session.add(credential)
          created_user_ids.append(user_id)
       
       async with test_session_factory() as session:
          user_count = await session.scalar(
              select(func.count())
              .select_from(User)
              .where(User.id == user_id)
          )
          credential_count = await session.scalar(
              select(func.count())
              .select_from(User_Credential)
              .where(User_Credential.user_id == user_id)
          )
         
          assert user_count == 1
          assert credential_count == 1
               
       return user_id
    

    yield create_user
    
    async with test_session_factory.begin() as session:
        await session.execute(
            delete(User)
            .where(User.id.in_(created_user_ids))
        )              
  