from decimal import Decimal
from dataclasses import dataclass


@dataclass
class Translation:
    id: int
    vocabulary: chr
    word: str
    translation: str
    sml: Decimal = None
    reference: str = None