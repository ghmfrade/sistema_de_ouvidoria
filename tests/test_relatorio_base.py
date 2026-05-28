"""Testes para o repositório e endpoint de relatório base."""
import pytest
from datetime import date, timedelta
from repositories.relatorios.relatorio_base_repo import get_relatorio_base


class TestRelatorioBaseRepo:
    """Testes do repositório get_relatorio_base."""

    def test_periodo_vazio_retorna_lista_vazia(self):
        """Período sem dados retorna lista vazia."""
        # Usar datas futuras bem distantes
        data_ini = date(2099, 1, 1)
        data_fim = date(2099, 12, 31)

        result = get_relatorio_base(data_ini, data_fim)

        assert isinstance(result, list)
        assert len(result) == 0

    def test_periodo_com_dados_retorna_dicts(self):
        """Período com dados retorna lista de dicts com as chaves corretas."""
        # Usar período abrangente que deve ter dados de teste
        data_ini = date(2020, 1, 1)
        data_fim = date.today()

        result = get_relatorio_base(data_ini, data_fim)

        # Se houver dados, validar estrutura
        if result:
            assert isinstance(result, list)
            assert isinstance(result[0], dict)

            # Validar chaves esperadas
            expected_keys = {
                "id", "protocolo", "status", "data_entrada",
                "data_1a_resposta_tecnica", "data_conclusao",
                "id_reclamacao", "categoria", "assunto",
                "cidade_origem", "cidade_destino",
                "n_autos", "sistema", "origem", "destino", "permissionaria", "pontuacao"
            }
            assert set(result[0].keys()) == expected_keys

    def test_denormalizacao_correta(self):
        """Valida que uma ouvidoria com múltiplas reclamações e autos aparece desnormalizada."""
        data_ini = date(2020, 1, 1)
        data_fim = date.today()

        result = get_relatorio_base(data_ini, data_fim)

        if not result:
            pytest.skip("Sem dados de teste no banco")

        # Agrupar por ID de ouvidoria
        ouvidorias = {}
        for row in result:
            oid = row["id"]
            if oid not in ouvidorias:
                ouvidorias[oid] = []
            ouvidorias[oid].append(row)

        # Se há ouvidorias com múltiplas reclamações/autos, validar desnormalização
        for oid, rows in ouvidorias.items():
            if len(rows) > 1:
                # Todos os rows devem ter o mesmo protocolo, status, data_entrada
                protocolo = rows[0]["protocolo"]
                status = rows[0]["status"]
                data_entrada = rows[0]["data_entrada"]

                for row in rows:
                    assert row["protocolo"] == protocolo, \
                        f"Protocolo inconsistente para ouvidoria {oid}"
                    assert row["status"] == status, \
                        f"Status inconsistente para ouvidoria {oid}"
                    assert row["data_entrada"] == data_entrada, \
                        f"Data de entrada inconsistente para ouvidoria {oid}"

    def test_status_enum_convertido_para_string(self):
        """Status deve ser string, não Enum."""
        data_ini = date(2020, 1, 1)
        data_fim = date.today()

        result = get_relatorio_base(data_ini, data_fim)

        if result:
            for row in result:
                assert isinstance(row["status"], str) or row["status"] is None, \
                    f"Status deve ser string ou None, recebeu {type(row['status'])}"

    def test_pontuacao_numeric(self):
        """Pontuação deve ser numérica (float, int ou Decimal)."""
        from decimal import Decimal

        data_ini = date(2020, 1, 1)
        data_fim = date.today()

        result = get_relatorio_base(data_ini, data_fim)

        if result:
            for row in result:
                if row["pontuacao"] is not None:
                    assert isinstance(row["pontuacao"], (int, float, Decimal)), \
                        f"Pontuação deve ser numérica, recebeu {type(row['pontuacao'])}"
