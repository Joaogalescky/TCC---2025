# https://openfheorg.github.io/openfhe-python/html/index.html

import uuid
from typing import Dict, Final, List

from openfhe import *

from src.settings import Settings

settings = Settings()


class HomomorphicElectionService:
    def __init__(self):
        self.cc = None
        self.key_pair = None
        # Util para simulação - trocar apos produção
        self.public_key = None  # chaves ficam na instancia
        self.secret_key = None
        # Cache para armazenar ciphertexts em memória
        self.ciphertext_cache: Dict[str, any] = {}

    def setup_crypto(self, plaintext_modulus=settings.PLAINTEXT_MODULUS, multiplicative_depth=settings.MULTIPLICATIVE_DEPTH):
        ''' Setup para criptografia
            - plaintext_modulus:
            - multiplicative_depth: 
        '''
        # Configurar parâmetros BFV
        parameters = CCParamsBFVRNS()
        parameters.SetPlaintextModulus(plaintext_modulus)
        parameters.SetMultiplicativeDepth(multiplicative_depth)

        # Criar contexto criptográfico
        self.cc = GenCryptoContext(parameters)

        # Habilitar recursos necessários
        self.cc.Enable(PKESchemeFeature.PKE)
        self.cc.Enable(PKESchemeFeature.KEYSWITCH)
        self.cc.Enable(PKESchemeFeature.LEVELEDSHE)

        # Gerar chaves
        self.key_pair = self.cc.KeyGen()
        self.cc.EvalMultKeyGen(self.key_pair.secretKey)

        self.public_key = self.key_pair.publicKey
        self.secret_key = self.key_pair.secretKey

    def create_vote_vector(self, candidate_position: int, total_candidates: int) -> List[int]:
        ''' Cria vetor para voto '''
        unit: Final[int] = 1
        vote = [0] * total_candidates  # [0, 0, n...]
        vote[candidate_position] = unit
        return vote

    def encrypt_vote(self, vote_vector: List[int]) -> str:
        ''' Criptografa o vetor com o voto '''
        # Construi um pacote codificado
        plaintext = self.cc.MakePackedPlaintext(vote_vector)
        # Criptografa o pacote
        ciphertext = self.cc.Encrypt(self.public_key, plaintext)
        # Gera UUID
        cipher_id = str(uuid.uuid4())
        # Armazena ciphertext em um dicio com o UUID
        self.ciphertext_cache[cipher_id] = ciphertext
        return cipher_id

    def create_zero_tally(self, total_candidates: int) -> str:
        ''' Cria vetor para eleição '''
        # Cria vetor para eleição
        zero_vector = [0] * total_candidates  # [0, 0, n...]
        # Construi um pacote codificado
        plaintext = self.cc.MakePackedPlaintext(zero_vector)
        # Criptografa o pacote
        ciphertext = self.cc.Encrypt(self.public_key, plaintext)
        # Gerar UUID
        cipher_id = str(uuid.uuid4())
        # Armazena ciphertext em um dicio com o UUID
        self.ciphertext_cache[cipher_id] = ciphertext

        return cipher_id

    def add_vote_to_tally(self, encrypted_tally: str, encrypted_vote: str) -> str:
        ''' Adiciona voto criptofrado à eleição '''
        # Recuperar ciphertexts do cache
        ct_tally = self.ciphertext_cache[encrypted_tally]
        ct_vote = self.ciphertext_cache[encrypted_vote]
        # Soma homomórfica: slot-a-slot dos vetores empacotados
        ct_result = self.cc.EvalAdd(ct_tally, ct_vote)
        # Gera UUID
        result_id = str(uuid.uuid4())
        # Armazenar resultado em um dicio com o UUID
        self.ciphertext_cache[result_id] = ct_result
        return result_id

    def decrypt_tally(self, encrypted_tally: str, total_candidates: int) -> List[int]:
        ''' Descriptografa a eleição '''
        # Recuperar ciphertext do cache
        ct_tally = self.ciphertext_cache[encrypted_tally]

        # Descriptografar
        # Retorna o plaintext empacotado
        plaintext_result = self.cc.Decrypt(self.secret_key, ct_tally)

        # Extrair valores empacotados
        decrypted_values = plaintext_result.GetPackedValue()
        return decrypted_values[:total_candidates]


# Instância global do serviço
crypto_service = HomomorphicElectionService()
