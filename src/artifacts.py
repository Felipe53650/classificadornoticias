"""Utilitários de integridade usados pelo treinamento e pelo serviço."""
import hashlib
from pathlib import Path


def dataset_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
