"""Seed the configured database with a demo agent, customer, and tickets."""
from app.core.database import SessionLocal, Base, engine
import app.models  # noqa: F401
from app.repositories.user_repo import UserRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.auth_service import AuthService
from app.services.ticket_service import TicketService
from app.ai.rule_based import RuleBasedProvider
from app.models.enums import Role


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        auth = AuthService(UserRepository(db))
        for email, name, role in [
            ("agent@demo.com", "Demo Agent", Role.agent),
            ("customer@demo.com", "Demo Customer", Role.customer),
        ]:
            if not UserRepository(db).get_by_email(email):
                auth.register(email, "password123", name, role)
        customer = UserRepository(db).get_by_email("customer@demo.com")
        svc = TicketService(TicketRepository(db), ActivityRepository(db),
                            UserRepository(db), RuleBasedProvider())
        for title, desc in [
            ("Double charged on invoice", "I was billed twice this month, need a refund."),
            ("Cannot log in", "Forgot password and locked out of my account."),
            ("App crashes on upload", "The app crashes every time I upload a file. Urgent."),
        ]:
            svc.create_ticket(customer, title, desc)
        print("Seed complete. Login: agent@demo.com / customer@demo.com (password123)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
