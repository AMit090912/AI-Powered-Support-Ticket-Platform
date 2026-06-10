import enum


class Role(str, enum.Enum):
    customer = "customer"
    agent = "agent"


class Status(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"


class Priority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Category(str, enum.Enum):
    billing = "billing"
    technical = "technical"
    account_access = "account_access"
    feature_request = "feature_request"
    general = "general"


class EventType(str, enum.Enum):
    created = "created"
    status_changed = "status_changed"
    assigned = "assigned"
    priority_changed = "priority_changed"
    category_changed = "category_changed"
    commented = "commented"
