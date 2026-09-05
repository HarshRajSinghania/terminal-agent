from typing import Any, Dict, List

def paginate_users(all_users: List[Dict[str, Any]], limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """Return paginated slice of users."""
    # Starter incomplete stub
    return {
        "items": all_users,
        "total": len(all_users),
        "limit": limit,
        "offset": offset,
        "has_more": False
    }
