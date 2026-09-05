from csv_stream import parse_csv_chunks

def test_parse_chunks():
    sample_csv = "id,name,age\n1,Alice,30\n2,Bob,25\n3,Carol,28\n4,Dave,35\n5,Eve,22\n"
    chunks = list(parse_csv_chunks(sample_csv, chunk_size=2))

    assert len(chunks) == 3
    assert len(chunks[0]) == 2
    assert chunks[0][0] == {"id": "1", "name": "Alice", "age": "30"}
    assert chunks[0][1] == {"id": "2", "name": "Bob", "age": "25"}

    assert len(chunks[1]) == 2
    assert chunks[1][0]["name"] == "Carol"
    assert chunks[1][1]["name"] == "Dave"

    assert len(chunks[2]) == 1
    assert chunks[2][0]["name"] == "Eve"

def test_empty_csv():
    chunks = list(parse_csv_chunks("", chunk_size=5))
    assert chunks == []
