"""Deterministic relevance ranker for repository files and symbols."""

import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alpha-numeric keywords, splitting snake_case and camelCase."""
    # Split camelCase
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # Split snake_case and non-alphanumeric
    tokens = re.findall(r"[a-zA-Z0-9]+", s1.lower())
    # Filter short stopwords
    stopwords = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of", "is", "it", "this", "that"}
    return [t for t in tokens if len(t) > 1 and t not in stopwords]


class DeterministicRanker:
    """Ranks repository files based on task relevance using deterministic symbol and term scoring."""

    @staticmethod
    def score_file(
        file_path: Path,
        content: str,
        query_tokens: List[str],
        base_dir: Path
    ) -> Tuple[float, str]:
        """
        Compute deterministic relevance score for a file.
        Returns (score, summary_reason).
        """
        if not query_tokens:
            return 0.0, "No query tokens"

        rel_path = str(file_path.relative_to(base_dir)).replace("\\", "/")
        path_tokens = tokenize(rel_path)
        content_tokens = tokenize(content[:20000]) # First 20KB for fast scoring

        query_set = set(query_tokens)
        
        # 1. Path Match Score (High weight: 10x)
        path_matches = [t for t in path_tokens if t in query_set]
        path_score = len(path_matches) * 10.0

        # Exact filename match bonus
        for q in query_tokens:
            if q in file_path.name.lower():
                path_score += 15.0

        # 2. Symbol Definition Match (defs, classes, functions: 5x)
        symbol_score = 0.0
        symbol_matches = []
        for line in content.splitlines()[:500]:
            trimmed = line.strip()
            if trimmed.startswith(("def ", "class ", "function ", "type ", "interface ", "struct ", "pub fn ")):
                line_tokens = tokenize(trimmed)
                matches = [t for t in line_tokens if t in query_set]
                if matches:
                    symbol_score += len(matches) * 5.0
                    symbol_matches.extend(matches)

        # 3. Content Frequency (TF-IDF style term frequency: 1x)
        content_counter = Counter(content_tokens)
        content_score = sum(math.log(1 + content_counter[t]) for t in query_set if t in content_counter)

        # Penalize test files slightly for implementation queries unless query specifically asks for test
        is_test_query = any("test" in q for q in query_tokens)
        is_test_file = "test" in rel_path.lower()
        if is_test_file and not is_test_query:
            total_score = (path_score + symbol_score + content_score) * 0.6
        else:
            total_score = path_score + symbol_score + content_score

        reasons = []
        if path_matches:
            reasons.append(f"path matches [{', '.join(set(path_matches))}]")
        if symbol_matches:
            reasons.append(f"symbols [{', '.join(set(symbol_matches))}]")
        if content_score > 0:
            reasons.append(f"term frequency score {content_score:.1f}")

        reason_str = ", ".join(reasons) if reasons else "low keyword frequency"
        return round(total_score, 2), reason_str

