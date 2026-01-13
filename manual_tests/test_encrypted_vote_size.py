import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAST_BACKEND_PATH = os.path.join(BASE_DIR, "fast_backend")
sys.path.append(FAST_BACKEND_PATH)

from src.crypto_service import crypto_service


def test_encrypted_vote_visualization():
    crypto_service.setup_crypto()
    crypto_service.clear_cache()
    
    print("\nVISUALIZAÇÃO DO VOTO CRIPTOGRAFADO\n")
    
    # Criar vetor de voto (3 candidatos, voto no candidato 1)
    NUM_CANDIDATES = 3
    CANDIDATE_POSITION = 1
    
    vote_vector = crypto_service.create_vote_vector(CANDIDATE_POSITION, NUM_CANDIDATES)
    
    print(f"Vetor de Voto Original (plaintext):")
    print(f"  - Vetor: {vote_vector}")
    print(f"  - Candidatos: {NUM_CANDIDATES}")
    print(f"  - Voto no candidato na posição: {CANDIDATE_POSITION}")
    print(f"  - Tamanho do vetor: {len(vote_vector)}")
    
    # Criptografar o voto
    encrypted_vote_id = crypto_service.encrypt_vote(vote_vector)
    
    print(f"\nVoto Criptografado:")
    print(f"  - ID do voto: {encrypted_vote_id}")
    
    # Recuperar o ciphertext do cache
    ciphertext = crypto_service.ciphertext_cache[encrypted_vote_id]
    
    # Informações do ciphertext
    ciphertext_str = str(ciphertext)
    print(f"  - Tamanho em caracteres: {len(ciphertext_str):,}")
    print(f"  - Tamanho em bytes: {sys.getsizeof(ciphertext):,}")
    print(f"  - Primeiros 300 caracteres: {ciphertext_str[:300]}...")
    
    # Comparação de tamanhos
    print(f"\nComparação de Tamanhos:")
    print(f"  - Voto original (plaintext): {sys.getsizeof(vote_vector)} bytes")
    print(f"  - Voto criptografado: {sys.getsizeof(ciphertext):,} bytes")
    print(f"  - Fator de expansão: {sys.getsizeof(ciphertext) / sys.getsizeof(vote_vector):.2f}x")
    
    # Testar descriptografia para validar
    tally = crypto_service.create_zero_tally(NUM_CANDIDATES)
    tally = crypto_service.add_vote_to_tally(tally, encrypted_vote_id)
    results = crypto_service.decrypt_tally(tally, NUM_CANDIDATES)
    
    print(f"\nValidação (descriptografia):")
    print(f"  - Resultado descriptografado: {results}")
    print(f"  - Voto original: {vote_vector}")
    print(f"  - Validação: {'✓ OK' if results == vote_vector else '✗ ERRO'}")
    
    print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    test_encrypted_vote_visualization()
