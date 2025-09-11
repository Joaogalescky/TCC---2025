from pydantic import BaseModel, EmailStr


class Message(BaseModel):
    message: str


class UserSchema(BaseModel):
    nome: str
    senha: str
    # cpf: str
    # telefone: str
    email: EmailStr
    # tipo: str
    statusVotacao: bool


class UserDB(UserSchema):
    id: int


class UserPublic(BaseModel):
    id: int
    nome: str
    email: EmailStr
    statusVotacao: bool


class UserList(BaseModel):
    users: list[UserPublic]


class CandidatoPublic(UserSchema):
    id: int


class AdminPublic(UserSchema):
    id: int
