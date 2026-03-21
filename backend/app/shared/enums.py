from enum import Enum


class HealthStatus(str, Enum):
    SANA = "SANA"
    SUBCLINICA = "SUBCLINICA"
    CLINICA = "CLINICA"
