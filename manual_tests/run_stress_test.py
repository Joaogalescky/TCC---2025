import json
import os
import signal
import sys
import time
import psutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAST_BACKEND_PATH = os.path.join(BASE_DIR, "fast_backend")
sys.path.append(FAST_BACKEND_PATH)

from src.crypto_service import crypto_service

# Estado global
current_test = {}
results = {}

def monitor_memory():
    """Monitora uso de memória em MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def signal_handler(signum, frame):
    """Handler para interrupção do processo"""
    print(f"\n\nPROCESSO INTERROMPIDO POR SINAL {signum}")
    
    if current_test.get('start_time', 0) > 0:
        save_interrupted_test(signum)
    
    generate_report()
    save_report()
    sys.exit(1)

def save_interrupted_test(signum):
    """Salva dados do teste interrompido"""
    end_time = time.time()
    duration = end_time - current_test['start_time']
    final_memory = monitor_memory()
    
    results[current_test['vote_count']] = {
        'success': False,
        'error': f'Processo terminado abruptamente (sinal {signum})',
        'duration': duration,
        'memory_used': final_memory - current_test['initial_memory'],
        'votes_per_second': current_test.get('processed_votes', 0) / duration if duration > 0 else 0,
        'processed_votes': current_test.get('processed_votes', 0),
        'final_results': current_test.get('final_results', []),
        'terminated': True
    }

def run_single_test(vote_count, description):
    """Executa um único teste de stress usando o fluxo do crypto_service.
    Substitui o comportamento anterior conservando o mínimo de mudanças possível.
    """
    print(f"\nTestando {description} votos ({vote_count:,})")

    # Atualiza estado global para suportar interrupção por sinal
    current_test.clear()
    current_test['start_time'] = time.time()
    current_test['vote_count'] = vote_count
    current_test['processed_votes'] = 0
    current_test['final_results'] = []

    # -- Preparação 
    crypto_service.clear_cache()
    crypto_service.setup_crypto() # gera contexto e chaves

    # Parâmetros do teste
    NUM_CANDIDATES = 3             
    CLEAR_CACHE_EVERY = 0 # 0 = não limpar automaticamente; >0 = limpar a cada N votos

    # Medidores
    t_start = time.time()
    proc = psutil.Process(os.getpid())
    mem_start = proc.memory_info().rss / 1024.0 / 1024.0

    encrypt_total = 0.0
    evaladd_total = 0.0
    peak_memory_mb = mem_start

    # Cria tally inicial criptografado (banco de votos)
    tally_id = crypto_service.create_zero_tally(NUM_CANDIDATES)

    # Loop único: para cada voto, cria 1-hot, encripta e soma ao tally
    for i in range(vote_count):
        # exemplo de política de escolha (round-robin)
        candidate_idx = i % NUM_CANDIDATES
        vote_vec = crypto_service.create_vote_vector(candidate_idx, NUM_CANDIDATES)

        # Encriptação (medir tempo)
        t0 = time.time()
        vote_id = crypto_service.encrypt_vote(vote_vec)  # usa encrypt_vote_with_proof internamente
        t1 = time.time()
        encrypt_total += (t1 - t0)

        # Soma homomórfica (medir tempo)
        t2 = time.time()
        tally_id = crypto_service.add_vote_to_tally(tally_id, vote_id)
        t3 = time.time()
        evaladd_total += (t3 - t2)

        # atualizar contadores para handler de sinal
        current_test['processed_votes'] = i + 1

        # monitora memória
        cur_mem = proc.memory_info().rss / 1024.0 / 1024.0
        if cur_mem > peak_memory_mb:
            peak_memory_mb = cur_mem

        # limpeza opcional do cache para controlar uso de memória
        if CLEAR_CACHE_EVERY and ((i + 1) % CLEAR_CACHE_EVERY == 0):
            crypto_service.cleanup_old_cache_entries()

        # feedback periódico (10% steps)
        if (i + 1) % max(1, vote_count // 10) == 0:
            pct = (i + 1) / vote_count * 100
            print(f"  * {pct:.0f}% - {i+1:,} votos processados - mem: {cur_mem:.1f} MB")

    # fim do loop
    duration = time.time() - t_start

    # descriptografar tally final (medir tempo)
    tdec0 = time.time()
    final_results = crypto_service.decrypt_tally(tally_id, NUM_CANDIDATES)
    tdec1 = time.time()
    decrypt_time = tdec1 - tdec0

    mem_end = proc.memory_info().rss / 1024.0 / 1024.0

    # montar métricas similar ao que seu script espera
    metrics = {
        "duration": duration,
        "encrypt_total_s": encrypt_total,
        "evaladd_total_s": evaladd_total,
        "decrypt_s": decrypt_time,
        "avg_encrypt_ms": (encrypt_total / vote_count) * 1000.0 if vote_count else 0,
        "avg_evaladd_ms": (evaladd_total / vote_count) * 1000.0 if vote_count else 0,
        "votes_per_second": vote_count / duration if duration > 0 else 0,
        "memory_used": peak_memory_mb,
        "initial_memory": mem_start,
        "final_memory": mem_end,
    }

    # valida integridade simples (soma dos resultados)
    try:
        total_votes = sum(final_results)
        success = (total_votes == vote_count)
        if not success:
            error_msg = f"Integridade falhou: esperado {vote_count}, obtido {total_votes}"
            print(error_msg)
    except Exception as e:
        final_results = []
        success = False
        error_msg = f"Erro ao validar resultado: {e}"
        print(error_msg)

    # armazena no dicionário global results (mesma estrutura do seu script)
    results[vote_count] = {
        "success": success,
        "metrics": metrics,
        "final_results": final_results,
        "error": None if success else (error_msg if 'error_msg' in locals() else "Desconhecido"),
    }

    # atualiza current_test com resultados para possível handler de sinal
    current_test['final_results'] = final_results

    # imprimir resumo (compatível com print_test_results)
    print("\n--- Resultados ---")
    print(f"Votos processados: {vote_count:,}")
    print(f"Tempo total: {metrics['duration']:.2f}s")
    print(f"Votos por segundo: {metrics['votes_per_second']:.2f}")
    print(f"Memória usada (pico durante teste): {metrics['memory_used']:.2f} MB")
    print(f"Resultados (descriptografados): {final_results}")
    print(f"Total verificado: {sum(final_results) if final_results else 0}")

    # retorna métricas caso o restante do script espere retorno
    return results[vote_count]

def save_report(filename=None):
    """Salva relatório em JSON"""
    try:
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f'stress_test_report_{timestamp}.json'
        
        report_data = {
            'test_type': 'massive_stress',
            'results': results,
            'summary': {
                'max_successful': max([k for k, v in results.items() if v['success']], default=0),
                'total_tests': len(results),
                'successful_tests': len([v for v in results.values() if v['success']]),
                'failed_tests': len([v for v in results.values() if not v['success']]),
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nRelatório salvo: {filename}")
        return filename
        
    except Exception as e:
        print(f"Erro ao salvar relatório: {e}")
        return None

def generate_report():
    """Gera relatório final"""
    print("\n== RELATÓRIO FINAL DE ESTRESSE ==")
    
    for vote_count, result in results.items():
        status = "SUCESSO" if result['success'] else "FALHOU"
        print(f"\n{vote_count:,} votos: {status}")
        
        if result['success']:
            print(f"Tempo: {result['metrics']['duration']:.2f}s")
            print(f"Velocidade: {result['metrics']['votes_per_second']:.0f} votos/s")
        else:
            print(f"Erro: {result.get('error', 'Desconhecido')}")
    
    successful_tests = [k for k, v in results.items() if v['success']]
    max_successful = max(successful_tests) if successful_tests else 0
    print(f"\nLIMITE MÁXIMO: {max_successful:,} votos")

def test_massive_votes():
    """Função principal de testes massivos"""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Iniciando testes de estresse de criptografia homomórfica...")
    
    try:
        crypto_service.setup_crypto()
        
        # T = K * O
        # T = Tempo de execução
        # K = Constante de proporcionalidade (tempo médio de execução)
        # O = Quantidade de operações
        
        test_cases = [
            (100, "cem"),
            (1000, "mil"),
            # (10000, "dez mil"),
            # (100000, "cem mil"),
            # (1000000, "um milhão"),
            # (10000000, "dez milhões"),
            # (100000000, "cem milhões"),
            # (8000000000, "população mundial de")
        ]
        
        for vote_count, description in test_cases:
            if vote_count in results and results[vote_count].get('success'):
                print(f"\nPulando {description} voto(s) - já completado com sucesso")
                continue
            
            run_single_test(vote_count, description)
        
        generate_report()
        save_report()
        
    except Exception as e:
        print(f"Erro durante os testes: {e}")
        save_report()
        raise

if __name__ == "__main__":
    test_massive_votes()
