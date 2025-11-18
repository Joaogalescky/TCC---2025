# https://openfheorg.github.io/openfhe-python/html/index.html

import uuid
from typing import Dict, List

from openfhe import CCParamsBFVRNS, GenCryptoContext, PKESchemeFeature

from src.settings import Settings

settings = Settings()


class HomomorphicElectionService:
    def __init__(self):
        self.cc = None
        self.key_pair = None
        self.public_key = None
        self.secret_key = None
        self.ciphertext_cache: Dict[str, any] = {}

    def setup_crypto(
        self,
        plaintext_modulus=settings.PLAINTEXT_MODULUS,
        multiplicative_depth=settings.MULTIPLICATIVE_DEPTH,
    ):
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

    @staticmethod
    def validate_1hot_vector(vote_vector: List[int]) -> bool:
        """Valida se o vetor é 1-hot válido"""
        # Verificar se todos os valores são 0 ou 1 (binários)
        if not all(x in {0, 1} for x in vote_vector):
            return False

        # Verificar se tem exatamente um "1"
        ones_count = sum(vote_vector)

        # Deve somar exatamente 1
        return ones_count == 1 and len(vote_vector) > 0

    def create_vote_vector(
        self, candidate_position: int, total_candidates: int
    ) -> List[int]:
        if candidate_position < 0 or candidate_position >= total_candidates:
            raise ValueError('Posição do candidato inválida')

        vote = [0] * total_candidates
        vote[candidate_position] = 1

        # Validar antes de retornar
        if not self.validate_1hot_vector(vote):
            raise ValueError('Vetor de voto inválido')

        return vote

    def generate_zk_proof(self, vote_vector: List[int], ciphertext) -> str:
        """Gera prova ZK de que o ciphertext contém um 1-hot válido"""
        # Implementação simplificada de ZK proof

        # Verificar que é 1-hot
        if not self.validate_1hot_vector(vote_vector):
            raise ValueError('Vetor não é 1-hot válido')

        # Simular prova ZK
        proof_data = {
            'sum_is_one': sum(vote_vector) == 1,
            'all_binary': all(x in {0, 1} for x in vote_vector),
            'vector_length': len(vote_vector),
        }

        # Retornar "prova" como string
        return f'zk_proof_{hash(str(proof_data))}'

    @staticmethod
    def verify_zk_proof(proof: str, total_candidates: int) -> bool:
        """Verifica a prova ZK"""
        # Implementação simplificada
        zk_proof_length = 10

        return proof.startswith('zk_proof_') and len(proof) > zk_proof_length

    def encrypt_vote_with_proof(self, vote_vector: List[int]) -> tuple[str, str]:
        """Encripta voto e gera prova ZK"""
        # Validar 1-hot
        if not self.validate_1hot_vector(vote_vector):
            raise ValueError('Voto deve ser 1-hot válido')

        # Encriptar
        plaintext = self.cc.MakePackedPlaintext(vote_vector)
        ciphertext = self.cc.Encrypt(self.public_key, plaintext)

        # Gerar prova ZK
        zk_proof = self.generate_zk_proof(vote_vector, ciphertext)

        # Armazenar em cache
        cipher_id = str(uuid.uuid4())
        self.ciphertext_cache[cipher_id] = ciphertext

        return cipher_id, zk_proof

    def encrypt_vote(self, vote_vector: List[int]) -> str:
        """Método original mantido para compatibilidade"""
        cipher_id, _ = self.encrypt_vote_with_proof(vote_vector)
        return cipher_id

    def create_zero_tally(self, total_candidates: int) -> str:
        """Cria vetor para eleição"""
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
        """Adiciona voto criptofrado à eleição"""
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
        """Descriptografa a eleição"""
        # Recuperar ciphertext do cache
        ct_tally = self.ciphertext_cache[encrypted_tally]

        # Descriptografar o plaintext empacotado
        plaintext_result = self.cc.Decrypt(self.secret_key, ct_tally)

        # Extrair valores empacotados
        decrypted_values = plaintext_result.GetPackedValue()

        return decrypted_values[:total_candidates]

    def clear_cache(self):
        self.ciphertext_cache.clear()

    def get_cache_size(self) -> int:
        return len(self.ciphertext_cache)


# Instância global do serviço
crypto_service = HomomorphicElectionService()
