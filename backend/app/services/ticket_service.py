from app.ai.base import TriageProvider
from app.models.ticket import Ticket
from app.models.user import User
from app.models.enums import Role, Status, EventType
from app.repositories.ticket_repo import TicketRepository
from app.repositories.activity_repo import ActivityRepository
from app.repositories.user_repo import UserRepository
from app.services.exceptions import ForbiddenError, NotFoundError


class TicketService:
    def __init__(
        self,
        tickets: TicketRepository,
        activity: ActivityRepository,
        users: UserRepository,
        triage: TriageProvider,
    ):
        self.tickets = tickets
        self.activity = activity
        self.users = users
        self.triage = triage

    def create_ticket(self, creator: User, title: str, description: str) -> Ticket:
        result = self.triage.triage(title, description)
        ticket = Ticket(
            title=title,
            description=description,
            status=Status.open,
            priority=result.priority,
            category=result.category,
            suggested_response=result.suggested_response,
            created_by_id=creator.id,
        )
        ticket = self.tickets.create(ticket)
        self.activity.log(
            ticket_id=ticket.id, actor_id=creator.id, event_type=EventType.created
        )
        return ticket

    def get_ticket(self, user: User, ticket_id: int) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        self._assert_can_view(user, ticket)
        return ticket

    def list_tickets(self, user: User, **filters) -> tuple[list[Ticket], int]:
        # Customers are scoped to their own tickets.
        if user.role == Role.customer:
            filters["owner_id"] = user.id
        return self.tickets.search(**filters)

    def update_ticket(self, user: User, ticket_id: int, changes: dict) -> Ticket:
        ticket = self.tickets.get(ticket_id)
        if not ticket:
            raise NotFoundError("Ticket not found")
        # `changes` only contains fields the client explicitly set (exclude_unset).
        # Any mutation attempt by a non-agent is forbidden.
        if changes and user.role != Role.agent:
            raise ForbiddenError("Only agents can update tickets")

        if changes.get("status") is not None and changes["status"] != ticket.status:
            old = ticket.status.value
            ticket.status = changes["status"]
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.status_changed,
                              old_value=old, new_value=ticket.status.value)
        if changes.get("priority") is not None and changes["priority"] != ticket.priority:
            old = ticket.priority.value
            ticket.priority = changes["priority"]
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.priority_changed,
                              old_value=old, new_value=ticket.priority.value)
        if changes.get("category") is not None and changes["category"] != ticket.category:
            old = ticket.category.value
            ticket.category = changes["category"]
            self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                              event_type=EventType.category_changed,
                              old_value=old, new_value=ticket.category.value)
        # `assigned_to_id` present with value None means "unassign".
        if "assigned_to_id" in changes and changes["assigned_to_id"] != ticket.assigned_to_id:
            new_assignee_id = changes["assigned_to_id"]
            if new_assignee_id is None:
                ticket.assigned_to_id = None
                self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                                  event_type=EventType.assigned, new_value="Unassigned")
            else:
                assignee = self.users.get(new_assignee_id)
                if not assignee or assignee.role != Role.agent:
                    raise NotFoundError("Assignee must be an existing agent")
                ticket.assigned_to_id = assignee.id
                self.activity.log(ticket_id=ticket.id, actor_id=user.id,
                                  event_type=EventType.assigned,
                                  new_value=assignee.full_name)
        return self.tickets.save(ticket)

    def _assert_can_view(self, user: User, ticket: Ticket) -> None:
        if user.role == Role.agent:
            return
        if ticket.created_by_id != user.id:
            raise ForbiddenError("You can only view your own tickets")
