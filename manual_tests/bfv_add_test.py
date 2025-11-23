#!/usr/bin/env python3
"""
Teste real de quantas somas um contexto BFV aguenta (OpenFHE required).
Versão atualizada: normaliza valores retornados pelo Decrypt e imprime RAW + NORMALIZED.
Instruções:
- Instale openfhe-python na sua máquina (compatível com sua instalação).
- Execute: python3 bfv_add_test.py
- Ajuste PLAINTEXT_MODULUS e MULTIPLICATIVE_DEPTH conforme necessário.
"""

from openfhe import CCParamsBFVRNS, GenCryptoContext, PKESchemeFeature
import uuid, sys, traceback

# --- Parâmetros (ajuste conforme necessário) ---
PLAINTEXT_MODULUS = 65537
MULTIPLICATIVE_DEPTH = 1
TOTAL_CANDIDATES = 4  # número de slots que você usa (vetor 1-hot)
PRINT_EVERY = 1000     # imprimir progresso a cada N somas
MAX_ITERS = 200000     # limite de segurança para iterações

# --- Helpers ---
def setup_crypto(plaintext_modulus, multiplicative_depth):
    params = CCParamsBFVRNS()
    params.SetPlaintextModulus(plaintext_modulus)
    params.SetMultiplicativeDepth(multiplicative_depth)
    cc = GenCryptoContext(params)
    cc.Enable(PKESchemeFeature.PKE)
    cc.Enable(PKESchemeFeature.KEYSWITCH)
    cc.Enable(PKESchemeFeature.LEVELEDSHE)
    key_pair = cc.KeyGen()
    cc.EvalMultKeyGen(key_pair.secretKey)
    return cc, key_pair.publicKey, key_pair.secretKey

def normalize_vector(vals, t, total):
    """Retorna lista de inteiros no intervalo [0, t-1] para os primeiros `total` slots."""
    normalized = []
    for v in vals[:total]:
        try:
            # operador % cobre tanto negativos quanto positivos maiores que t-1
            normalized.append(int((int(v) + t) % t))
        except Exception:
            # fallback robusto: converte via int e aplica ajuste
            vv = int(v)
            if vv < 0:
                vv = vv + t
            normalized.append(int(vv))
    return normalized

# --- Teste principal ---
def main():
    print("Setup do contexto BFV...")
    cc, public_key, secret_key = setup_crypto(PLAINTEXT_MODULUS, MULTIPLICATIVE_DEPTH)

    print("Criando plaintexts de tally zero e um voto 1-hot...")
    zero_vector = [0] * TOTAL_CANDIDATES
    vote_vector = [0] * TOTAL_CANDIDATES
    vote_vector[0] = 1  # voto para candidato 0 (ajuste se quiser testar outra posição)
    pt_zero = cc.MakePackedPlaintext(zero_vector)
    pt_vote = cc.MakePackedPlaintext(vote_vector)
    ct_tally = cc.Encrypt(public_key, pt_zero)
    ct_vote = cc.Encrypt(public_key, pt_vote)

    print(f"Iniciando loop de soma (até {MAX_ITERS} iterações).")
    for i in range(1, MAX_ITERS + 1):
        ct_tally = cc.EvalAdd(ct_tally, ct_vote)
        try:
            pt_out = cc.Decrypt(secret_key, ct_tally)
            raw_vals = pt_out.GetPackedValue()
            normalized_vals = normalize_vector(raw_vals, PLAINTEXT_MODULUS, TOTAL_CANDIDATES)

            if i % PRINT_EVERY == 0 or i <= 20:
                # Imprime RAW (como saiu da API) e NORMALIZED (0..t-1)
                print(f"[{i}] raw: {raw_vals[:TOTAL_CANDIDATES]}  |  normalized: {normalized_vals}")

            # opcional: detectar aproximação do limite do modulus (aviso)
            max_val = max(normalized_vals) if normalized_vals else 0
            if max_val > 0.9 * PLAINTEXT_MODULUS:
                print(f"*** AVISO: contador se aproxima do modulus (max={max_val} > 90% de {PLAINTEXT_MODULUS}) ***")

        except Exception as err:
            print("Decryption falhou ou ocorreu erro após", i, "adds.")
            traceback.print_exc()
            sys.exit(0)

    print("Alcancado cap de segurança:", MAX_ITERS)

if __name__ == "__main__":
    main()
