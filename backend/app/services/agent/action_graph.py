import logging
from typing import List
from core.config import default_config
from .schemas import (
   TaskStatus
)
from .utils import CodeExecutor, ExecuteResult

OPENAI_API_KEY = default_config.OPENAI_API_KEY

logger = logging.getLogger(default_config.SESS_LOG_NAME)

class ActionNode:
    """Represents a single executable code snippet within a task."""
    def __init__(self, action_id: int, code: str, description: str):
        """Initialize an action with its identifier, runnable code, and description."""
        self.action_id = action_id
        self.description = description
        self.code = code
        self.status = TaskStatus.PENDING

    def to_dict(self) -> dict:
        """Serialize the action node for persistence or logging."""
        return {
            "action_id": self.action_id,
            "code": self.code,
            "description": self.description,
            "status": self.status.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Rebuild an ActionNode instance from serialized data."""
        node = cls(
            action_id=data["action_id"],
            code=data["code"],
            description=data["description"]
        )
        node.status = TaskStatus(data["status"])
        return node

    def __repr__(self):
        """Return a concise debug string showing id, status, and code preview."""
        return f"ActionNode(id={self.action_id}, description='{self.description}', status='{self.status.value}', code='{self.code[:default_config.LOG_PREVIEW_LENGTH]}...')"

class ActionGraph:
    """Manages the sequence of actions for a single parent task."""
    def __init__(self):
        """Manage an ordered collection of actions and their execution result."""
        self.nodes: List[ActionNode] = []
        self.result: ExecuteResult | None = None

    def to_dict(self) -> dict:
        """Serialize the graph nodes and last execution summary."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "result_summary": self.result.message if self.result else None,
            "result_success": self.result.success if self.result else None
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Restore an ActionGraph from serialized node data."""
        graph = cls()
        for node_data in data.get("nodes", []):
            graph.add_action(ActionNode.from_dict(node_data))
        
        # We don't fully reconstruct self.result object here as it's transient,
        # but we restored the nodes' status which is what matters for history.
        return graph

    def add_action(self, node: ActionNode):
        """Add an action node and keep nodes sorted by action_id."""
        self.nodes.append(node)
        self.nodes.sort(key=lambda n: n.action_id)
        
    def __repr__(self):
        return f"ActionGraph with {len(self.nodes)} actions."
    
    def execute_action_graph(self, namespace: dict):
        """Execute actions sequentially in the given namespace and record status."""
        executor = CodeExecutor(namespace=namespace)
        last_message = ''
        lean_namespace = {
            default_config.KEY_AGENT_STATE: executor.namespace.get(default_config.KEY_AGENT_STATE, 'Agent state not found')
        }
        for current_action_node in self.nodes:
            exec_success, result = executor.execute(current_action_node.code)
            if not exec_success:
                current_action_node.status = TaskStatus.FAILED
                self.result = ExecuteResult(success=False, message=result, namespace=lean_namespace)
                return
            current_action_node.status = TaskStatus.SUCCESS
            last_message = result
        
        self.result = ExecuteResult(success=True, message=last_message, namespace=lean_namespace)

    #! Deprecated
    def print_actions(self):
        """Deprecated: print action details for manual debugging."""
        for action in self.nodes:
            print(f"  - ID: {action.action_id}")
            print(f"    Description: {action.description}")
            print(f"    Code: {action.code}")
            print("--------------------")