from typing import Any, Dict, Tuple

def build_user_query(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Build SQL query and parameters safely."""
    if not filters:
        return "SELECT * FROM users WHERE 1=1", {}

    clauses = [f"{k} = :{k}" for k in filters.keys()]
    where = " AND ".join(clauses)
    return f"SELECT * FROM users WHERE {where}", dict(filters)

