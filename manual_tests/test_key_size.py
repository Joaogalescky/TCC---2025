import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAST_BACKEND_PATH = os.path.join(BASE_DIR, "fast_backend")
sys.path.append(FAST_BACKEND_PATH)

from src.crypto_service import crypto_service


def test_key_sizes():
    crypto_service.setup_crypto()
    
    print("\nINFORMAÇÕES DAS CHAVES CRIPTOGRÁFICAS\n")
    
    # Chave Pública
    public_key_str = str(crypto_service.public_key)
    print(f"Chave Pública:")
    print(f"  - Tamanho em caracteres: {len(public_key_str):,}")
    print(f"  - Tamanho em bytes: {sys.getsizeof(crypto_service.public_key):,}")
    print(f"  - Primeiros 200 caracteres: {public_key_str[:200]}...")
    
    # Chave Privada
    secret_key_str = str(crypto_service.secret_key)
    print(f"\nChave Privada:")
    print(f"  - Tamanho em caracteres: {len(secret_key_str):,}")
    print(f"  - Tamanho em bytes: {sys.getsizeof(crypto_service.secret_key):,}")
    print(f"  - Primeiros 200 caracteres: {secret_key_str[:200]}...")
    
    # Contexto Criptográfico
    print(f"\nContexto Criptográfico:")
    print(f"  - Tamanho em bytes: {sys.getsizeof(crypto_service.cc):,}")
    
    # Parâmetros
    print(f"\nParâmetros BFV:")
    print(f"  - Plaintext Modulus: 65537")
    print(f"  - Multiplicative Depth: 2")
    
    print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    test_key_sizes()
