import json
import os
import signal
import sys
import time
import psutil
import gc
import random

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

    if current_test.get("start_time", 0) > 0:
        save_interrupted_test(signum)

    generate_report()
    save_report()
    sys.exit(1)


def save_interrupted_test(signum):
    """Salva dados do teste interrompido"""
    end_time = time.perf_counter()
    duration = end_time - current_test["start_time"]
    final_memory = monitor_memory()

    key = f"{current_test['vote_count']}_{current_test['num_candidates']}"

    results[key] = {
        "vote_count": current_test["vote_count"],
        "num_candidates": current_test["num_candidates"],
        "success": False,
        "error": f"Processo terminado abruptamente (sinal {signum})",
        "duration": duration,
        "memory_used": final_memory - current_test.get("initial_memory", final_memory),
        "votes_per_second": (
            current_test.get("processed_votes", 0) / duration if duration > 0 else 0
        ),
        "processed_votes": current_test.get("processed_votes", 0),
        "final_results": current_test.get("final_results", []),
        "terminated": True,
    }


def run_single_test(vote_count, num_candidates, description):
    """Executa um único teste de stress parametrizado"""
    print(
        f"\n--- Testando {description} votos ({vote_count:,}) com {num_candidates} Candidatos ---"
    )

    current_test.clear()
    current_test["vote_count"] = vote_count
    current_test["num_candidates"] = num_candidates
    current_test["processed_votes"] = 0
    current_test["final_results"] = []

    # Preparação
    crypto_service.clear_cache()
    gc.collect()

    crypto_service.setup_crypto()  # gera contexto e chaves

    # Parâmetros do teste
    CLEAR_CACHE_EVERY = 0  # 0 = não limpar automaticamente; > 0 = limpar a cada N votos

    # Medidores
    # Iniciar cronômetro após o setup para medir apenas o processamento de votos
    current_test["start_time"] = time.perf_counter()
    t_start = current_test["start_time"]

    proc = psutil.Process(os.getpid())
    proc.cpu_percent()  # Calibração
    cpu_times_start = proc.cpu_times()

    mem_start = monitor_memory()
    current_test["initial_memory"] = mem_start  # importante para handler de sinal

    encrypt_total = 0.0
    evaladd_total = 0.0
    peak_memory_mb = mem_start

    # Feedback periódico (10% steps)
    tally_id = crypto_service.create_zero_tally(num_candidates)
    print_interval = max(1, vote_count // 10)
    mem_check_interval = max(1, min(1000, vote_count // 100))

    for i in range(vote_count):
        # Distribui votos entre os candidatos disponíveis (0 a num_candidates-1)
        candidate_idx = i % num_candidates
        vote_vec = crypto_service.create_vote_vector(candidate_idx, num_candidates)

        t0 = time.perf_counter()
        vote_id = crypto_service.encrypt_vote(vote_vec)
        t1 = time.perf_counter()
        encrypt_total += t1 - t0

        t2 = time.perf_counter()
        tally_id = crypto_service.add_vote_to_tally(tally_id, vote_id)
        t3 = time.perf_counter()
        evaladd_total += t3 - t2

        current_test["processed_votes"] = i + 1

        # Monitorar memória com frequência adaptativa
        if i % mem_check_interval == 0:
            cur_mem = monitor_memory()
            if cur_mem > peak_memory_mb:
                peak_memory_mb = cur_mem
        # limpeza opcional do cache para controlar uso de memória
        if CLEAR_CACHE_EVERY and ((i + 1) % CLEAR_CACHE_EVERY == 0):
            # tenta liberar memória periodicamente
            crypto_service.cleanup_old_cache_entries()
            gc.collect()

        if (i + 1) % print_interval == 0:
            cur_mem = monitor_memory()
            pct = (i + 1) / vote_count * 100
            print(
                f"  * {pct:.0f}% ({num_candidates} cand) - {i+1:,} votos - mem: {cur_mem:.1f} MB"
            )

    processing_end_time = time.perf_counter()
    duration_processing = processing_end_time - t_start

    tdec0 = time.perf_counter()
    final_results = crypto_service.decrypt_tally(tally_id, num_candidates)
    tdec1 = time.perf_counter()
    decrypt_time = tdec1 - tdec0

    try:
        crypto_service.clear_cache()
    except Exception:
        pass
    gc.collect()

    mem_end = monitor_memory()

    # Cálculo final de CPU (User + System)
    cpu_percent = proc.cpu_percent()
    cpu_times_end = proc.cpu_times()
    cpu_time_used = (cpu_times_end.user - cpu_times_start.user) + (
        cpu_times_end.system - cpu_times_start.system
    )

    total_wall_time = duration_processing + decrypt_time

    metrics = {
        "duration": total_wall_time,
        "processing_only_s": duration_processing,
        "encrypt_total_s": encrypt_total,
        "evaladd_total_s": evaladd_total,
        "decrypt_s": decrypt_time,
        "avg_encrypt_ms": (encrypt_total / vote_count) * 1000.0 if vote_count else 0,
        "avg_evaladd_ms": (evaladd_total / vote_count) * 1000.0 if vote_count else 0,
        "votes_per_second": (
            vote_count / duration_processing if duration_processing > 0 else 0
        ),
        "memory_used": peak_memory_mb - mem_start,
        "initial_memory": mem_start,
        "final_memory": mem_end,
        "cpu_percent": cpu_percent,
        "cpu_time_s": cpu_time_used,
    }

    try:
        total_votes = sum(final_results)
        success = total_votes == vote_count
        if not success:
            error_msg = (
                f"Integridade falhou: esperado {vote_count}, obtido {total_votes}"
            )
            print(error_msg)
    except Exception as e:
        final_results = []
        success = False
        error_msg = f"Erro ao validar resultado: {e}"
        print(error_msg)

    # Chave composta para diferenciar testes no relatório final
    result_key = f"{vote_count}_{num_candidates}"

    results[result_key] = {
        "vote_count": vote_count,
        "num_candidates": num_candidates,
        "success": success,
        "metrics": metrics,
        "final_results": final_results,
        "error": (
            None
            if success
            else (error_msg if "error_msg" in locals() else "Desconhecido")
        ),
    }

    current_test["final_results"] = final_results

    print(f"\n--- Resultados ({num_candidates} Candidatos) ---")
    print(
        f"Tempo Total: {metrics['duration']:.2f}s | CPU: {metrics['cpu_time_s']:.2f}s"
    )
    print(f"TPS (Votos/s): {metrics['votes_per_second']:.2f}")
    print(f"Média Encrypt: {metrics['avg_encrypt_ms']:.3f}ms")
    print(f"Resultado: {final_results}")

    return results[result_key]


def save_report(filename=None):
    """Salva relatório em JSON"""
    try:
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"stress_test_report_{timestamp}.json"

        report_data = {
            "test_type": "massive_stress_mixed_candidates",
            "results": results,
            "summary": {
                "total_tests": len(results),
                "successful_tests": len([v for v in results.values() if v["success"]]),
                "failed_tests": len([v for v in results.values() if not v["success"]]),
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\nRelatório salvo: {filename}")
        return filename

    except Exception as e:
        print(f"Erro ao salvar relatório: {e}")
        return None


def execute_test(run_id):
    """Executa o conjunto de testes misturando quantidade de candidatos."""

    global results
    results = {}

    # Limpeza completa da memória antes de cada rodada
    crypto_service.clear_cache()
    gc.collect()

    print(f"INICIANDO RODADA DE TESTE #{run_id} (Ordem Aleatória)")

    try:
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

        # Lista de candidatos a serem testados
        candidate_options = [3, 6, 9]

        # Cria uma lista plana de todos os testes a serem feitos
        test_queue = []
        for vote_count, description in test_cases:
            for num_cand in candidate_options:
                test_queue.append((vote_count, num_cand, description))

        # IMPORTANTE: Embaralha a ordem para evitar viés de aquecimento da máquina
        # Se 3 candidatos sempre rodar primeiro, ele sempre pegará a máquina 'fria'.
        random.shuffle(test_queue)

        print(f"Fila de testes gerada com {len(test_queue)} execuções (embaralhadas).")

        for vote_count, num_cand, description in test_queue:
            run_single_test(vote_count, num_cand, description)
            gc.collect()

        generate_report()

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_report_run_{run_id}_{timestamp}.json"
        save_report(filename=filename)

    except Exception as e:
        print(f"Erro durante a rodada de teste #{run_id}: {e}")
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"stress_test_report_run_{run_id}_ERROR_{timestamp}.json"
        save_report(filename=filename)
        raise


def generate_report():
    """Gera relatório final"""
    print("\n== RELATÓRIO FINAL DE ESTRESSE (MISTO) ==")

    # Ordena chaves para exibição organizada, já que a execução foi aleatória
    sorted_keys = sorted(
        results.keys(),
        key=lambda k: (results[k]["vote_count"], results[k]["num_candidates"]),
    )

    for key in sorted_keys:
        result = results[key]
        vc = result["vote_count"]
        nc = result["num_candidates"]
        status = "SUCESSO" if result["success"] else "FALHOU"

        print(f"\n[{nc} Cand] {vc:,} votos: {status}")

        if result["success"]:
            m = result["metrics"]
            print(
                f"  > Tempo Wall: {m['duration']:.2f}s | Encrypt Médio: {m['avg_encrypt_ms']:.2f}ms"
            )
            print(f"  > TPS: {m['votes_per_second']:.0f}")
        else:
            print(f"  > Erro: {result.get('error', 'Desconhecido')}")


def execute_battery_of_test(num_tests):
    """Função principal de testes massivos"""
    import subprocess

    print(f"Iniciando {num_tests} rodadas de teste de estresse...")

    for i in range(1, num_tests + 1):
        try:
            result = subprocess.run(
                [sys.executable, __file__, "--run-single", str(i)], cwd=os.getcwd()
            )
            if result.returncode != 0:
                print(f"Rodada #{i} falhou com código {result.returncode}")
        except Exception as e:
            print(f"Erro ao executar rodada #{i}: {e}")

    print("\n--- FIM DE TODAS AS RODADAS DE TESTE ---")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--run-single":
        # Modo de execução única (chamado por subprocess)
        run_id = int(sys.argv[2])
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        execute_test(run_id)
    else:
        # Modo de bateria de testes
        execute_battery_of_test(25)
