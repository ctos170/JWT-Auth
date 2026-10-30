import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import delete, func, select

from src.auth import service as auth_service
from src.auth.schemas import Register_Request
from src.database.models.models import User, User_Credential


@pytest.mark.anyio
async def test_concurrent_signups_with_same_email_return_specific_conflict(
    test_session_factory, monkeypatch
):
    # Her çalıştırmada farklı e-posta kullanarak eski test verisiyle çakışmayı önle.
    email = f"signup-race-{uuid4().hex}@example.com"
    form_values = {
        "name": "Test",
        "surname": "User",
        "age": 25,
        "email": email,
        "phone_number": None,
        "password": "StrongPass123!",
    }

    # İki isteğin de e-posta kontrolünü kayıt yapılmadan önce tamamlamasını sağla.
    # İkisi de "kullanıcı yok" sonucunu alınca devam eder; çakışmayı UNIQUE index
    # belirler ve hata yönetimimiz bu ihlali özel 409 mesajına dönüştürür.
    original_lookup = auth_service.get_user_by_email_or_phone_number
    lookup_count = 0
    both_lookups_finished = asyncio.Event()

    async def synchronized_lookup(session, requested_email, phone_number=None):
        nonlocal lookup_count
        result = await original_lookup(session, requested_email, phone_number)
        lookup_count += 1
        if lookup_count == 2:
            both_lookups_finished.set()
        await both_lookups_finished.wait()
        return result

    monkeypatch.setattr(
        auth_service,
        "get_user_by_email_or_phone_number",
        synchronized_lookup,
    )

    async def signup():
        # Her eşzamanlı istek kendine ait bir veritabanı oturumu kullanır.
        async with test_session_factory() as db:
            form_data = Register_Request(**form_values)
            return await auth_service.register_user(form_data, db)

    try:
        # İki kayıt servisini eşzamanlı çalıştır; beklenen istisnaları sonuç olarak al.
        results = await asyncio.gather(
            signup(),
            signup(),
            return_exceptions=True,
        )

        successes = [result for result in results if isinstance(result, dict)]
        errors = [result for result in results if isinstance(result, HTTPException)]

        # İki kontrol de kayıt öncesinde tamamlanmış olmalı; böylece kaybeden istek
        # uygulama ön kontrolünden değil, veritabanındaki UNIQUE index'ten etkilenir.
        assert lookup_count == 2, results
        assert len(successes) == 1, results
        assert len(errors) == 1, results
        assert errors[0].status_code == 409
        assert errors[0].detail == "Bu e-posta adresi zaten kullanımda."
        # -s seçeneğiyle pytest çalıştırıldığında beklenen yanıtı terminalde göster.
        print(f"Beklenen çakışma yanıtı: HTTP {errors[0].status_code} - {errors[0].detail}")

        # Yanıtları kontrol etmenin yanında veritabanında tek kayıt kaldığını doğrula.
        async with test_session_factory() as db:
            saved_count = await db.scalar(
                select(func.count())
                .select_from(User_Credential)
                .where(User_Credential.email == email)
            )

        assert saved_count == 1
    finally:
        # Kayıt servisi commit ettiği için test verisini ayrıca temizle.
        async with test_session_factory() as db:
            user_id = await db.scalar(
                select(User_Credential.user_id)
                .where(User_Credential.email == email)
            )
            if user_id is not None:
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
