from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    supabase_configured: bool
    openai_configured: bool
