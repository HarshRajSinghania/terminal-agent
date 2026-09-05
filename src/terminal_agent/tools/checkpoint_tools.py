"""Checkpoint creation and rollback tools."""

from typing import Any, Dict
from terminal_agent.checkpoints.manager import CheckpointManager
from terminal_agent.tools.base import BaseTool, ToolResult


class CreateCheckpointTool(BaseTool):
    name = "create_checkpoint"
    description = "Create a snapshot checkpoint before making major or risky modifications. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Descriptive name for the checkpoint"},
            "reason": {"type": "string", "description": "Explainability reason for creating checkpoint"}
        },
        "required": ["name", "reason"]
    }

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        name = args.get("name", "checkpoint")
        snapshot = self.checkpoint_manager.create_checkpoint(name=name)

        return ToolResult(
            success=True,
            output=f"Created checkpoint '{snapshot.checkpoint_id}' ('{name}') with {len(snapshot.modified_files)} files.",
            data={
                "checkpoint_id": snapshot.checkpoint_id,
                "name": snapshot.name,
                "files_count": len(snapshot.modified_files)
            },
            reason=reason
        )


class RestoreCheckpointTool(BaseTool):
    name = "restore_checkpoint"
    description = "Roll back repository state to a previous checkpoint. Requires a reason."
    parameters_schema = {
        "type": "object",
        "properties": {
            "checkpoint_id": {"type": "string", "description": "The checkpoint ID or name to restore"},
            "reason": {"type": "string", "description": "Explainability reason for rolling back"}
        },
        "required": ["checkpoint_id", "reason"]
    }

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.checkpoint_manager = checkpoint_manager

    def run(self, args: Dict[str, Any], reason: str = "") -> ToolResult:
        checkpoint_id = args.get("checkpoint_id", "")
        success = self.checkpoint_manager.rollback(checkpoint_id)

        if success:
            return ToolResult(
                success=True,
                output=f"Successfully restored repository state from checkpoint '{checkpoint_id}'.",
                data={"checkpoint_id": checkpoint_id},
                reason=reason
            )
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Checkpoint '{checkpoint_id}' not found or restore failed.",
                reason=reason
            )
