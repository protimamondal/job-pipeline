from typing import Literal

from pydantic import BaseModel, ConfigDict

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
