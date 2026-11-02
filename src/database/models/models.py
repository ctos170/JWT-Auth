import uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship,DeclarativeBase
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, UUID,CheckConstraint
from datetime import datetime, timezone
from typing import Optional, List

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "age >= 18 AND age < 80",
            name="check_user_age"
        ),
        )

    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    name : Mapped[str] = mapped_column(String(150))
    surname : Mapped[str] = mapped_column(String(175))
    age: Mapped[int] = mapped_column(Integer)
    is_active : Mapped[bool] = mapped_column(Boolean,default=True)

    created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
        )
    
    updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ) 

    credential: Mapped["User_Credential"] = relationship(uselist=False, back_populates="user", cascade="all, delete-orphan")
    sessions : Mapped[List["Session"]] = relationship(back_populates="user",cascade="all, delete-orphan")
    password_reset_tokens : Mapped[List["Password_Reset_Token"]] = relationship(back_populates="user",cascade="all, delete-orphan")
    

class User_Credential(Base):
    __tablename__ = "user_credentials"
    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id : Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id",ondelete="CASCADE"),
        unique=True
    )
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    phone_number : Mapped[Optional[str]] = mapped_column(String(200),unique=True,index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    user : Mapped["User"] = relationship(back_populates="credential") 


class Password_Reset_Token(Base):
    __tablename__ = "password_reset_tokens"
    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("users.id",ondelete="CASCADE"),index=True)
    token_hash : Mapped[str] = mapped_column(String(255),unique=True)
    expires_at : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user : Mapped["User"] = relationship(back_populates="password_reset_tokens")


class Session(Base):
    __tablename__ = "user_sessions"
    id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    user_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("users.id",ondelete="CASCADE"))
    refresh_token_jti : Mapped[str] = mapped_column(String(255),unique=True,index=True)
    device_info : Mapped[str] = mapped_column(String(255))
    ip_address : Mapped[str] = mapped_column(String(255))
    is_revoked : Mapped[bool] = mapped_column(Boolean,default=False)
    expires_at : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    created_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),
    )
   
    updated_at: Mapped[datetime] = mapped_column(
                DateTime(timezone=True),
                default=lambda: datetime.now(timezone.utc),
                onupdate=lambda: datetime.now(timezone.utc),
    ) 

    user : Mapped["User"] = relationship(back_populates="sessions") 
    session_jtis : Mapped[List["Session_Token_Jtis"]] = relationship(back_populates="session",cascade="all, delete-orphan")


class Token_Blacklist(Base):
    __tablename__ = "token_blacklist"  
    jti : Mapped[str] = mapped_column(String(255),primary_key=True)
    revoked_at : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at : Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Session_Token_Jtis(Base):
    __tablename__= "session_token_jtis"

    jti : Mapped[str] = mapped_column(String(255),primary_key=True)
    session_id:Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_sessions.id",ondelete="CASCADE")
        )
    token_type:Mapped[str] = mapped_column(String(50))
    expires_at:Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at:Mapped[Optional[datetime]]= mapped_column(DateTime(timezone=True))
    revoked_at:Mapped[Optional[datetime]]= mapped_column(DateTime(timezone=True))

    session:Mapped["Session"] = relationship(back_populates="session_jtis")