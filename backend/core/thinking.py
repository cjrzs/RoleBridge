"""
Thinking Process Management - Manages Agent's thinking process
"""
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class ThinkingStepType(str, Enum):
    """Types of thinking steps"""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    CONFIRM = "confirm"
    DECISION = "decision"


class ThinkingStep:
    """
    Represents a single thinking step
    """
    
    def __init__(
        self,
        step_type: ThinkingStepType,
        content: str,
        metadata: Optional[Dict] = None
    ):
        self.step_type = step_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "type": self.step_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class ThinkingProcess:
    """
    Manages the Agent's thinking process
    """
    
    def __init__(self):
        self.steps: List[ThinkingStep] = []
        self.current_step: Optional[ThinkingStep] = None
    
    def add_step(
        self,
        step_type: ThinkingStepType,
        content: str,
        metadata: Optional[Dict] = None
    ) -> ThinkingStep:
        """
        Add a new thinking step
        
        Args:
            step_type: Type of the step
            content: Content of the step
            metadata: Optional metadata
            
        Returns:
            Created thinking step
        """
        step = ThinkingStep(step_type, content, metadata)
        self.steps.append(step)
        self.current_step = step
        return step
    
    def format_for_display(self) -> str:
        """
        Format thinking process for display
        
        Returns:
            Formatted string
        """
        lines = []
        for i, step in enumerate(self.steps, 1):
            step_type_name = {
                ThinkingStepType.THINK: "💭 思考",
                ThinkingStepType.ACT: "⚡ 行动",
                ThinkingStepType.OBSERVE: "👀 观察",
                ThinkingStepType.CONFIRM: "❓ 确认",
                ThinkingStepType.DECISION: "✅ 决策"
            }.get(step.step_type, step.step_type.value)
            
            lines.append(f"### 步骤 {i}: {step_type_name}")
            lines.append(step.content)
            if step.metadata:
                lines.append(f"\n*元数据: {step.metadata}*")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_latest_steps(self, count: int = 5) -> List[ThinkingStep]:
        """
        Get latest N thinking steps
        
        Args:
            count: Number of steps to return
            
        Returns:
            List of thinking steps
        """
        return self.steps[-count:] if len(self.steps) > count else self.steps
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step.to_dict() if self.current_step else None
        }

