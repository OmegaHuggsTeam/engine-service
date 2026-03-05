"""
Pydantic v2 models para o Identity Manager.
ProviderType, ProvisioningStep, ProviderConfig, StepConfig, IdentityConfig, ProvisioningTask.
"""

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    GROQ = "groq"


class ProvisioningStep(str, Enum):
    NAVIGATE = "navigate"
    FILL_FORM = "fill_form"
    SUBMIT = "submit"
    VERIFY = "verify"
    EXTRACT_KEY = "extract_key"
    STORE_KEY = "store_key"


class StepConfig(BaseModel):
    """Configuracao de um step de provisionamento."""
    step: ProvisioningStep
    selector: Optional[str] = None
    value_field: Optional[str] = None
    timeout_ms: int = 5000


class ProviderConfig(BaseModel):
    """Configuracao de um provider de identidade."""
    provider: ProviderType
    enabled: bool = True
    base_url: str
    steps: list[StepConfig] = Field(default_factory=list)
    form_fields: dict[str, str] = Field(default_factory=dict)


class IdentityConfig(BaseModel):
    """Configuracao completa de identidade com providers."""
    version: str = "1.0"
    identity_name: str
    providers: list[ProviderConfig] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ProvisioningTask(BaseModel):
    """Tarefa de provisionamento com checksum e dependencias."""
    id: str = ""
    provider: ProviderType
    step: ProvisioningStep
    status: str = "pending"
    depends_on: list[str] = Field(default_factory=list)
    input_data: dict[str, Any] = Field(default_factory=dict)
    checksum: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    def compute_checksum(self) -> str:
        """Computa SHA-256 checksum dos dados da task."""
        payload = f"{self.id}:{self.provider.value}:{self.step.value}"
        return hashlib.sha256(payload.encode()).hexdigest()
