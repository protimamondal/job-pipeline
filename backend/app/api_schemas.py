from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

JobStatus = Literal["saved", "applied", "interviewing", "rejected"]


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: str
    title: str
    location: str
    salary_usd: int | None
    url: str | None
    description: str


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApplicationCreate(BaseModel):
    job_id: int
    status: JobStatus = "saved"
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: JobStatus | None = None
    notes: str | None = None


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job: JobRead
    status: JobStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DraftRequest(BaseModel):
    instruction: str | None = None


class ChatRequest(BaseModel):
    messages: list[dict]


# A pasted resume, trimmed. Blank is rejected rather than saved as an empty
# document; the upper limit keeps one request from sending megabytes of text
# that would later be chunked and embedded at our cost.
ResumeText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000)
]


class ResumeUpdate(BaseModel):
    resume: ResumeText


class ResumeRead(BaseModel):
    resume: str | None
