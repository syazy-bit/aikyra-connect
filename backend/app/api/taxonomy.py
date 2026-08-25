from fastapi import APIRouter

from app.core import taxonomy
from app.models.problem_dna import UrgencyLevel

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])


@router.get("")
def get_taxonomy():
    """Public taxonomy — the single source of truth for discovery filters.

    Frontends must never hardcode domains; new domains appear here first.
    """
    return {
        "domains": [
            {
                "key": domain.key,
                "label": domain.label,
                "subdomains": [sub.name for sub in domain.subdomains],
            }
            for domain in taxonomy.all_domains()
        ],
        "urgency_levels": [level.value for level in UrgencyLevel],
    }
