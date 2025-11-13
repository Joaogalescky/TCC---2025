from typing import List, Dict
from openfhe import *
import uuid


class HomomorphicElectionService:
    def __init__(self):
        self.cc = None
        self.key_pair = None
        self.public_key = None
        self.secret_key = None
        # Cache para armazenar ciphertexts em memória
        self.ciphertext_cache: Dict[str, any] = {}

    def setup_crypto(self, plaintext_modulus=65537, multiplicative_depth=1):
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
        vote = [0] * total_candidates
        vote[candidate_position] = 1
        return vote

    def encrypt_vote(self, vote_vector: List[int]) -> str:
        # Criar plaintext
        plaintext = self.cc.MakePackedPlaintext(vote_vector)
        
        # Encriptar
        ciphertext = self.cc.Encrypt(self.public_key, plaintext)
        
        # Gerar ID único e armazenar em cache
        cipher_id = str(uuid.uuid4())
        self.ciphertext_cache[cipher_id] = ciphertext
        
        return cipher_id

    def create_zero_tally(self, total_candidates: int) -> str:
        zero_vector = [0] * total_candidates
        plaintext = self.cc.MakePackedPlaintext(zero_vector)
        ciphertext = self.cc.Encrypt(self.public_key, plaintext)
        
        # Gerar ID único e armazenar em cache
        cipher_id = str(uuid.uuid4())
        self.ciphertext_cache[cipher_id] = ciphertext
        
        return cipher_id

    def add_vote_to_tally(self, encrypted_tally: str, encrypted_vote: str) -> str:
        # Recuperar ciphertexts do cache
        ct_tally = self.ciphertext_cache[encrypted_tally]
        ct_vote = self.ciphertext_cache[encrypted_vote]
        
        # Soma homomórfica
        ct_result = self.cc.EvalAdd(ct_tally, ct_vote)
        
        # Armazenar resultado em novo ID
        result_id = str(uuid.uuid4())
        self.ciphertext_cache[result_id] = ct_result
        
        return result_id

    def decrypt_tally(self, encrypted_tally: str, total_candidates: int) -> List[int]:
        # Recuperar ciphertext do cache
        ct_tally = self.ciphertext_cache[encrypted_tally]
        
        # Descriptografar
        plaintext_result = self.cc.Decrypt(self.secret_key, ct_tally)
        
        # Extrair valores
        decrypted_values = plaintext_result.GetPackedValue()
        return decrypted_values[:total_candidates]


# Instância global do serviço
crypto_service = HomomorphicElectionService()