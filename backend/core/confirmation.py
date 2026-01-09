"""
Confirmation Management - Manages user confirmation requests
"""
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import asyncio


class ConfirmationStatus(str, Enum):
    """Status of confirmation request"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ConfirmationRequest:
    """
    Represents a user confirmation request
    """
    
    def __init__(
        self,
        request_id: str,
        question: str,
        options: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ):
        self.request_id = request_id
        self.question = question
        self.options = options or {}
        self.timeout = timeout
        self.status = ConfirmationStatus.PENDING
        self.response: Optional[Any] = None
        self.created_at = datetime.now()
        self._event = asyncio.Event()
    
    async def wait_for_response(self) -> Any:
        """
        Wait for user response
        
        Returns:
            User response or None if timeout
        """
        try:
            await asyncio.wait_for(self._event.wait(), timeout=self.timeout)
            return self.response
        except asyncio.TimeoutError:
            self.status = ConfirmationStatus.TIMEOUT
            return None
    
    def set_response(self, response: Any):
        """
        Set user response
        
        Args:
            response: User response
        """
        self.response = response
        self.status = ConfirmationStatus.CONFIRMED
        self._event.set()
    
    def reject(self):
        """Reject the confirmation request"""
        self.status = ConfirmationStatus.REJECTED
        self._event.set()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "request_id": self.request_id,
            "question": self.question,
            "options": self.options,
            "status": self.status.value,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat()
        }


class ConfirmationManager:
    """
    Manages confirmation requests
    """
    
    def __init__(self):
        self.requests: Dict[str, ConfirmationRequest] = {}
        self._request_counter = 0
    
    def create_request(
        self,
        question: str,
        options: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> ConfirmationRequest:
        """
        Create a new confirmation request
        
        Args:
            question: Question to ask user
            options: Optional options/choices
            timeout: Timeout in seconds
            
        Returns:
            Confirmation request
        """
        self._request_counter += 1
        request_id = f"confirm_{self._request_counter}"
        
        request = ConfirmationRequest(request_id, question, options, timeout)
        self.requests[request_id] = request
        
        return request
    
    def get_request(self, request_id: str) -> Optional[ConfirmationRequest]:
        """
        Get confirmation request by ID
        
        Args:
            request_id: Request ID
            
        Returns:
            Confirmation request or None
        """
        return self.requests.get(request_id)
    
    def respond_to_request(self, request_id: str, response: Any) -> bool:
        """
        Respond to a confirmation request
        
        Args:
            request_id: Request ID
            response: User response
            
        Returns:
            True if request found and responded, False otherwise
        """
        request = self.requests.get(request_id)
        if request:
            request.set_response(response)
            return True
        return False
    
    def reject_request(self, request_id: str) -> bool:
        """
        Reject a confirmation request
        
        Args:
            request_id: Request ID
            
        Returns:
            True if request found and rejected, False otherwise
        """
        request = self.requests.get(request_id)
        if request:
            request.reject()
            return True
        return False
    
    def cleanup_old_requests(self, max_age_seconds: int = 300):
        """
        Clean up old confirmation requests
        
        Args:
            max_age_seconds: Maximum age in seconds
        """
        now = datetime.now()
        to_remove = []
        
        for request_id, request in self.requests.items():
            age = (now - request.created_at).total_seconds()
            if age > max_age_seconds:
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self.requests[request_id]

