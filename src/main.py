from fastapi import FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore

from src.auth.router import router as auth_router
from src.users.router import router as users_router


app.include_router(auth_router,prefix="/api/auth",tags=["Auth enpointleri"])
app.include_router(users_router,prefix="/api/users",tags=["Kullanıcı enpointleri"])