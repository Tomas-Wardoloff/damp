from enum import Enum
import unicodedata


class HealthStatus(str, Enum):
    SANA = "SANA"
    SUBCLINICA = "SUBCLINICA"
    CLINICA = "CLINICA"
    MASTITIS = "MASTITIS"
    CELO = "CELO"
    FEBRIL = "FEBRIL"
    DIGESTIVO = "DIGESTIVO"

    @classmethod
    def from_model_value(cls, raw_value: str) -> "HealthStatus":
        normalized = unicodedata.normalize("NFKD", str(raw_value))
        normalized = normalized.encode("ascii", "ignore").decode("ascii").strip().upper()

        aliases = {
            "SUB_CLINICA": "SUBCLINICA",
            "SUBCLINICA": "SUBCLINICA",
            "CLINICA": "CLINICA",
            "MASTITIS": "MASTITIS",
            "SANA": "SANA",
            "CELO": "CELO",
            "FEBRIL": "FEBRIL",
            "DIGESTIVO": "DIGESTIVO",
        }

        mapped = aliases.get(normalized, normalized)
        return cls(mapped)
