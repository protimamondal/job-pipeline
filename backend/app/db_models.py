from sqlalchemy import Text , ForeignKey, func ,UniqueConstraint, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime


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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] =  mapped_column( DateTime(timezone=True),server_default=func.now())


class Application(Base):
    __tablename__= "applications"
    __table_args__ = (UniqueConstraint("user_id","job_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str]
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column( DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column( DateTime(timezone=True),server_default=func.now(), onupdate=func.now())

    # The job this application is about. Async sessions cannot lazy load, so
    # every query that reads `.job` has to ask for it up front.
    job: Mapped["Job"] = relationship(lazy="raise")
