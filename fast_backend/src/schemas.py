from pydantic import BaseModel, EmailStr

class Message(BaseModel):
    message: str
    
class UserSchema(BaseModel):
    nome: str
    cpf: str
    telefone: str
    email: EmailStr
    password: str
    tipo: str
    statusVotacao: bool