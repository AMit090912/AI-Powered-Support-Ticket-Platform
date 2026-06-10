from app.core import security
from app.models.user import User
from app.models.enums import Role
from app.repositories.user_repo import UserRepository
from app.services.exceptions import ConflictError, NotFoundError


class AuthService:
    def __init__(self, users: UserRepository):
        self.users = users

    def register(self, email: str, password: str, full_name: str, role: Role) -> User:
        if self.users.get_by_email(email):
            raise ConflictError("Email already registered")
        user = User(
            email=email,
            hashed_password=security.hash_password(password),
            full_name=full_name,
            role=role,
        )
        return self.users.create(user)

    def authenticate(self, email: str, password: str) -> User:
        user = self.users.get_by_email(email)
        if not user or not security.verify_password(password, user.hashed_password):
            raise NotFoundError("Invalid email or password")
        return user

    def issue_token(self, user: User) -> str:
        return security.create_access_token({"sub": str(user.id), "role": user.role.value})
