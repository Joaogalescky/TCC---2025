import json
import os
import signal
import sys
import time
import psutil
import gc

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
        'memory_used': final_memory - current_test.get('initial_memory', final_memory),
        'votes_per_second': current_test.get('processed_votes', 0) / duration if duration > 0 else 0,
        'processed_votes': current_test.get('processed_votes', 0),
        'final_results': current_test.get('final_results', []),
        'terminated': True
    }

def run_single_test(vote_count, description):
    """Executa um único teste de stress usando o fluxo do crypto_service.py"""
    print(f"\nTestando {description} votos ({vote_count:,})")

    current_test.clear()
    current_test['start_time'] = time.time()
    current_test['vote_count'] = vote_count
    current_test['processed_votes'] = 0
    current_test['final_results'] = []

    # Preparação 
    crypto_service.clear_cache()
    gc.collect()

    crypto_service.setup_crypto() # gera contexto e chaves

    # Parâmetros do teste
    NUM_CANDIDATES = 3             
    CLEAR_CACHE_EVERY = 0 # 0 = não limpar automaticamente; >0 = limpar a cada N votos

    # Medidores
    t_start = time.time()
    proc = psutil.Process(os.getpid())
    proc.cpu_percent()

    mem_start = monitor_memory()
    current_test['initial_memory'] = mem_start  # importante para handler de sinal

    encrypt_total = 0.0
    evaladd_total = 0.0
    peak_memory_mb = mem_start

    tally_id = crypto_service.create_zero_tally(NUM_CANDIDATES)

    for i in range(vote_count):
        candidate_idx = i % NUM_CANDIDATES
        vote_vec = crypto_service.create_vote_vector(candidate_idx, NUM_CANDIDATES)

        t0 = time.time()
        vote_id = crypto_service.encrypt_vote(vote_vec)
        t1 = time.time()
        encrypt_total += (t1 - t0)

        t2 = time.time()
        tally_id = crypto_service.add_vote_to_tally(tally_id, vote_id)
        t3 = time.time()
        evaladd_total += (t3 - t2)

        # atualizar contadores para handler de sinal
        current_test['processed_votes'] = i + 1

        cur_mem = monitor_memory()
        if cur_mem > peak_memory_mb:
            peak_memory_mb = cur_mem

        # limpeza opcional do cache para controlar uso de memória
        if CLEAR_CACHE_EVERY and ((i + 1) % CLEAR_CACHE_EVERY == 0):
            # tenta liberar memória periodicamente
            crypto_service.cleanup_old_cache_entries()
            gc.collect()

        # feedback periódico (10% steps)
        if (i + 1) % max(1, vote_count // 10) == 0:
            pct = (i + 1) / vote_count * 100
            print(f"  * {pct:.0f}% - {i+1:,} votos processados - mem: {cur_mem:.1f} MB")

    duration = time.time() - t_start

    tdec0 = time.time()
    final_results = crypto_service.decrypt_tally(tally_id, NUM_CANDIDATES)
    tdec1 = time.time()
    decrypt_time = tdec1 - tdec0

    try:
        crypto_service.clear_cache()
    except Exception:
        pass
    gc.collect()

    mem_end = monitor_memory()
    cpu_percent = proc.cpu_percent()

    metrics = {
        "duration": duration,
        "encrypt_total_s": encrypt_total,
        "evaladd_total_s": evaladd_total,
        "decrypt_s": decrypt_time,
        "avg_encrypt_ms": (encrypt_total / vote_count) * 1000.0 if vote_count else 0,
        "avg_evaladd_ms": (evaladd_total / vote_count) * 1000.0 if vote_count else 0,
        "votes_per_second": vote_count / duration if duration > 0 else 0,
        "memory_used": peak_memory_mb - mem_start,
        "initial_memory": mem_start,
        "final_memory": mem_end,
        "cpu_percent": cpu_percent,
    }

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

    results[vote_count] = {
        "success": success,
        "metrics": metrics,
        "final_results": final_results,
        "error": None if success else (error_msg if 'error_msg' in locals() else "Desconhecido"),
    }

    current_test['final_results'] = final_results

    print("\n--- Resultados ---")
    print(f"Votos processados: {vote_count:,}")
    print(f"Tempo total: {metrics['duration']:.2f}s")
    print(f"Votos por segundo: {metrics['votes_per_second']:.2f}")
    print(f"Memória usada: {metrics['memory_used']:.2f} MB")
    print(f"Resultados (descriptografados): {final_results}")
    print(f"Total verificado: {sum(final_results) if final_results else 0}")

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

def execute_test(run_id):
    """Executa o conjunto de testes para uma única rodada."""
    
    global results
    results = {}
    
    # Limpeza completa da memória antes de cada rodada
    crypto_service.clear_cache()
    gc.collect()
    
    print(f"INICIANDO RODADA DE TESTE #{run_id}")
    
    try:
        # T = K * O
        # T = Tempo de execução
        # K = Constante de proporcionalidade (tempo médio de execução)
        # O = Quantidade de operações
        
        test_cases = [
            (100, "cem"),
            (1000, "mil"),
            (10000, "dez mil"),
            (65000, "sessenta e cinco mil"),
            # (100000, "cem mil"),
            # (1000000, "um milhão"),
            # (10000000, "dez milhões"),
            # (100000000, "cem milhões"),
            # (8000000000, "população mundial de")
        ]
        
        for vote_count, description in test_cases:
            run_single_test(vote_count, description)
            gc.collect()
        
        generate_report()
        
        
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'stress_test_report_run_{run_id}_{timestamp}.json'
        save_report(filename=filename)
        
    except Exception as e:
        print(f"Erro durante a rodada de teste #{run_id}: {e}")
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'stress_test_report_run_{run_id}_ERROR_{timestamp}.json'
        save_report(filename=filename)
        raise

def generate_report():
    """Gera relatório final"""
    print("\n== RELATÓRIO FINAL DE ESTRESSE ==")
    
    for vote_count, result in results.items():
        status = "SUCESSO" if result['success'] else "FALHOU"
        print(f"\n{vote_count:,} votos: {status}")
        
        if result['success']:
            print(f"Tempo: {result['metrics']['duration']:.2f}s")
            print(f"Velocidade: {result['metrics']['votes_per_second']:.0f} votos/s")
            print(f"Memória inicial: {result['metrics']['initial_memory']:.1f} MB")
            print(f"Memória final: {result['metrics']['final_memory']:.1f} MB")
            print(f"Memória usada (pico - inicial): {result['metrics']['memory_used']:.2f} MB")
            print(f"CPU média: {result['metrics']['cpu_percent']:.1f}%")
        else:
            print(f"Erro: {result.get('error', 'Desconhecido')}")
    
    successful_tests = [k for k, v in results.items() if v['success']]
    max_successful = max(successful_tests) if successful_tests else 0
    print(f"\nLIMITE MÁXIMO: {max_successful:,} votos")

def execute_battery_of_test(num_tests):
    """Função principal de testes massivos"""
    import subprocess
    
    print(f"Iniciando {num_tests} rodadas de teste de estresse de criptografia homomórfica...")
    
    for i in range(1, num_tests + 1):
        try:
            # Executa cada rodada em um novo processo Python
            result = subprocess.run(
                [sys.executable, __file__, '--run-single', str(i)],
                cwd=os.getcwd()
            )
            if result.returncode != 0:
                print(f"Rodada #{i} falhou com código {result.returncode}")
        except Exception as e:
            print(f"Erro ao executar rodada #{i}: {e}")
        
    print("\n--- FIM DE TODAS AS RODADAS DE TESTE ---")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--run-single':
        # Modo de execução única (chamado por subprocess)
        run_id = int(sys.argv[2])
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        execute_test(run_id)
    else:
        # Modo de bateria de testes
        execute_battery_of_test(25)
