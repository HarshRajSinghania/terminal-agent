"""Unit tests for validation benchmarks and AgentBench report compatibility."""

from pathlib import Path
from benchmarks.runner import BenchmarkRunner


def test_benchmark_task_discovery():
    runner = BenchmarkRunner()
    tasks = runner.list_tasks()
    assert len(tasks) == 10, f"Expected 10 benchmark tasks, discovered {len(tasks)}"


def test_benchmark_evaluation_suite(tmp_path: Path):
    runner = BenchmarkRunner(output_dir=tmp_path)
    report = runner.run_all(temp_base=tmp_path)

    assert report["total_tasks"] == 10
    assert report["passed_tasks"] == 10
    assert report["failed_tasks"] == 0
    assert report["pass_rate_percent"] == 100.0

    # Verify AgentBench schema compatibility
    for run in report["runs"]:
        assert "session_id" in run
        assert "task" in run
        assert "task_id" in run
        assert "category" in run
        assert run["status"] == "VERIFIED"
        assert run["tests_passed"] > 0
        assert run["tests_failed"] == 0
        assert "duration_ms" in run

