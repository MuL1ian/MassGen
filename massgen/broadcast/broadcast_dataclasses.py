# -*- coding: utf-8 -*-
"""Data structures for broadcast communication system."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class BroadcastStatus(Enum):
    """Status of a broadcast request."""

    PENDING = "pending"  # Just created, not yet sent to agents
    COLLECTING = "collecting"  # Sent to agents, collecting responses
    COMPLETE = "complete"  # All responses collected
    TIMEOUT = "timeout"  # Timeout reached before all responses collected


@dataclass
class BroadcastRequest:
    """Represents a broadcast question from one agent to others.

    Args:
        id: Unique identifier for this broadcast request
        sender_agent_id: ID of the agent sending the broadcast
        question: The question or message being broadcast
        timestamp: When the broadcast was created
        status: Current status of the broadcast
        timeout: Maximum time to wait for responses (seconds)
        responses_received: Number of responses collected so far
        expected_response_count: Expected number of responses (num agents + human if applicable)
        response_mode: How the broadcast should be handled ("inline" only for now; other modes like "background" could be added in future)
        metadata: Additional metadata for the broadcast
    """

    id: str
    sender_agent_id: str
    question: str
    timestamp: datetime
    status: BroadcastStatus = BroadcastStatus.PENDING
    timeout: int = 300
    responses_received: int = 0
    expected_response_count: int = 0
    response_mode: str = "inline"  # Always "inline" for now. Could support other modes (e.g., "background") in future if needed.
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "sender_agent_id": self.sender_agent_id,
            "question": self.question,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "timeout": self.timeout,
            "responses_received": self.responses_received,
            "expected_response_count": self.expected_response_count,
            "response_mode": self.response_mode,
            "metadata": self.metadata,
        }


@dataclass
class BroadcastResponse:
    """Represents a response to a broadcast request.

    Args:
        request_id: ID of the broadcast request this responds to
        responder_id: ID of the agent or "human" responding
        content: The response content
        timestamp: When the response was created
        is_human: Whether this response is from a human
        metadata: Additional metadata for the response
    """

    request_id: str
    responder_id: str
    content: str
    timestamp: datetime
    is_human: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "responder_id": self.responder_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "is_human": self.is_human,
            "metadata": self.metadata,
        }
