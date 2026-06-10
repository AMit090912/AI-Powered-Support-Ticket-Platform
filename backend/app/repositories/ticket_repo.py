from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.enums import Status, Priority, Category


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, ticket_id: int) -> Ticket | None:
        return self.db.get(Ticket, ticket_id)

    def create(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def save(self, ticket: Ticket) -> Ticket:
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def search(
        self,
        *,
        owner_id: int | None = None,
        q: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        category: Category | None = None,
        assignee_id: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Ticket], int]:
        stmt = select(Ticket)
        if owner_id is not None:
            stmt = stmt.where(Ticket.created_by_id == owner_id)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))
        if status is not None:
            stmt = stmt.where(Ticket.status == status)
        if priority is not None:
            stmt = stmt.where(Ticket.priority == priority)
        if category is not None:
            stmt = stmt.where(Ticket.category == category)
        if assignee_id is not None:
            stmt = stmt.where(Ticket.assigned_to_id == assignee_id)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = self.db.scalars(
            stmt.order_by(Ticket.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)
