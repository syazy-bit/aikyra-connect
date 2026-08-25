"""Application-level exceptions mapped to HTTP responses in main.py."""


class NotFoundError(Exception):
    """Requested resource does not exist."""

    def __init__(self, entity: str, entity_id: object) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id '{entity_id}' not found")


class ConflictError(Exception):
    """Operation conflicts with current protected state (e.g., validated data)."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
