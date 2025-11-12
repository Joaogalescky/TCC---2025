from typing import List

from openfhe import *


class HomomorphicElectionService:
    def __init__(self):
        self.cc = None
        self.key_pair = None
        self.public_key = None
        self.secret_key = None

    def setup_crypto(self, plaintext_modulus=65537, multiplicative_depth=1):
        """Configura o contexto criptográfico BFV"""
        params = CCParamsBFVRNS()
        params.SetPlaintextModulus(plaintext_modulus)
        params.SetMultiplicativeDepth(multiplicative_depth)

        self.cc = GenCryptoContext(params)
        self.cc.Enable(PKESchemeFeature.PKE)
        self.cc.Enable(PKESchemeFeature.KEYSWITCH)
        self.cc.Enable(PKESchemeFeature.LEVELEDSHE)

        self.key_pair = self.cc.KeyGen()
        self.cc.EvalMultKeyGen(self.key_pair.secretKey)

        self.public_key = self.key_pair.publicKey
        self.secret_key = self.key_pair.secretKey

    def create_vote_vector(self, candidate_position: int, total_candidates: int) -> List[int]:
        """Cria vetor 1-hot para o voto"""
        vote = [0] * total_candidates
        vote[candidate_position] = 1
        return vote

    def encrypt_vote(self, vote_vector: List[int]) -> str:
        """Encripta o vetor de voto e retorna como string serializada"""
        pt_vote = self.cc.MakePackedPlaintext(vote_vector)
        ct_vote = self.cc.Encrypt(self.public_key, pt_vote)
        # Serializar o ciphertext para string (implementação simplificada)
        return f"encrypted_vote_{len(vote_vector)}"

    def create_zero_tally(self, total_candidates: int) -> str:
        """Cria tally inicial com zeros encriptados"""
        zero_vector = [0] * total_candidates
        pt_zero = self.cc.MakePackedPlaintext(zero_vector)
        ct_zero = self.cc.Encrypt(self.public_key, pt_zero)
        return f"encrypted_tally_{total_candidates}"

    def add_vote_to_tally(self, encrypted_tally: str, encrypted_vote: str) -> str:
        """Soma homomórfica do voto ao tally (implementação simplificada)"""
        # Em implementação real, desserializar, somar e serializar novamente
        return encrypted_tally

    def decrypt_tally(self, encrypted_tally: str, total_candidates: int) -> List[int]:
        """Descriptografa o tally final (implementação simplificada)"""
        # Em implementação real, desserializar e descriptografar
        return [0] * total_candidates


# Instância global do serviço
crypto_service = HomomorphicElectionService()
