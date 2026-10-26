from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tenant_id: str = Field(min_length=1, max_length=128)
    user_message: str = Field(min_length=1, max_length=16_000)
    session_id: str = Field(min_length=1, max_length=128)


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class Suggestion(BaseModel):
    label: str
    message: str


class CartItem(BaseModel):
    id: str
    title: str
    price_mkd: int = Field(ge=0)
    image_url: Optional[str] = None
    old_price_mkd: int = Field(default=0, ge=0)
    combo_percent: int = Field(default=0, ge=0, le=100)
    combo_ids: List[str] = Field(default_factory=list)
    detail: str = ""
    images: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    tenant_id: str
    session_id: str
    assistant_message: str
    model: str
    usage: TokenUsage
    cached: bool
    suggestions: List[Suggestion] = Field(default_factory=list)
    image_url: Optional[str] = None
    cart: Optional[CartItem] = None
    card: Optional[CartItem] = None
    cards: List[CartItem] = Field(default_factory=list)
