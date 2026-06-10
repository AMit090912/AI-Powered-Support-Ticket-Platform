from app.models.comment import Comment
from app.models.user import User
from app.models.enums import Role, EventType
from app.repositories.ticket_repo import TicketRepository
from app.repositories.comment_repo import CommentRepository
from app.repositories.activity_repo import ActivityRepository
from app.services.exceptions import ForbiddenError, NotFoundError


class CommentService:
    def __init__(
        self,
        tickets: TicketRepository,
        comments: CommentRepository,
        activity: ActivityRepository,
    ):
        self.tickets = tickets
        self.comments = comments
        self.activity = activity

    def add_comment(self, user: User, ticket_id: int, body: str) -> Comment:
        ticket = self._get_accessible(user, ticket_id)
        comment = self.comments.create(
            Comment(ticket_id=ticket.id, author_id=user.id, body=body)
        )
        self.activity.log(
            ticket_id=ticket.id, actor_id=user.id, event_type=EventType.commented
        )
        return comment

    def list_comments(self, user: User, ticket_id: int) -> list[Comment]:
        self._get_accessible(user, ticket_id)
        return self.comments.list_for_ticket(ticket_id)

    def _get_accessible(self, user: User, ticket_id: int):
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        if user.role != Role.agent and ticket.created_by_id != user.id:
            raise ForbiddenError("You can only access your own tickets")
        return ticket
