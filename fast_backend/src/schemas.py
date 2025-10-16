from pydantic import BaseModel, ConfigDict, EmailStr


class Message(BaseModel):
    message: str


class UserSchema(BaseModel):
    username: str
    password: str
    # cpf: str
    # telefone: str
    email: EmailStr
    # tipo: str
    statusVotacao: bool


class UserDB(UserSchema):
    id: int


class UserPublic(BaseModel):
    id: int
    username: str
    email: EmailStr
    statusVotacao: bool
    model_config=ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class CandidatoPublic(UserSchema):
    id: int


class AdminPublic(UserSchema):
    id: int
