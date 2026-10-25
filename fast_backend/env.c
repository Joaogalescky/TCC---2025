DATABASE_URL='sqlite+aiosqlite:///database.db'
SECRET_KEY='MySecretKey'
ALGORITHM='HS256'
ACCESS_TOKEN_EXPIRE_MINUTES=30
PLAINTEXT_MODULUS=65537
MULTIPLICATIVE_DEPTH=2

# Administrador criado ao iniciar a API, se ainda não existir
ADMIN_USERNAME='admin'
ADMIN_EMAIL='admin@admin.com'
ADMIN_PASSWORD='troque-esta-senha'

# Lotes de votos (LOTE_TAMANHO >= LOTE_MINIMO_DECIFRAR >= 1)
LOTE_TAMANHO=1000
LOTE_MINIMO_DECIFRAR=100

# Pasta das chaves do OpenFHE; sem a variável, usa fast_backend/keys
# KEYS_DIR='/caminho/para/keys'