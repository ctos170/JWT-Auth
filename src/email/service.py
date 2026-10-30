from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType,NameEmail
from pydantic import EmailStr,SecretStr
from src.core.config import settings
from pathlib import Path




BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_FOLDER = BASE_DIR / "templates" 


conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=SecretStr(settings.MAIL_PASSWORD),
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM=settings.MAIL_FROM,
    USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)


async def send_email( 
    subject: str,
    email_to: list[EmailStr],
    template_name:str,
    template_body:dict
    ):
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[NameEmail(name=email,email=email) for email in email_to],
            template_body=template_body,
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        await fm.send_message(message,template_name=template_name)
    except Exception as e:
        print(f"Email gönderilirken hata oluştu: {e}")
        raise e           










