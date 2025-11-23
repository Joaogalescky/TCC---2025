# https://openfheorg.github.io/openfhe-python/html/index.html

import uuid
from typing import Dict, List
from collections import OrderedDict

from openfhe import CCParamsBFVRNS, GenCryptoContext, PKESchemeFeature

from src.settings import Settings

settings = Settings()


class HomomorphicElectionService:
    def __init__(self, max_cache_size: int = 1000):
        self.cc = None
        self.key_pair = None
        self.public_key = None
        self.secret_key = None
        self.ciphertext_cache: OrderedDict = OrderedDict()
        self.max_cache_size = max_cache_size

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
        """Gera prova ZK simulada de que o ciphertext contém um 1-hot válido"""
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
        """Verifica a prova ZK simulada"""
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
        self.manage_cache(cipher_id, ciphertext)

        return cipher_id, zk_proof

    def encrypt_vote(self, vote_vector: List[int]) -> str:
        cipher_id, _ = self.encrypt_vote_with_proof(vote_vector)
        return cipher_id

    def manage_cache(self, cipher_id: str, ciphertext):
        """Gerencia cache FIFO"""
        if len(self.ciphertext_cache) >= self.max_cache_size:
            self.ciphertext_cache.popitem(last=False)
        
        self.ciphertext_cache[cipher_id] = ciphertext
        self.ciphertext_cache.move_to_end(cipher_id)

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
        self.manage_cache(cipher_id, ciphertext)

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
        self.manage_cache(result_id, ct_result)

        return result_id

    def decrypt_tally(self, encrypted_tally: str, total_candidates: int) -> List[int]:
        """Descriptografa a eleição"""
        # Recuperar ciphertext do cache
        ct_tally = self.ciphertext_cache[encrypted_tally]

        # Descriptografar o plaintext empacotado
        plaintext_result = self.cc.Decrypt(self.secret_key, ct_tally)

        # Extrair valores empacotados
        decrypted_values = plaintext_result.GetPackedValue()
        
        normalized = []
        t = settings.PLAINTEXT_MODULUS
        for v in decrypted_values[:total_candidates]:
            if v < 0:
                v = v + t
            normalized.append(int(v))
        return normalized

    def clear_cache(self):
        self.ciphertext_cache.clear()

    def get_cache_size(self) -> int:
        return len(self.ciphertext_cache)

    def batch_add_votes(self, encrypted_tally: str, encrypted_votes: List[str]) -> str:
        """Adiciona múltiplos votos em um lote"""
        current_tally = encrypted_tally
        
        for encrypted_vote in encrypted_votes:
            current_tally = self.add_vote_to_tally(current_tally, encrypted_vote)
            
        return current_tally

    def process_votes_streaming(self, vote_vectors: List[List[int]], total_candidates: int) -> List[int]:
        """Processa em transmissão os lotes de votes"""
        tally = self.create_zero_tally(total_candidates)
        
        batch_size = 50  # Processar em lotes pequenos
        
        for i in range(0, len(vote_vectors), batch_size):
            batch = vote_vectors[i:i + batch_size]
            
            # Processar lote
            for vote_vector in batch:
                encrypted_vote = self.encrypt_vote(vote_vector)
                tally = self.add_vote_to_tally(tally, encrypted_vote)
            
            # Limpar cache periodicamente
            if i % (batch_size * 10) == 0:
                self.cleanup_old_cache_entries()
        
        return self.decrypt_tally(tally, total_candidates)

    def cleanup_old_cache_entries(self):
        """Remove entradas antigas do cache"""
        if len(self.ciphertext_cache) > self.max_cache_size // 2:
            # Manter apenas metade das entradas mais recentes
            items_to_keep = self.max_cache_size // 2
            items = list(self.ciphertext_cache.items())
            self.ciphertext_cache.clear()
            
            for key, value in items[-items_to_keep:]:
                self.ciphertext_cache[key] = value


# Instância global do serviço
crypto_service = HomomorphicElectionService()
