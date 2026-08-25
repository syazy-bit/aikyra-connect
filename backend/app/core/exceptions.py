"""Application-level exceptions mapped to HTTP responses in main.py."""


class NotFoundError(Exception):
    """Requested resource does not exist."""

    def __init__(self, entity: str, entity_id: object) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(f"{entity} with id '{entity_id}' not found")
