"""HTTP contracts for persistent control-plane resources."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.blueprint.loader import MAX_BLUEPRINT_BYTES, BlueprintFormat
from app.evaluation import EvaluationCase, ReleaseGateReport


class BlueprintSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=MAX_BLUEPRINT_BYTES)
    format: BlueprintFormat


class BlueprintRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    tenant_id: str
    name: str
    display_name: str
    version: str
    stage: str
    content: str
    format: str
    created_at: str
    updated_at: str


class BlueprintVersionRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    blueprint_id: str
    tenant_id: str
    version: str
    content_hash: str
    stage: str
    created_at: str


class KnowledgeDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)
    source_id: str = Field(min_length=2, max_length=128)
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=2_000_000)
    allowed_roles: tuple[str, ...] = Field(min_length=1)
    citation_base: str = Field(min_length=1, max_length=1_000)


class KnowledgeDocumentRecord(KnowledgeDocumentCreate):
    id: str
    version: int
    created_at: str


class RagProfile(BaseModel):
    """Per-module retrieval policy controlled by an enterprise."""

    model_config = ConfigDict(extra="forbid")

    strategy: Literal["hybrid", "semantic", "keyword"] = "hybrid"
    chunk_strategy: Literal["contextual", "structure", "fixed"] = "contextual"
    chunk_size: int = Field(default=800, ge=200, le=4_000)
    chunk_overlap: int = Field(default=120, ge=0, le=1_000)
    candidate_count: int = Field(default=20, ge=5, le=100)
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = True
    compression: bool = True
    return_citations: bool = True
    source_ids: tuple[str, ...] = ()


class ModuleInstallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)
    rag: RagProfile = Field(default_factory=RagProfile)


class BusinessModuleRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    key: str
    name: str
    category: str
    description: str
    agent_count: int
    risk_level: str
    knowledge_types: tuple[str, ...]
    connectors: tuple[str, ...]
    installed: bool = False
    installation_id: str | None = None
    rag: RagProfile | None = None
    updated_at: str | None = None


class StoredEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)
    cases: tuple[EvaluationCase, ...] = Field(min_length=1, max_length=500)
    use_stored_knowledge: bool = True


class EvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    tenant_id: str
    blueprint_id: str
    blueprint_version: str
    score: float
    passed: bool
    report: ReleaseGateReport
    created_at: str


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str | None = Field(default=None, min_length=1, max_length=128)
    environment: Literal["test", "production"]


class DeploymentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    blueprint_id: str
    blueprint_version: str
    environment: str
    created_at: str
