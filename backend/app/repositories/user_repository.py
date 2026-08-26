from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Database access for users.

    Performs operations on the session only — never commits. Transaction
    boundaries are owned by the service layer.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: dict) -> User:
        user = User(**data)
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        ).scalar_one_or_none()

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)
