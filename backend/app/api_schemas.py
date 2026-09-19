from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

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