#!/usr/bin/env python3

import sys
import time
import psutil
import os
sys.path.append('/workspaces/TCC---2025/fast_backend')

from fast_backend.src.crypto_service import crypto_service

def monitor_memory():
    # Monitora uso de memória"
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024   # MB

def test_massive_votes():
    # Testa limites massivos de votos
    print("Iniciando testes de estresse de criptografia homomórfica...")
    
    crypto_service.setup_crypto()
    
    test_cases = [
        # (100, "cem"),
        # (1000, "mil"), 
        # (10000, "dez mil"),
        # (100000, "cem mil"),
        # (1000000, "um milhão"),
        # (8000000, "população mundial de")
    ]
    
    results = {}
    
    for vote_count, description in test_cases:
        print(f"\nTestando {description} votos ({vote_count:,})")
        
        initial_memory = monitor_memory()
        start_time = time.time()
        
        try:
            # Criar tally inicial
            tally = crypto_service.create_zero_tally(3)
            
            # Processar votos em lotes
            batch_size = min(1000, vote_count // 10)
            processed = 0
            
            for batch_start in range(0, vote_count, batch_size):
                batch_end = min(batch_start + batch_size, vote_count)
                
                for i in range(batch_start, batch_end):
                    candidate_pos = i % 3  # Distribuir entre 3 candidatos
                    vote_vector = crypto_service.create_vote_vector(candidate_pos, 3)
                    encrypted_vote = crypto_service.encrypt_vote(vote_vector)
                    tally = crypto_service.add_vote_to_tally(tally, encrypted_vote)
                    processed += 1
                
                # Log progresso
                if batch_end % (vote_count // 10) == 0 or batch_end == vote_count:
                    progress = (batch_end / vote_count) * 100
                    current_memory = monitor_memory()
                    print(f"  * {progress:.0f}% - {batch_end:,} votos - Memória: {current_memory:.1f}MB")
            
            # Descriptografar resultado
            final_results = crypto_service.decrypt_tally(tally, 3)
            
            end_time = time.time()
            final_memory = monitor_memory()
            
            # Calcular métricas
            duration = end_time - start_time
            memory_used = final_memory - initial_memory
            votes_per_second = vote_count / duration if duration > 0 else 0
            
            results[vote_count] = {
                'success': True,
                'duration': duration,
                'memory_used': memory_used,
                'votes_per_second': votes_per_second,
                'final_results': final_results,
                'cache_size': len(crypto_service.ciphertext_cache)
            }
            
            print(f"SUCESSO!")
            print(f"Tempo: {duration:.2f}s")
            print(f"Memória: +{memory_used:.1f} MB")
            print(f"Velocidade: {votes_per_second:.0f} votos/s")
            print(f"Resultados: {final_results}")
            print(f"Cache: {len(crypto_service.ciphertext_cache)} entradas")
            
            # Verificar integridade
            total_votes = sum(final_results)
            if total_votes == vote_count:
                print(f"Integridade: {total_votes:,} votos corretos")
            else:
                print(f"Erro de integridade: esperado {vote_count:,}, obtido {total_votes:,}")
                results[vote_count]['success'] = False
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            results[vote_count] = {
                'success': False,
                'error': str(e),
                'duration': duration,
                'memory_used': monitor_memory() - initial_memory
            }
            
            print(f"Falhou após {duration:.2f}s")
            print(f"Erro: {e}")
            
            max_successful = max([k for k, v in results.items() if v['success']], default=0)
            print(f"\nLIMITE MÁXIMO TESTADO: {max_successful:,} votos")
            
            break
    
    # Relatório final
    print("\n== RELATÓRIO FINAL DE ESTRESSE ==")
    
    for vote_count, result in results.items():
        status = "SUCESSO!" if result['success'] else "FALHOU!"
        print(f"votos: {vote_count:,} - {status}")
        
        if result['success']:
            print(f"Tempo: {result['duration']:.2f}s")
            print(f"Memória: +{result['memory_used']:.1f}MB")
            print(f"Velocidade: {result['votes_per_second']:.0f} votos/s")
            print(f"Cache: {result['cache_size']} entradas\n")
        else:
            print(f"Erro: {result.get('error', 'Desconhecido')}")
    
    # Encontrar limite máximo
    max_successful = max([k for k, v in results.items() if v['success']], default=0)
    print(f"LIMITE MÁXIMO TESTADO: {max_successful:,} votos")


if __name__ == "__main__":
    test_massive_votes()