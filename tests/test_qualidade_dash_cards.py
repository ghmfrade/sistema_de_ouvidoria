"""Testes do Painel SIGO (qualidade_dash) — helpers, layout e callbacks.

Cobre:
  - Importação do layout sem erros (apanha typos de id, helpers ausentes).
  - Registro de callbacks no app Dash (apanha Outputs duplicados / IDs ausentes).
  - Estrutura do helper `kpi_card_button` (modos KPI vs only-button).
  - Helpers puros de callbacks (`_tem_regular`, conversões para query string).
"""
import dash
import dash_bootstrap_components as dbc
import pytest


# ── Layout: importação e build ───────────────────────────────────────────────

def test_build_layout_funciona():
    """O layout precisa ser instanciável sem chamar API/banco."""
    from qualidade_dash.layout import build_layout
    layout = build_layout()
    assert layout is not None


def test_layout_contem_9_kpi_cards():
    """A nova interface SIGO tem exatamente 9 cards-botão."""
    from qualidade_dash.layout import build_layout

    layout = build_layout()
    encontrados = []

    def _walk(component):
        # dbc.Card com id em dict (pattern-matching) é nosso kpi-card
        cid = getattr(component, "id", None)
        if isinstance(cid, dict) and cid.get("type") == "kpi-card":
            encontrados.append(cid.get("index"))
        for child in (getattr(component, "children", None) or []):
            if hasattr(child, "children") or hasattr(child, "id"):
                _walk(child)

    # children pode vir como lista ou componente único
    children = layout.children if isinstance(layout.children, list) else [layout.children]
    for c in children:
        _walk(c)

    assert sorted(encontrados) == [1, 2, 3, 4, 5, 6, 7, 8, 9], (
        f"Indices encontrados: {encontrados}"
    )


def test_registra_callbacks_sem_erro():
    """Callbacks devem registrar sem Outputs duplicados nem IDs ausentes."""
    from qualidade_dash.callbacks import register_callbacks

    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    from qualidade_dash.layout import build_layout
    app.layout = build_layout()
    register_callbacks(app)  # deve passar sem exceção


# ── kpi_card_button ──────────────────────────────────────────────────────────

class TestKpiCardButton:
    def test_modo_padrao_inclui_valor(self):
        from qualidade_dash.components import kpi_card_button
        card = kpi_card_button(1, "Total", value_id="kpi-val-1")
        cid = card.id
        assert isinstance(cid, dict)
        assert cid == {"type": "kpi-card", "index": 1}
        assert card.n_clicks == 0
        assert "kpi-card" in card.className

    def test_only_button_mode(self):
        from qualidade_dash.components import kpi_card_button
        card = kpi_card_button(9, "Mapa", only_button=True)
        assert card.id["index"] == 9
        # Sem value_id quando only_button=True
        # card.children é o div .kpi-body; .children é a lista interna
        body = card.children
        body_children = body.children
        ids = [getattr(c, "id", None) for c in body_children]
        assert "kpi-val-9" not in ids

    def test_accent_color_exposto_como_var(self):
        from qualidade_dash.components import kpi_card_button
        card = kpi_card_button(1, "X", accent_color="#ff0000")
        assert card.style == {"--accent": "#ff0000"}


# ── Helpers puros de callbacks ───────────────────────────────────────────────

class TestHelpersServico:
    def test_tem_regular_apenas_fretamento(self):
        from qualidade_dash.callbacks import _tem_regular
        assert _tem_regular(["Fretamento Metropolitano"]) is False
        assert _tem_regular(["Fretamento Metropolitano", "Fretamento Intermunicipal"]) is False

    def test_tem_regular_com_regular(self):
        from qualidade_dash.callbacks import _tem_regular
        assert _tem_regular(["Regular – Metropolitano"]) is True
        assert _tem_regular(["Regular – Intermunicipal", "Fretamento Metropolitano"]) is True

    def test_tem_regular_vazio_ou_none(self):
        from qualidade_dash.callbacks import _tem_regular
        assert _tem_regular(None) is False
        assert _tem_regular([]) is False


class TestHelpersQueryString:
    def test_tipo_servico_str_lista_vazia(self):
        from qualidade_dash.callbacks import _tipo_servico_str
        assert _tipo_servico_str([]) is None
        assert _tipo_servico_str(None) is None

    def test_tipo_servico_str_unico(self):
        from qualidade_dash.callbacks import _tipo_servico_str
        assert _tipo_servico_str(["Regular – Metropolitano"]) == "Regular – Metropolitano"

    def test_tipo_servico_str_multiplo(self):
        from qualidade_dash.callbacks import _tipo_servico_str
        out = _tipo_servico_str(["A", "B", "C"])
        assert out == "A,B,C"

    def test_meses_str(self):
        from qualidade_dash.callbacks import _meses_str
        assert _meses_str([1, 2, 12]) == "1,2,12"
        assert _meses_str([]) is None
        assert _meses_str(None) is None

    def test_perm_ids_str(self):
        from qualidade_dash.callbacks import _perm_ids_str
        assert _perm_ids_str([1, 2, 3]) == "1,2,3"
        assert _perm_ids_str([]) is None

    def test_assuntos_str(self):
        from qualidade_dash.callbacks import _assuntos_str
        assert _assuntos_str(["ATRASO", "FALTA"]) == "ATRASO,FALTA"
        assert _assuntos_str([]) is None


class TestEmpresaNomesFromOpts:
    def test_resolve_nomes_pelos_ids(self):
        from qualidade_dash.callbacks import _empresa_nomes_from_opts
        opts = [
            {"label": "Empresa A", "value": 1},
            {"label": "Empresa B", "value": 2},
            {"label": "Empresa C", "value": 3},
        ]
        nomes = _empresa_nomes_from_opts([1, 3], opts)
        assert set(nomes) == {"Empresa A", "Empresa C"}

    def test_sem_ids_retorna_vazio(self):
        from qualidade_dash.callbacks import _empresa_nomes_from_opts
        assert _empresa_nomes_from_opts(None, [{"label": "X", "value": 1}]) == []
        assert _empresa_nomes_from_opts([], []) == []

    def test_ids_inexistentes_sao_ignorados(self):
        from qualidade_dash.callbacks import _empresa_nomes_from_opts
        opts = [{"label": "Empresa A", "value": 1}]
        assert _empresa_nomes_from_opts([99], opts) == []
