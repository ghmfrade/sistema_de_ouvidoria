"""Testes unitários para os helpers de subtítulo do qualidade_dash (sem banco/API)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from qualidade_dash.callbacks import (
    _regiao_label_curto,
    _build_subtitulo_compartilhado,
    _build_subtitulo_regular,
)

_REG_METRO = "Regular – Metropolitano"
_REG_INTER = "Regular – Intermunicipal"
_FRET_M    = "Fretamento Metropolitano"
_FRET_I    = "Fretamento Intermunicipal"


class TestRegiaoLabelCurto:
    def test_tc1_retorna_tc1(self):
        assert _regiao_label_curto("TC1") == "TC1"

    def test_tc5_retorna_tc5(self):
        assert _regiao_label_curto("TC5") == "TC5"

    def test_rm_remove_prefixo(self):
        assert _regiao_label_curto("RM Baixada Santista") == "Baixada Santista"

    def test_rm_campinas_remove_prefixo(self):
        assert _regiao_label_curto("RM Campinas") == "Campinas"

    def test_sem_prefixo_retorna_igual(self):
        assert _regiao_label_curto("Campinas") == "Campinas"


class TestSubtituloCompartilhado:
    def test_todos_servicos_retorna_vazio(self):
        assert _build_subtitulo_compartilhado(
            [_REG_METRO, _REG_INTER, _FRET_M, _FRET_I], None, None, None
        ) == ""

    def test_so_reg_metro_sem_filtros(self):
        assert _build_subtitulo_compartilhado([_REG_METRO], None, None, None) == "Serviço Regular Metropolitano"

    def test_so_reg_inter_sem_filtros(self):
        assert _build_subtitulo_compartilhado([_REG_INTER], None, None, None) == "Serviço Regular Intermunicipal"

    def test_reg_metro_com_uma_regiao(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO], ["RM Baixada Santista"], None, None)
        assert "Baixada Santista" in sub
        assert "Regular Metropolitano" in sub

    def test_reg_inter_com_tc1(self):
        sub = _build_subtitulo_compartilhado([_REG_INTER], ["TC1"], None, None)
        assert "TC1" in sub
        assert "Regular Intermunicipal" in sub

    def test_reg_metro_inter_com_duas_regioes(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO, _REG_INTER], ["RM Baixada Santista", "TC1"], None, None)
        assert "Baixada Santista" in sub
        assert "TC1" in sub

    def test_reg_metro_com_empresa(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO], None, "COMETA", None)
        assert "COMETA" in sub
        assert "Regular Metropolitano" in sub

    def test_misto_fret_reg_com_empresa(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO, _FRET_M], None, "COMETA", None)
        assert "Fretamento" in sub
        assert "COMETA" in sub
        assert "Regular" in sub

    def test_assunto_no_final(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO], None, None, "ATRASO")
        assert sub.endswith("— ATRASO")

    def test_assunto_com_empresa(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO], None, "COMETA", "ATRASO")
        assert "COMETA" in sub
        assert "ATRASO" in sub

    def test_so_fretamento_sem_filtros(self):
        sub = _build_subtitulo_compartilhado([_FRET_M, _FRET_I], None, None, None)
        assert "Fretamento" in sub

    def test_assunto_sem_outros_filtros(self):
        sub = _build_subtitulo_compartilhado([_REG_METRO], None, None, "LOTAÇÃO")
        assert "LOTAÇÃO" in sub


class TestSubtituloRegular:
    def test_ambos_regulares_retorna_servico_regular(self):
        assert _build_subtitulo_regular([_REG_METRO, _REG_INTER], None, None, None) == "Serviço Regular"

    def test_so_metro_retorna_metro(self):
        assert _build_subtitulo_regular([_REG_METRO], None, None, None) == "Serviço Regular Metropolitano"

    def test_so_inter_retorna_inter(self):
        assert _build_subtitulo_regular([_REG_INTER], None, None, None) == "Serviço Regular Intermunicipal"

    def test_com_empresa(self):
        sub = _build_subtitulo_regular([_REG_METRO], None, "COMETA", None)
        assert "Regular Metropolitano" in sub
        assert "COMETA" in sub

    def test_com_regiao(self):
        sub = _build_subtitulo_regular([_REG_METRO], ["RM Campinas"], None, None)
        assert "Campinas" in sub

    def test_assunto_incluido_quando_true(self):
        sub = _build_subtitulo_regular([_REG_METRO], None, None, "ATRASO", incluir_assunto=True)
        assert "ATRASO" in sub

    def test_assunto_ignorado_quando_false(self):
        sub = _build_subtitulo_regular([_REG_METRO], None, None, "ATRASO", incluir_assunto=False)
        assert "ATRASO" not in sub

    def test_empresa_prevalece_sobre_regiao_no_texto(self):
        sub = _build_subtitulo_regular([_REG_METRO], ["RM Campinas"], "COMETA", None)
        assert "COMETA" in sub

    def test_assunto_com_empresa(self):
        sub = _build_subtitulo_regular([_REG_METRO], None, "COMETA", "ATRASO", incluir_assunto=True)
        assert "COMETA" in sub
        assert "ATRASO" in sub
