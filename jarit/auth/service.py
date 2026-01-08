from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from sqlalchemy import func
from jarit.core.security import get_password_hash, verify_password
from ..db.models.users import User, UserRole
from .schemas import UserCreate
import os

ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION")


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user: UserCreate, current_user: User | None = None):
    count = user_count(db)
    print(f"User count: {count}")
    if count == 0:
        db_role = UserRole.ADMIN

    elif ALLOW_REGISTRATION == "true":
        if current_user and current_user.role == UserRole.ADMIN:
            db_role = UserRole(user.role)
        else:
            db_role = UserRole.USER


    elif current_user and current_user.role == UserRole.ADMIN:
        db_role = UserRole(user.role)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Registration is disabled. Admin privileges required to create new users.",
            )
    
    # Check if user exists
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        role=db_role.value,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def user_count(db: Session) -> int:
    return db.query(func.count(User.id)).scalar()
