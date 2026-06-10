from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.enums import Role


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list_agents(self) -> list[User]:
        return list(self.db.scalars(select(User).where(User.role == Role.agent)))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
