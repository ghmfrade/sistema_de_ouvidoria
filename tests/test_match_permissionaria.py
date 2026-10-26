"""Testes da resolução de permissionária e do parse de autos de requisição.

Não tocam o banco: o universo é injetado à mão, no mesmo formato que
`construir_universo` produz.
"""
import pytest

from api.database.match_permissionaria import _preparar, casar
from api.database.termos_requisicao import parse_numero_auto


def universo(*empresas) -> list[dict]:
    """Monta um universo a partir de tuplas (id, cnpj, nome, nome_fantasia)."""
    return [_preparar(*e) for e in empresas]


# Recortes reais do cadastro, com os nomes que causaram os erros em produção.
GUERINO = (73, "72543978000100", "GUERINO SEISCENTO TRANSPORTES S/A", None)
GUERINI = (1011, "67356568000110", "GUERINI PLANEJAMENTOS LTDA", "GUERINI PLANEJAMENTOS LTD")
PASSARO = (42, "61563557000125", "EMPRESA DE ÔNIBUS PASSARO MARRON S/A", "PASSARO MARRON")
RAPIDO_FENIX = (92, "07022473000139", "RAPIDO FENIX VIAÇÃO LTDA", None)
MHS_FENIX = (209, "44341190000186", "MHS TRANSPORTE E TURISMO LTDA - ME", "FENIX")
HELIO = (675, "47939199000181", "HELIO APARECIDO BRAGA 06885710857 - ME", "TRANSPORTE")
REUNIDAS = (100, "61084029000100", "EMPRESAS REUNIDAS PAULISTA DE TRANSPORTES LTDA", None)
PRINCESA_NORTE = (49, "81159857000150", "EMPRESA PRINCESA DO NORTE S/A", None)
PRINCESA_OESTE = (488, "45993490000102", "VIACAO PRINCESA D OESTE LTDA.", "PRINCESA D OESTE")


class TestErrosDeProducao:
    """Casos que o matcher antigo errava por disputar o cadastro inteiro."""

    def test_guerino_nao_cai_na_guerini(self):
        """GUERINI não tem auto, logo fica fora do universo do regular."""
        perm_id, etapa = casar("GUERINO SEISCENTOS", universo(GUERINO))
        assert perm_id == 73
        assert etapa == "similaridade"

    def test_guerino_com_sufixo_tambem_resolve(self):
        perm_id, _ = casar("GUERINO SEISCENTOS TRANSPORTE", universo(GUERINO))
        assert perm_id == 73

    def test_guerino_vence_guerini_mesmo_disputando(self):
        """Ainda que a GUERINI estivesse no universo, a similaridade prefere
        a GUERINO — o CNPJ errado do CSV é que levava para a empresa errada."""
        perm_id, _ = casar("GUERINO SEISCENTOS", universo(GUERINO, GUERINI))
        assert perm_id == 73

    def test_passaro_marrom_com_m_casa_no_marron_com_n(self):
        perm_id, etapa = casar("PASSARO MARROM", universo(PASSARO))
        assert perm_id == 42
        assert etapa == "similaridade"

    def test_viacao_fenix_casa_na_empresa_com_autos(self):
        """Com MHS fora do universo, 'VIAÇÃO FENIX' acha a Rapido Fenix.

        Antes, remove_sufixos reduzia 'VIAÇÃO FENIX' a 'FENIX' e empatava com
        o nome_fantasia da MHS, que não tem nenhum auto.
        """
        perm_id, _ = casar("VIAÇÃO FENIX", universo(RAPIDO_FENIX))
        assert perm_id == 92

    def test_empresas_reunidas_no_plural(self):
        perm_id, _ = casar("EMPRESA REUNIDAS PAULISTA", universo(REUNIDAS))
        assert perm_id == 100


class TestNomeGenericoNaoSequestra:
    """Regressão da Estratégia 5: 'nome cadastrado contido na empresa'."""

    def test_fantasia_de_uma_palavra_generica_nao_captura(self):
        """'TRANSPORTE' é substring de 'RAFAELA TRANSPORTES', mas não casa."""
        perm_id, etapa = casar("RAFAELA TRANSPORTES", universo(HELIO))
        assert perm_id is None
        assert etapa == "nenhuma"

    def test_varias_variantes_nao_caem_na_mesma_empresa(self):
        u = universo(HELIO)
        for nome in ("MV SERAFIM TRANSPORTES LTDA", "BOLONHA TRANSPORTE",
                     "ENZO TRANSPORTES", "IL TRANSPORTES"):
            perm_id, _ = casar(nome, u)
            assert perm_id is None, nome


class TestRecusaEmVezDeErrar:
    def test_empresa_desconhecida_devolve_none(self):
        u = universo(GUERINO, PASSARO, RAPIDO_FENIX)
        for nome in ("USUÁRIO", "BUSER", "PRIMAR NAVEGAÇÕES E TURISMO LTDA EPP"):
            perm_id, etapa = casar(nome, u)
            assert perm_id is None, nome
            assert etapa == "nenhuma"

    def test_nomes_parecidos_sem_folga_devolvem_none(self):
        """PRINCESA DOS CAMPOS fica entre NORTE e D'OESTE: recusa é o certo."""
        perm_id, _ = casar("PRINCESA DOS CAMPOS", universo(PRINCESA_NORTE, PRINCESA_OESTE))
        assert perm_id is None

    def test_universo_vazio_devolve_none(self):
        assert casar("QUALQUER EMPRESA", []) == (None, "nenhuma")

    @pytest.mark.parametrize("valor", [None, "", "   ", 123])
    def test_entrada_invalida_devolve_none(self, valor):
        assert casar(valor, universo(GUERINO)) == (None, "nenhuma")


class TestMatchExato:
    def test_nome_identico(self):
        perm_id, etapa = casar("GUERINO SEISCENTO TRANSPORTES S/A", universo(GUERINO))
        assert perm_id == 73
        assert etapa == "exato"

    def test_nome_fantasia_identico(self):
        perm_id, etapa = casar("PASSARO MARRON", universo(PASSARO))
        assert perm_id == 42
        assert etapa == "exato"


class TestParseNumeroAuto:
    @pytest.mark.parametrize("entrada,esperado", [
        ("3323-A-1", "3323A"),
        ("0012-A-2", "12A"),
        ("8033", "8033A"),
        ("6459-A-1", "6459A"),
        ("7503-A-1", "7503A"),
        (" 8532-A-1 ", "8532A"),
    ])
    def test_formatos(self, entrada, esperado):
        assert parse_numero_auto(entrada) == esperado

    @pytest.mark.parametrize("entrada", ["", "A-1", "sem numero", None])
    def test_invalidos(self, entrada):
        assert parse_numero_auto(entrada) is None


class TestOverrides:
    def test_override_resolve_nome_que_a_cascata_nao_pega(self):
        """'VB TRANSPRTES' (typo) só resolve pela tabela de overrides."""
        vb = (125, "46014122000138", "VB TRANSPORTES E TURISMO LTDA", None)
        perm_id, etapa = casar("VB TRANSPRTES", universo(vb))
        assert perm_id == 125
        assert etapa == "override"

    def test_override_ignorado_se_empresa_fora_do_universo(self):
        """O override não force um perm_id que não tem auto do tipo."""
        perm_id, _ = casar("VB TRANSPRTES", universo(GUERINO))
        assert perm_id is None
