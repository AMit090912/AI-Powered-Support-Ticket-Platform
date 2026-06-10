from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import ActivityEvent
from app.models.enums import EventType


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        *,
        ticket_id: int,
        actor_id: int | None,
        event_type: EventType,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            ticket_id=ticket_id,
            actor_id=actor_id,
            event_type=event_type,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_for_ticket(self, ticket_id: int) -> list[ActivityEvent]:
        return list(
            self.db.scalars(
                select(ActivityEvent)
                .where(ActivityEvent.ticket_id == ticket_id)
                .order_by(ActivityEvent.created_at)
            )
        )
