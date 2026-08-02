from pydantic import BaseModel, Field


class GrammarCheckRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    level: str = Field(default="A2", min_length=1, max_length=40)
    context: str = Field(default="", max_length=2000)
