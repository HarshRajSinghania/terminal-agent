import csv
import io
from typing import Dict, Iterator, List

def parse_csv_chunks(csv_text: str, chunk_size: int = 2) -> Iterator[List[Dict[str, str]]]:
    """Parse CSV string into chunked batches of dictionary records."""
    if not csv_text or not csv_text.strip():
        return

    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    current_chunk: List[Dict[str, str]] = []

    for row in reader:
        current_chunk.append(dict(row))
        if len(current_chunk) >= chunk_size:
            yield current_chunk
            current_chunk = []

    if current_chunk:
        yield current_chunk

