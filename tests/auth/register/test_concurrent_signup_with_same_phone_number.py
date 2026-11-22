import asyncio
from uuid import uuid4
import pytest
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import delete, func, select
from src.auth import service as auth_service
from src.auth.schemas import Register_Request
from src.database.models.models import User, User_Credential
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing import Any


@pytest.mark.anyio
async def test_concurrent_signup_with_same_phone_number(
    test_session_factory, monkeypatch
):
    marker = uuid4().hex
    phone_number = "+90 543 981 4312"
    
    attempts = [
        {
            "name": f"RaceFirst-{marker}",
            "surname": "User",
            "age": 25,
            "email": f"sign-up-race-{uuid4().hex}@example.com",
            "phone_number": phone_number,
            "password": "StrongPass123!",
        },
        {
            "name": f"RaceSecond-{marker}",
            "surname": "User",
            "age": 25,
            "email": f"sign-up-race-{uuid4().hex}@example.com",
            "phone_number":phone_number,
            "password": "StrongPass123!",
        },
    ]

    attempt_names = [form_values["name"] for form_values in attempts]

    original_lookup = auth_service.find_user_by_phone_number
    lookup_count = 0
    lookup_results = []
    both_lookups_finished = asyncio.Event()

    async def synchronized_lookup(requested_phone_number:PhoneNumber,session):
        nonlocal lookup_count
        result = await original_lookup(requested_phone_number,session)
        lookup_results.append(result)
        lookup_count += 1
        if lookup_count == 2:
            both_lookups_finished.set()
        await both_lookups_finished.wait()
        return result
    
    monkeypatch.setattr(
        auth_service,
        "find_user_by_phone_number",
        synchronized_lookup,
    )

    async def signup(form_values:dict[str,Any]):
        # Her eşzamanlı servis çağrısı kendine ait bir DB session kullanır.
        async with test_session_factory() as db:
            form_data = Register_Request(**form_values)
            return await auth_service.register_user(
                form_data,
                db,
                BackgroundTasks(),
            )
    
    try:
        # Aynı telefon numarası için iki kayıt denemesini eşzamanlı çalıştır.
        results = await asyncio.gather(
            signup(attempts[0]),
            signup(attempts[1]),
            return_exceptions=True,
        )

        successes = [result for result in results if isinstance(result, dict)]
        errors = [result for result in results if isinstance(result, HTTPException)]

        # İki ön kontrol de kayıt öncesinde tamamlanıp kullanıcı bulamamış olmalı.
        assert lookup_count == 2, results
        assert lookup_results == [None, None]
        assert len(successes) == 1, results
        assert len(errors) == 1, results
        assert errors[0].status_code == 409
        assert errors[0].detail == "Bu telefon numarası zaten kullanımda."

        # gather sonuçları giriş sırasını korur; hata alan isteğin adını bul.
        failed_attempt = next(
            form_values
            for form_values, result in zip(attempts, results)
            if isinstance(result, HTTPException)
        )

        normalized_phone_number = Register_Request(**attempts[0]).phone_number 
        # Credential çakışmasından sonra DB'de yalnızca kazananın User ve credential'ı kalmalı.
        async with test_session_factory() as db:
            credential_count = await db.scalar(
                select(func.count())
                .select_from(User_Credential)
                .where(User_Credential.phone_number == normalized_phone_number)
            )
            attempt_user_count = await db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.name.in_(attempt_names))
            )
            failed_user_count = await db.scalar(
                select(func.count())
                .select_from(User)
                .where(User.name == failed_attempt["name"])
            )

        assert credential_count == 1
        assert attempt_user_count == 1
        assert failed_user_count == 0
    finally:
        # Başarılı kullanıcıyı ve olası orphan kaydı temizle; başka test verisine dokunma.
        async with test_session_factory.begin() as db:
            await db.execute(
                delete(User).
                where(User.name.in_(attempt_names))
            )
        
    