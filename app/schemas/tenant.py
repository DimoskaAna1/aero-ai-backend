from typing import List

from pydantic import BaseModel, Field


class QuickChip(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)


class TenantConfig(BaseModel):
    id: str
    name: str
    industry: str
    agent_name: str
    greeting_message: str
    quick_chips: List[QuickChip]
    system_prompt: str
