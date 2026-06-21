"""Helpers compartilhados pelas fontes de dados."""
from __future__ import annotations
import unicodedata


def slug(nome: str) -> str:
    """Normaliza nome de município para chave de junção.

    'São Miguel Arcanjo' -> 'sao miguel arcanjo'
    Robusto a acento e caixa, que variam entre SNIS, IBGE e configs.
    """
    s = unicodedata.normalize("NFKD", nome or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()
