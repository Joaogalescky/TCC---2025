from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Message(BaseModel):
    message: str


class UserSchema(BaseModel):
    username: str
    password: str
    email: EmailStr
    statusVotacao: bool


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    statusVotacao: bool
    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class CandidateSchema(BaseModel):
    username: str


class CandidatePublic(BaseModel):
    id: int
    username: str
    model_config = ConfigDict(from_attributes=True)


class CandidateList(BaseModel):
    candidates: list[CandidatePublic]


class ElectionSchema(BaseModel):
    title: str


class ElectionPublic(BaseModel):
    id: int
    title: str
    model_config = ConfigDict(from_attributes=True)


class ElectionList(BaseModel):
    elections: list[ElectionPublic]


class Token(BaseModel):
    access_token: str
    token_type: str


class FilterPage(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class VoteSchema(BaseModel):
    candidate_id: int


class VoteResponse(BaseModel):
    message: str
    vote_id: int


class ElectionResultsSchema(BaseModel):
    election_id: int
    candidates: List[dict]  # [{"id": 1, "username": "Candidato A", "votes": 10}]
    total_votes: int
