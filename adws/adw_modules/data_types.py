# ABOUTME: Data type definitions for ADW state management
# ABOUTME: Provides Pydantic models for type-safe state validation and serialization

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ADWStateData(BaseModel):
    """Type-safe state data container for ADW workflows."""

    adw_id: str = Field(..., description="Unique ADW ID")
    issue_number: Optional[str] = Field(None, description="GitHub issue number")
    branch_name: Optional[str] = Field(None, description="Git branch name")
    plan_file: Optional[str] = Field(None, description="Path to plan file")
    issue_class: Optional[str] = Field(None, description="Classification of issue")
    worktree_path: Optional[str] = Field(None, description="Path to git worktree")
    backend_port: Optional[int] = Field(None, description="Backend service port")
    frontend_port: Optional[int] = Field(None, description="Frontend service port")
    model_set: str = Field("base", description="Model configuration set")
    all_adws: List[str] = Field(default_factory=list, description="List of all ADW IDs in workflow")

    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow additional fields for forward compatibility


class AgentTemplateRequest(BaseModel):
    """Request for executing an agent template."""
    template_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class GitHubIssue(BaseModel):
    """GitHub issue data."""
    number: int
    title: str
    body: Optional[str] = None
    state: str = "open"

    class Config:
        extra = "allow"


class AgentPromptResponse(BaseModel):
    """Response from agent prompt execution."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None

    class Config:
        extra = "allow"


class IssueClassSlashCommand(BaseModel):
    """Slash command for issue classification."""
    command: str
    issue_id: Optional[str] = None

    class Config:
        extra = "allow"


class ADWExtractionResult(BaseModel):
    """Result of extracting ADW information from output."""
    adw_id: str
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class GitHubIssueListItem(BaseModel):
    """Item in GitHub issues list response."""
    number: int
    title: str
    state: str
    body: Optional[str] = None

    class Config:
        extra = "allow"


class GitHubComment(BaseModel):
    """GitHub comment data."""
    id: int
    body: str
    user: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        extra = "allow"
