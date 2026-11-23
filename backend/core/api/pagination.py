"""Pagination shared by every module's list routes, so they all take and return the same shape:
``limit`` (1-200, default 50) and ``offset`` in, ``{items, total, limit, offset}`` out."""

from dataclasses import dataclass
from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A page of results; ``total`` counts every match, not just this page."""

    items: list[T]
    total: int
    limit: int
    offset: int


class Envelope(BaseModel, Generic[T]):
    """The shape of every successful response: the payload sits under ``data``."""

    success: bool = True
    message: str
    data: T
    timestamp: str


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def get_pagination(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


Pagination = Annotated[PageParams, Depends(get_pagination)]
