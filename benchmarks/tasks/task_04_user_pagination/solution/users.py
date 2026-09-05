from typing import Any, Dict, List

def paginate_users(all_users: List[Dict[str, Any]], limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """Return paginated slice of users."""
    total = len(all_users)
    items = all_users[offset : offset + limit]
    has_more = (offset + limit) < total
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more
    }

