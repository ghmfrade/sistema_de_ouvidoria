"""Cliente para download de relatório base."""
from api.client.base import get_bytes_public


def download_relatorio_base(data_ini: str, data_fim: str) -> bytes | None:
    """Faz download do relatório base em XLSX.

    Args:
        data_ini: data inicial em formato ISO (YYYY-MM-DD)
        data_fim: data final em formato ISO (YYYY-MM-DD)

    Returns:
        Bytes do arquivo XLSX, ou None se sem dados para o período.
    """
    return get_bytes_public(
        "/relatorio-base/download",
        {"data_ini": data_ini, "data_fim": data_fim}
    )
