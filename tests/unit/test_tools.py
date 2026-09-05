"""Unit tests for tool system and tool registry dispatch."""

from pathlib import Path
from terminal_agent.tools.registry import ToolRegistry


def test_tool_registry_and_file_tools(tmp_path: Path):
    registry = ToolRegistry(working_dir=tmp_path)
    assert len(registry.list_tool_names()) >= 12

    # 1. Write file tool
    write_res = registry.execute(
        "write_file",
        {"path": "calculator.py", "content": "def add(a, b):\n    return a - b\n", "reason": "Initial bugged implementation"}
    )
    assert write_res.success is True
    assert (tmp_path / "calculator.py").exists()

    # 2. Read file tool
    read_res = registry.execute(
        "read_file",
        {"path": "calculator.py", "reason": "Inspect calculator"}
    )
    assert read_res.success is True
    assert "return a - b" in read_res.output

    # 3. Edit file tool
    edit_res = registry.execute(
        "edit_file",
        {
            "path": "calculator.py",
            "old_str": "return a - b",
            "new_str": "return a + b",
            "reason": "Fix addition operator"
        }
    )
    assert edit_res.success is True
    assert "return a + b" in (tmp_path / "calculator.py").read_text()

    # 4. Search files tool
    search_res = registry.execute(
        "search_files",
        {"query": "def add", "reason": "Find add function"}
    )
    assert search_res.success is True
    assert "calculator.py" in search_res.output

    # 5. List files tool
    list_res = registry.execute(
        "list_files",
        {"directory": ".", "reason": "List project root"}
    )
    assert list_res.success is True
    assert "calculator.py" in list_res.output


def test_command_tool(tmp_path: Path):
    registry = ToolRegistry(working_dir=tmp_path)
    cmd_res = registry.execute(
        "run_command",
        {"command": "python -c \"print('agent test run')\"", "reason": "Sanity check"}
    )
    assert cmd_res.success is True
    assert "agent test run" in cmd_res.output
