from __future__ import annotations


class AuditOutboxStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


AUDIT_OUTBOX_EVENT_TYPE = "AUDIT"

