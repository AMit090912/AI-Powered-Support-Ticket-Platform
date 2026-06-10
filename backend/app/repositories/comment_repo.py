from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, comment: Comment) -> Comment:
        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        return comment

    def list_for_ticket(self, ticket_id: int) -> list[Comment]:
        return list(
            self.db.scalars(
                select(Comment).where(Comment.ticket_id == ticket_id).order_by(Comment.created_at)
            )
        )
