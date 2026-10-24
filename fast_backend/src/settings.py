from pathlib import Path

from pydantic import EmailStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / '.env',
        env_file_encoding='utf-8',
    )

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    PLAINTEXT_MODULUS: int
    MULTIPLICATIVE_DEPTH: int

    # Administrador criado na inicialização (opcional)
    ADMIN_USERNAME: str | None = None
    ADMIN_EMAIL: EmailStr | None = None
    ADMIN_PASSWORD: str | None = None

    # Votos agrupados em lotes: ao completar LOTE_TAMANHO votos, o lote é fechado
    # num subtotal cifrado e os votos individuais são apagados
    LOTE_TAMANHO: int = 1000
    # Nenhum conjunto parcial de votos (nem o seu complemento) com menos votos
    # que isso pode ser decifrado
    LOTE_MINIMO_DECIFRAR: int = 100
    # Contexto e chaves do OpenFHE, gerados uma vez e carregados ao iniciar
    KEYS_DIR: Path = BASE_DIR / 'keys'

    @model_validator(mode='after')
    def validate_lotes(self):
        if self.LOTE_MINIMO_DECIFRAR < 1:
            raise ValueError('LOTE_MINIMO_DECIFRAR deve ser pelo menos 1')
        if self.LOTE_TAMANHO < self.LOTE_MINIMO_DECIFRAR:
            raise ValueError(
                'LOTE_TAMANHO deve ser maior ou igual a LOTE_MINIMO_DECIFRAR'
            )
        return self
