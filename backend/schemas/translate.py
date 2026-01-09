"""
Translation Request/Response Schemas
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TranslateRequest(BaseModel):
    """Translation request model"""
    content: str = Field(..., description="要翻译的内容")
    target_role: str = Field(..., description="目标角色（如：developer, product, ops, management）")
    source_role: Optional[str] = Field(None, description="源角色（可选，用于提供上下文）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "我们需要实现一个用户登录功能，支持手机号和邮箱登录。",
                "target_role": "developer",
                "source_role": "product"
            }
        }


class ThinkingStep(BaseModel):
    """Thinking step model"""
    type: str = Field(..., description="思考步骤类型")
    content: str = Field(..., description="思考内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    timestamp: str = Field(..., description="时间戳")


class ConfirmationRequest(BaseModel):
    """Confirmation request model"""
    request_id: str = Field(..., description="请求ID")
    question: str = Field(..., description="确认问题")
    options: Optional[Dict[str, Any]] = Field(None, description="选项")
    timeout: float = Field(30.0, description="超时时间（秒）")
    status: str = Field("pending", description="状态")
    created_at: str = Field(..., description="创建时间")


class TranslateResponse(BaseModel):
    """Translation response model"""
    translated_content: str = Field(..., description="翻译后的内容（Markdown 格式）")
    role_analysis: Optional[Dict] = Field(None, description="角色分析结果")
    uncertainties: List[str] = Field(default_factory=list, description="不确定性问题列表")
    thinking_process: Optional[Dict] = Field(None, description="思考过程")
    
    class Config:
        json_schema_extra = {
            "example": {
                "translated_content": "## 一、需求理解\n...",
                "role_analysis": {
                    "role_name": "developer",
                    "normalized_role": "developer",
                    "is_predefined": True
                },
                "uncertainties": [],
                "thinking_process": {
                    "steps": []
                }
            }
        }


class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str = Field(..., description="消息类型")
    data: Dict[str, Any] = Field(..., description="消息数据")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "type": "thinking",
                    "data": {
                        "type": "think",
                        "content": "正在分析角色...",
                        "timestamp": "2024-01-01T00:00:00"
                    }
                },
                {
                    "type": "confirmation_request",
                    "data": {
                        "request_id": "confirm_1",
                        "question": "请确认...",
                        "timeout": 30.0
                    }
                }
            ]
        }

