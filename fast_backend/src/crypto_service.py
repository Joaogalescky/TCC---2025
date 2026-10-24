# https://openfheorg.github.io/openfhe-python/html/index.html

import os
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import List

from openfhe import (
    BINARY,
    CCParamsBFVRNS,
    ClearEvalMultKeys,
    DeserializeCiphertextString,
    DeserializeCryptoContext,
    DeserializePrivateKey,
    DeserializePublicKey,
    GenCryptoContext,
    PKESchemeFeature,
    ReleaseAllContexts,
    Serialize,
    SerializeToFile,
)

from src.settings import Settings

settings = Settings()

# Arquivos gravados em KEYS_DIR na primeira inicialização
KEY_FILES = {
    'context': 'cryptocontext.bin',
    'public': 'public.key',
    'secret': 'secret.key',
    'evalmult': 'evalmult.key',
}


class LegacyCacheAPI:
    """
    API legada: textos cifrados guardados num cache em memória e referenciados
    por UUID. Mantida para os scripts de medição em manual_tests/; as rotas do
    sistema usam a API por bytes de HomomorphicElectionService.
    """

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
        # Verificar se os ciphertext existem no cache
        if encrypted_tally not in self.ciphertext_cache:
            raise ValueError(f'Encrypted tally {encrypted_tally} not found in cache')
        if encrypted_vote not in self.ciphertext_cache:
            raise ValueError(f'Encrypted vote {encrypted_vote} not found in cache')

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
        return self._normalize(plaintext_result.GetPackedValue(), total_candidates)

    def clear_cache(self):
        self.ciphertext_cache.clear()

    def get_cache_size(self) -> int:
        return len(self.ciphertext_cache)

    def cleanup_old_cache_entries(self):
        """Remove entradas antigas do cache"""
        if len(self.ciphertext_cache) > self.max_cache_size // 2:
            # Manter apenas metade das entradas mais recentes
            items_to_keep = self.max_cache_size // 2
            items = list(self.ciphertext_cache.items())
            self.ciphertext_cache.clear()

            for key, value in items[-items_to_keep:]:
                self.ciphertext_cache[key] = value


class HomomorphicElectionService(LegacyCacheAPI):
    def __init__(self, max_cache_size: int = 1000):
        self.cc = None
        self.key_pair = None
        self.public_key = None
        self.secret_key = None
        self.ciphertext_cache: OrderedDict = OrderedDict()
        self.max_cache_size = max_cache_size
        self.keys_dir: Path | None = None

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

    # Persistência de contexto e chaves (sem elas, nada pode ser decifrado
    # depois de reiniciar o backend)

    def load_or_create_keys(self, keys_dir: Path):
        """Carrega contexto e chaves de keys_dir; gera e grava na primeira vez"""
        keys_dir = Path(keys_dir)
        if self.cc is not None and self.keys_dir == keys_dir:
            return

        paths = {name: keys_dir / file for name, file in KEY_FILES.items()}
        existing = [p for p in paths.values() if p.exists()]

        if len(existing) == len(paths):
            self._load_keys(paths)
        elif not existing:
            keys_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(keys_dir, 0o700)
            self.setup_crypto()
            self._save_keys(paths)
        else:
            # Chaves misturadas tornariam os votos já gravados indecifráveis
            raise RuntimeError(f'Conjunto de chaves incompleto em {keys_dir}')

        self.keys_dir = keys_dir
        self._warm_up()

    def _warm_up(self):
        # O OpenFHE trava se o primeiro uso do contexto acontecer numa thread
        # diferente da que o criou (ex.: TestClient e threads de servidor);
        # uma operação completa aqui, na mesma thread, evita isso
        ciphertext = self.encrypt_vector([0])
        ciphertext = self.deserialize(self.serialize(self.add(ciphertext, ciphertext)))
        self.decrypt(ciphertext, 1)

    def _save_keys(self, paths: dict):
        ok = (
            SerializeToFile(str(paths['context']), self.cc, BINARY)
            and SerializeToFile(str(paths['public']), self.public_key, BINARY)
            and SerializeToFile(str(paths['secret']), self.secret_key, BINARY)
            and self.cc.SerializeEvalMultKey(str(paths['evalmult']), BINARY)
        )
        if not ok:
            raise RuntimeError('Falha ao gravar as chaves do OpenFHE')
        os.chmod(paths['secret'], 0o600)

    def _load_keys(self, paths: dict):
        self.cc, ok_context = DeserializeCryptoContext(str(paths['context']), BINARY)
        self.public_key, ok_public = DeserializePublicKey(str(paths['public']), BINARY)
        self.secret_key, ok_secret = DeserializePrivateKey(str(paths['secret']), BINARY)
        ok_evalmult = self.cc.DeserializeEvalMultKey(str(paths['evalmult']), BINARY)
        if not (ok_context and ok_public and ok_secret and ok_evalmult):
            raise RuntimeError('Falha ao carregar as chaves do OpenFHE')
        self.key_pair = None

    def reset(self):
        """Descarta todo o estado em memória (equivale a reiniciar o processo)"""
        self.cc = None
        self.key_pair = None
        self.public_key = None
        self.secret_key = None
        self.keys_dir = None
        self.ciphertext_cache.clear()
        ClearEvalMultKeys()
        ReleaseAllContexts()

    def _require_keys(self):
        if self.cc is None:
            raise RuntimeError('Chaves do OpenFHE não carregadas')

    # API usada pelo sistema: trabalha com textos cifrados e bytes, sem cache

    @staticmethod
    def serialize(ciphertext) -> bytes:
        return Serialize(ciphertext, BINARY)

    def deserialize(self, data: bytes):
        self._require_keys()
        return DeserializeCiphertextString(data, BINARY)

    def encrypt_vector(self, vector: List[int]):
        self._require_keys()
        plaintext = self.cc.MakePackedPlaintext(vector)
        return self.cc.Encrypt(self.public_key, plaintext)

    def zero(self, total_candidates: int):
        return self.encrypt_vector([0] * total_candidates)

    def add(self, ciphertext_a, ciphertext_b):
        self._require_keys()
        # Soma homomórfica: slot-a-slot dos vetores empacotados
        return self.cc.EvalAdd(ciphertext_a, ciphertext_b)

    def decrypt(self, ciphertext, total_candidates: int) -> List[int]:
        self._require_keys()
        plaintext_result = self.cc.Decrypt(self.secret_key, ciphertext)
        return self._normalize(plaintext_result.GetPackedValue(), total_candidates)

    @staticmethod
    def _normalize(values, total_candidates: int) -> List[int]:
        normalized = []
        t = settings.PLAINTEXT_MODULUS
        for v in values[:total_candidates]:
            normalized_v = v + t if v < 0 else v
            normalized.append(int(normalized_v))
        return normalized

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


# Instância global do serviço
crypto_service = HomomorphicElectionService()
