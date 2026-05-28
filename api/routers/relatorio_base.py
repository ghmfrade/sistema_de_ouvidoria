from datetime import date
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from repositories.relatorios.relatorio_base_repo import get_relatorio_base
from utils.formatters import to_excel

router = APIRouter(tags=["relatorio-base"])


@router.get("/download")
def download_relatorio(data_ini: date, data_fim: date):
    """
    Download de relatório base em XLSX.
    Retorna 204 se sem dados, ou XLSX com as linhas desnormalizadas.
    """
    try:
        rows = get_relatorio_base(data_ini, data_fim)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Se sem dados, retorna 204 No Content
    if not rows:
        return Response(status_code=204)

    # Construir DataFrame com nomes amigáveis
    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "id": "ID",
        "protocolo": "Protocolo",
        "status": "Status",
        "data_entrada": "Data de Entrada",
        "data_1a_resposta_tecnica": "Data da 1ª Resposta Técnica",
        "data_conclusao": "Data de Conclusão",
        "id_reclamacao": "ID - Reclamação",
        "categoria": "Categoria",
        "assunto": "Assunto",
        "cidade_origem": "Local de Embarque",
        "cidade_destino": "Local de Desembarque",
        "n_autos": "Nº Auto",
        "origem": "Origem (Denominação A)",
        "destino": "Destino (Denominação B)",
        "permissionaria": "Permissionária",
        "pontuacao": "Pontuação",
    })

    # Gerar XLSX
    xlsx_bytes = to_excel(df)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_base_{data_ini}_{data_fim}.xlsx"
        }
    )
