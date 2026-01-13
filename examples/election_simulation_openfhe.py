# election_simulation_openfhe.py
# Simulação simples de eleição com OpenFHE (Python)
# Cada voto é um vetor 1-hot [0,0,1,0,...], encriptado e somado homomorficamente ao tally.

from openfhe import *

def setup_crypto(plaintext_modulus=65537, multiplicative_depth=1):
    """
    Cria CryptoContext e chaves.
    """
    params = CCParamsBFVRNS()
    params.SetPlaintextModulus(plaintext_modulus)
    params.SetMultiplicativeDepth(multiplicative_depth)

    cc = GenCryptoContext(params)
    cc.Enable(PKESchemeFeature.PKE)
    cc.Enable(PKESchemeFeature.KEYSWITCH)
    cc.Enable(PKESchemeFeature.LEVELEDSHE)

    # Key generation
    key_pair = cc.KeyGen()
    cc.EvalMultKeyGen(key_pair.secretKey)

    return cc, key_pair

def encrypt_zero_tally(cc, public_key, n_candidates):
    """
    Cria um vetor de zeros do tamanho n_candidates, transforma em plaintext empacotado e encripta.
    """
    zero_vector = [0] * n_candidates
    pt_zero = cc.MakePackedPlaintext(zero_vector)
    ct_zero = cc.Encrypt(public_key, pt_zero)
    return ct_zero

def vote_vector(n_candidates, choice_index):
    """
    Retorna um vetor 1-hot (lista de inteiros) com 1 na posição choice_index.
    choice_index = 0..n_candidates-1
    """
    v = [0] * n_candidates
    v[choice_index] = 1
    return v

def run_simulation():
    print("=== Simulação de eleição homomórfica (OpenFHE) ===")
    # Parâmetros da eleição
    n_candidates = int(input("Número de candidatos: ").strip())
    n_voters = int(input("Número de eleitores (simulação): ").strip())

    # Configuração do contexto criptográfico
    # PlaintextModulus deve ser > número máximo de votos por candidato esperado
    cc, key_pair = setup_crypto(plaintext_modulus=65537, multiplicative_depth=1)
    public_key = key_pair.publicKey
    secret_key = key_pair.secretKey

    # Tally criptografado inicial (vetor de zeros)
    ct_tally = encrypt_zero_tally(cc, public_key, n_candidates)
    print("\nTally inicial (criptografado) criado.\n")

    # Simular eleitores (lê escolha do usuário para cada eleitor)
    for i in range(n_voters):
        while True:
            try:
                raw = input(f"Eleitor {i+1} - escolha do candidato (1..{n_candidates}): ").strip()
                choice = int(raw)
                if 1 <= choice <= n_candidates:
                    break
                else:
                    print("Escolha inválida. Insira um número no intervalo correto.")
            except ValueError:
                print("Entrada inválida. Digite um número inteiro.")

        # Constrói o vetor de voto 1-hot e o encripta
        v = vote_vector(n_candidates, choice - 1)  # usuário digita 1..N -> índice 0..N-1
        pt_vote = cc.MakePackedPlaintext(v)
        ct_vote = cc.Encrypt(public_key, pt_vote)

        # Soma homomórfica no tally
        ct_tally = cc.EvalAdd(ct_tally, ct_vote)
        print(f"Voto recebido e somado (eleitor {i+1}).")

    # Finalizando eleição: descriptografa o tally
    pt_result = cc.Decrypt(ct_tally, secret_key)
    # Ajusta o comprimento para n_candidates para exibir corretamente
    pt_result.SetLength(n_candidates)

    # pt_result é um PackedPlaintext — converte para lista de inteiros
    result_list = pt_result.GetPackedValue()  # dependendo da versão, pode ser GetCoefPackedValue() ou similar

    print("\n=== Resultado final (descriptografado) ===")
    for idx, cnt in enumerate(result_list):
        print(f"Candidato {idx + 1}: {cnt} voto(s)")

    # Mostra também o plaintext completo (opcional)
    print("\nPlaintext final (raw):", pt_result)

if __name__ == "__main__":
    run_simulation()
