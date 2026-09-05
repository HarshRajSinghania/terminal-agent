"""Test output parsers for extracting structured test results."""

import re
from dataclasses import dataclass
from typing import Tuple


@dataclass
class ParsedSummary:
    passed: int
    failed: int
    errors: int
    skipped: int
    total: int


class TestOutputParser:
    """Parses standard test runners output (pytest, unittest, etc.)."""

    @classmethod
    def parse(cls, output: str, exit_code: int) -> ParsedSummary:
        """Extract passed/failed/error counts from output."""
        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Check pytest summary line: e.g. "== 5 passed, 1 failed in 0.12s =="
        pytest_match = re.search(r"=+\s*(.*?)\s+in\s+[\d\.]+s\s*=+", output)
        if pytest_match:
            summary_str = pytest_match.group(1)
            p_match = re.search(r"(\d+)\s+passed", summary_str)
            if p_match:
                passed = int(p_match.group(1))

            f_match = re.search(r"(\d+)\s+failed", summary_str)
            if f_match:
                failed = int(f_match.group(1))

            e_match = re.search(r"(\d+)\s+error", summary_str)
            if e_match:
                errors = int(e_match.group(1))

            s_match = re.search(r"(\d+)\s+skipped", summary_str)
            if s_match:
                skipped = int(s_match.group(1))

            total = passed + failed + errors + skipped
            return ParsedSummary(passed=passed, failed=failed, errors=errors, skipped=skipped, total=total)

        # Check unittest style: "Ran 5 tests in 0.001s\n\nOK"
        unittest_ran = re.search(r"Ran\s+(\d+)\s+tests?", output)
        if unittest_ran:
            total_ran = int(unittest_ran.group(1))
            if "OK" in output and exit_code == 0:
                return ParsedSummary(passed=total_ran, failed=0, errors=0, skipped=0, total=total_ran)
            
            f_match = re.search(r"failures=(\d+)", output)
            if f_match:
                failed = int(f_match.group(1))
            e_match = re.search(r"errors=(\d+)", output)
            if e_match:
                errors = int(e_match.group(1))
            
            passed = max(0, total_ran - failed - errors)
            return ParsedSummary(passed=passed, failed=failed, errors=errors, skipped=0, total=total_ran)

        # Fallback heuristics based on exit code
        if exit_code == 0:
            return ParsedSummary(passed=1, failed=0, errors=0, skipped=0, total=1)
        else:
            return ParsedSummary(passed=0, failed=1, errors=0, skipped=0, total=1)
