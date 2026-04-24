from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)


class ChatSource(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    snippet: str


class ChatAskResponse(BaseModel):
    answer: str
    sources: list[ChatSource]
    retrieved_chunks: int
