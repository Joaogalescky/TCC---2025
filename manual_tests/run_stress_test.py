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

current_test = {
    'vote_count': 0,
    'description': '',
    'start_time': 0,
    'initial_memory': 0,
    'processed_votes': 0,
    'final_results': [],
    'last_memory': 0,
    'last_progress_time': 0
}

results = {}


def monitor_memory():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB


def signal_handler(signum, frame):
    print(f"\n\nPROCESSO INTERROMPIDO POR SINAL {signum}")

    if current_test['start_time'] > 0:
        end_time = time.time()
        duration = end_time - current_test['start_time']
        current_memory = monitor_memory()
        memory_used = current_memory - current_test['initial_memory']

        votes_per_second = current_test['processed_votes'] / duration if duration > 0 else 0

        results[current_test['vote_count']] = {
            'success': False,
            'error': f'Processo terminado abruptamente (sinal {signum})',
            'duration': duration,
            'memory_used': memory_used,
            'votes_per_second': votes_per_second,
            'processed_votes': current_test['processed_votes'],
            'final_results': current_test['final_results'],
            'final_memory': current_memory,
            'terminated': True
        }

        print("\nCAPTURADO NO TERMINATED")
        print(f"Teste: {current_test['vote_count']:,} voto(s)")
        print(f"Votos processados: {current_test['processed_votes']:,}")
        print(f"Tempo decorrido: {duration:.2f}s")
        print(f"Memória utilizada: +{memory_used:.1f} MB")
        print(f"Velocidade: {votes_per_second:.0f} voto(s)")

    generate_report()
    save_report()
    sys.exit(1)


def save_report(filename=None, overwrite=False):
    try:
        if filename is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f'stress_test_report_{timestamp}.json'

        if os.path.exists(filename) and not overwrite:
            base_name = os.path.splitext(filename)[0]
            counter = 1
            while os.path.exists(f"{base_name}_{counter}.json"):
                counter += 1
            filename = f"{base_name}_{counter}.json"

        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

        report_data = {
            'final_results': results,
            'summary': {
                'max_successful': max([k for k, v in results.items() if v['success']], default=0),
                'max_terminated': max([k for k, v in results.items() if v.get('terminated')], default=0),
                'total_tests': len(results),
                'successful_tests': len([v for v in results.values() if v['success']]),
                'failed_tests': len([v for v in results.values() if not v['success'] and not v.get('terminated')]),
                'terminated_tests': len([v for v in results.values() if v.get('terminated')]),
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'test_duration_total': sum([v['duration'] for v in results.values()])
            },
            'test_cases': list(results.keys())
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\nRelatório salvo em: {os.path.abspath(filename)}")
        return filename

    except Exception as e:
        print(f"Erro ao salvar relatório: {e}")
        print(f"Tipo do erro: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None


def generate_report():
    try:
        print("\n== RELATÓRIO FINAL DE ESTRESSE ==")

        for vote_count, result in results.items():
            status = "SUCESSO!" if result['success'] else "FALHOU!"

            if result.get('terminated'):
                print(f"\n{vote_count:,} voto(s): INTERROMPIDO (Terminated)")
                print(f"Votos processados: {result.get('processed_votes', 0):,}")
                print(f"Tempo decorrido: {result['duration']:.2f}s")
                print(f"Memória utilizada: +{result['memory_used']:.1f} MB")
                print(f"Velocidade: {result['votes_per_second']:.0f} voto(s)")
                print(f"Motivo: {result.get('error', 'Desconhecido')}")
            elif result['success']:
                print(f"\n{vote_count:,} voto(s): {status}")
                print(f"Tempo: {result['duration']:.2f}s")
                print(f"Memória: +{result['memory_used']:.1f} MB")
                print(f"Velocidade: {result['votes_per_second']:.0f} voto(s)")
                print(f"Cache: {result.get('cache_size', 0)} entradas")
                print(f"Resultados: {result.get('final_results', [])}")
            else:
                print(f"\n{vote_count:,} voto(s): {status}")
                print(f"Erro: {result.get('error', 'Desconhecido')}")

        successful_tests = [k for k, v in results.items() if v['success']]
        max_successful = max(successful_tests) if successful_tests else 0

        terminated_tests = [k for k, v in results.items() if v.get('terminated')]
        max_terminated = max(terminated_tests) if terminated_tests else 0

        print(f"\nLIMITE MÁXIMO BEM SUCEDIDO: {max_successful:,} voto(s)")
        if max_terminated > max_successful:
            print(f"LIMITE DE FALHA (Terminated): {max_terminated:,} voto(s)")

        total_tests = len(results)
        successful_count = len(successful_tests)
        terminated_count = len(terminated_tests)
        failed_count = total_tests - successful_count - terminated_count

        print("\nESTATÍSTICAS:")
        print(f"Total de testes: {total_tests}")
        print(f"Sucessos: {successful_count}")
        print(f"Falhas: {failed_count}")
        print(f"Interrompidos: {terminated_count}")

    except Exception as e:
        print(f"Erro ao gerar relatório: {e}")


def test_massive_votes():
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

            print(f"\nTestando {description} voto(s) ({vote_count:,})")

            crypto_service.clear_cache()
            print(f"Cache limpo - tamanho inicial: {crypto_service.get_cache_size()} entrada(s)")

            current_test.update({
                'vote_count': vote_count,
                'description': description,
                'start_time': time.time(),
                'initial_memory': monitor_memory(),
                'processed_votes': 0,
                'final_results': [],
                'last_memory': 0,
                'last_progress_time': time.time()
            })

            try:
                tally = crypto_service.create_zero_tally(3)

                batch_size = min(1000, vote_count // 10)
                processed = 0

                for batch_start in range(0, vote_count, batch_size):
                    batch_end = min(batch_start + batch_size, vote_count)

                    for i in range(batch_start, batch_end):
                        candidate_pos = i % 3
                        vote_vector = crypto_service.create_vote_vector(candidate_pos, 3)
                        encrypted_vote = crypto_service.encrypt_vote(vote_vector)
                        tally = crypto_service.add_vote_to_tally(tally, encrypted_vote)
                        processed += 1
                        current_test['processed_votes'] = processed

                    current_time = time.time()
                    if (current_time - current_test['last_progress_time'] > 2 or
                        batch_end % max(1, vote_count // 10) == 0 or
                        batch_end == vote_count):

                        progress = (batch_end / vote_count) * 100
                        current_memory = monitor_memory()
                        current_test['last_memory'] = current_memory
                        current_test['last_progress_time'] = current_time

                        print(f"  * {progress:.0f}% - {batch_end:,} voto(s) - Memória: {current_memory:.1f} MB")

                final_results = crypto_service.decrypt_tally(tally, 3)
                current_test['final_results'] = final_results
                end_time = time.time()
                final_memory = monitor_memory()

                duration = end_time - current_test['start_time']
                memory_used = final_memory - current_test['initial_memory']
                votes_per_second = vote_count / duration if duration > 0 else 0

                results[vote_count] = {
                    'success': True,
                    'duration': duration,
                    'memory_used': memory_used,
                    'votes_per_second': votes_per_second,
                    'final_results': final_results,
                    'cache_size': crypto_service.get_cache_size()
                }

                print("SUCESSO!")
                print(f"Tempo: {duration:.2f}s")
                print(f"Memória: +{memory_used:.1f} MB")
                print(f"Velocidade: {votes_per_second:.0f} voto(s)")
                print(f"Resultados: {final_results}")

                total_votes = sum(final_results)
                if total_votes == vote_count:
                    print(f"Integridade: {total_votes:,} voto(s) correto(s)")
                else:
                    print(f"Erro de integridade: esperado {vote_count:,}, obtido {total_votes:,}")
                    results[vote_count]['success'] = False

                cache_size_before = crypto_service.get_cache_size()
                crypto_service.clear_cache()
                print(f"Cache limpo após teste: {cache_size_before} → {crypto_service.get_cache_size()} entrada(s)")

            except Exception as e:
                end_time = time.time()
                duration = end_time - current_test['start_time']

                results[vote_count] = {
                    'success': False,
                    'error': str(e),
                    'duration': duration,
                    'memory_used': monitor_memory() - current_test['initial_memory'],
                    'processed_votes': current_test['processed_votes'],
                    'final_results': current_test['final_results'],
                    'cache_size': crypto_service.get_cache_size()
                }

                print(f"Falhou após {duration:.2f}s")
                print(f"Erro: {e}")

                cache_size_before = crypto_service.get_cache_size()
                crypto_service.clear_cache()
                print(f"Cache limpo após teste: {cache_size_before} -> {crypto_service.get_cache_size()} entrada(s)")

        generate_report()
        saved_file = save_report()

        if saved_file:
            print(f"Relatório JSON salvo com sucesso: {saved_file}")
        else:
            print("Falha ao salvar relatório JSON")

    except Exception as e:
        print(f"Erro durante os testes: {e}")
        # Salva relatório mesmo em caso de erro
        save_report()
        raise


if __name__ == "__main__":
    test_massive_votes()
