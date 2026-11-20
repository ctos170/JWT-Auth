from fastapi import FastAPI
from slowapi import  _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.core.limiter import limiter


app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore

from src.auth.router import router as auth_router
from src.users.router import router as users_router


app.include_router(auth_router,prefix="/api/auth",tags=["Auth enpointleri"])
app.include_router(users_router,prefix="/api/users",tags=["Kullanıcı enpointleri"])