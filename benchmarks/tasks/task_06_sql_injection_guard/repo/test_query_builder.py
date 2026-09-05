from query_builder import build_user_query

def test_empty_filters():
    sql, params = build_user_query({})
    assert sql == "SELECT * FROM users WHERE 1=1"
    assert params == {}

def test_parameterized_query():
    sql, params = build_user_query({"role": "admin", "status": "active"})
    assert sql == "SELECT * FROM users WHERE role = :role AND status = :status"
    assert params == {"role": "admin", "status": "active"}

def test_sql_injection_defense():
    evil_input = "' OR '1'='1"
    sql, params = build_user_query({"username": evil_input})
    assert sql == "SELECT * FROM users WHERE username = :username"
    assert params["username"] == evil_input
    assert evil_input not in sql

