from typing import Annotated, List, Union

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select


class Atelier(SQLModel, table=True):
    id: Union[int, None] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    url: str = Field(index=True)
    category: Union[str, None] = Field(default=None, index=True)
    price: Union[float, None] = Field(default=None, index=True)
    duration: Union[str, None] = Field(default=None, index=True)
    location: Union[str, None] = Field(default=None, index=True)


class AtelierCreate(SQLModel):
    title: str
    url: str
    category: Union[str, None] = None
    price: Union[float, None] = None
    duration: Union[str, None] = None
    location: Union[str, None] = None