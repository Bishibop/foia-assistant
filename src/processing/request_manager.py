"""
Request Manager for handling multiple FOIA requests in memory.
"""

from typing import Dict, List, Optional
from src.models.request import FOIARequest


class RequestManager:
    """Manages multiple FOIA requests in memory"""
    
    def __init__(self):
        self._requests: Dict[str, FOIARequest] = {}
        self._active_request_id: Optional[str] = None
        
    def create_request(self, name: str, description: str = "") -> FOIARequest:
        """Create a new FOIA request"""
        request = FOIARequest(name=name, description=description)
        self._requests[request.id] = request
        
        # Set as active if it's the first request
        if not self._active_request_id:
            self._active_request_id = request.id
            
        return request
        
    def get_request(self, request_id: str) -> Optional[FOIARequest]:
        """Retrieve a specific request"""
        return self._requests.get(request_id)
        
    def get_active_request(self) -> Optional[FOIARequest]:
        """Get the currently active request"""
        if self._active_request_id:
            return self._requests.get(self._active_request_id)
        return None
        
    def set_active_request(self, request_id: str) -> bool:
        """Set the active request"""
        if request_id in self._requests:
            self._active_request_id = request_id
            return True
        return False
        
    def list_requests(self) -> List[FOIARequest]:
        """List all requests sorted by creation date"""
        return sorted(
            self._requests.values(), 
            key=lambda r: r.created_at, 
            reverse=True
        )
        
    def delete_request(self, request_id: str) -> bool:
        """Delete a request and its associated data"""
        if request_id in self._requests:
            del self._requests[request_id]
            
            # Update active request if needed
            if self._active_request_id == request_id:
                # Set next available request as active
                if self._requests:
                    self._active_request_id = next(iter(self._requests))
                else:
                    self._active_request_id = None
            return True
        return False
        
    def update_request(self, request_id: str, **kwargs) -> bool:
        """Update request fields"""
        request = self.get_request(request_id)
        if not request:
            return False
            
        # Update allowed fields
        allowed_fields = {
            'name', 'description', 'foia_request_text', 
            'deadline', 'status', 'document_folder'
        }
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(request, field):
                setattr(request, field, value)
                
        return True
        
    def get_request_count(self) -> int:
        """Get total number of requests"""
        return len(self._requests)
        
    def has_active_request(self) -> bool:
        """Check if there's an active request"""
        return self._active_request_id is not None and self._active_request_id in self._requests
        
    def clear_all_requests(self):
        """Clear all requests (for testing purposes)"""
        self._requests.clear()
        self._active_request_id = None