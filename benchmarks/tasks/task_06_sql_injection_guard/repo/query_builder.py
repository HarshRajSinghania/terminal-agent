from typing import Any, Dict, Tuple

def build_user_query(filters: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Build SQL query and parameters safely."""
    # BUG: insecure string formatting
    clauses = [f"{k} = '{v}'" for k, v in filters.items()]
    where = " AND ".join(clauses) if clauses else "1=1"
    return f"SELECT * FROM users WHERE {where}", {}
