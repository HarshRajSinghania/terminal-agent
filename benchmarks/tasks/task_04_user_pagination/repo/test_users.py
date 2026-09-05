from users import paginate_users

def test_pagination_page_1():
    users = [{"id": i, "name": f"User {i}"} for i in range(25)]
    res = paginate_users(users, limit=10, offset=0)
    assert len(res["items"]) == 10
    assert res["items"][0]["id"] == 0
    assert res["items"][9]["id"] == 9
    assert res["total"] == 25
    assert res["has_more"] is True

def test_pagination_last_page():
    users = [{"id": i, "name": f"User {i}"} for i in range(25)]
    res = paginate_users(users, limit=10, offset=20)
    assert len(res["items"]) == 5
    assert res["items"][0]["id"] == 20
    assert res["items"][4]["id"] == 24
    assert res["total"] == 25
    assert res["has_more"] is False

def test_pagination_empty():
    res = paginate_users([], limit=10, offset=0)
    assert res["items"] == []
    assert res["total"] == 0
    assert res["has_more"] is False

