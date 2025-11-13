#!/usr/bin/env python3

import sys
sys.path.append('/workspaces/TCC---2025/fast_backend')

from src.crypto_service import crypto_service

def test_crypto():
    print("Configurando criptografia...")
    crypto_service.setup_crypto()
    
    print("Criptografia configurada!")
    
    # Teste básico
    print("\nTestando votação para 3 candidatos...")
    
    # Voto no candidato 1 (posição 1)
    vote_vector = crypto_service.create_vote_vector(1, 3)
    print(f"Vetor de voto: {vote_vector}")
    
    encrypted_vote = crypto_service.encrypt_vote(vote_vector)
    print(f"Voto criptografado: {encrypted_vote[:50]}...")
    
    # Criar tally inicial
    encrypted_tally = crypto_service.create_zero_tally(3)
    print(f"Tally inicial: {encrypted_tally[:50]}...")
    
    # Somar voto ao tally
    new_tally = crypto_service.add_vote_to_tally(encrypted_tally, encrypted_vote)
    print(f"Tally atualizado: {new_tally[:50]}...")
    
    # Descriptografar resultado
    results = crypto_service.decrypt_tally(new_tally, 3)
    print(f"Resultados: {results}")
    
    if results == [0, 1, 0]:
        print("Teste passou! Criptografia funcionando corretamente.")
        return True
    else:
        print("Teste falhou!")
        return False

if __name__ == "__main__":
    test_crypto()