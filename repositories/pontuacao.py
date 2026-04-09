"""Regras de cálculo de pontuação para autos de linha."""

from decimal import Decimal


def calcular_pontuacao_auto(n_autos: int) -> Decimal:
    """Pontuação de cada auto vinculado a uma reclamação: 1 / n_autos.

    Uma reclamação vale 1 ponto distribuído igualmente entre todos os autos
    que atendem ao trecho. Ex.: 3 autos → 0.3333 cada.
    """
    if n_autos <= 0:
        return Decimal("0")
    return Decimal(str(round(1.0 / n_autos, 4)))
