from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str]
    title: Mapped[str]
    location: Mapped[str]
    salary_usd: Mapped[int | None]
    url: Mapped[str | None]
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str]
