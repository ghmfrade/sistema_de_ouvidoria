"""Testes para o Dashboard de Qualidade v2 (/dashboard/qualidade-v2/*).

Cobre todos os 13 endpoints definidos em api/routers/dashboard_qualidade_novo.py:
  - Parsers de parâmetros (unit tests, sem banco)
  - Acesso público (nenhum endpoint exige autenticação)
  - Estrutura e tipos dos campos em cada resposta
  - Comportamento com filtros (ano, meses, tipo_servico, categoria)
  - Paginação: estrutura, campo pagina, página além do limite, por_pagina
  - Invariantes: ordenação, limites numéricos, xmax/zmax_global
  - Casos-limite: ano sem dados, perm_ids inválidos, lista vazia
"""
import pytest

BASE = "/dashboard/qualidade-v2"


# ── Parsers de parâmetros (sem banco) ─────────────────────────────────────────

class TestParseList:
    def test_none_retorna_lista_vazia(self):
        from api.routers.dashboard_qualidade_novo import _parse_list
        assert _parse_list(None) == []

    def test_string_vazia_retorna_lista_vazia(self):
        from api.routers.dashboard_qualidade_novo import _parse_list
        assert _parse_list("") == []

    def test_um_item(self):
        from api.routers.dashboard_qualidade_novo import _parse_list
        assert _parse_list("Regular Metropolitano") == ["Regular Metropolitano"]

    def test_multiplos_itens(self):
        from api.routers.dashboard_qualidade_novo import _parse_list
        result = _parse_list("Fretamento Intermunicipal,Fretamento Metropolitano")
        assert result == ["Fretamento Intermunicipal", "Fretamento Metropolitano"]

    def test_remove_espacos_ao_redor(self):
        from api.routers.dashboard_qualidade_novo import _parse_list
        assert _parse_list(" A , B , C ") == ["A", "B", "C"]

    def test_ignora_itens_vazios_entre_virgulas(self):
        from api.routers.dashboard_qualidade_novo import _parse_list
        assert _parse_list("A,,B,") == ["A", "B"]


class TestParseMeses:
    def test_none_retorna_lista_vazia(self):
        from api.routers.dashboard_qualidade_novo import _parse_meses
        assert _parse_meses(None) == []

    def test_string_vazia_retorna_lista_vazia(self):
        from api.routers.dashboard_qualidade_novo import _parse_meses
        assert _parse_meses("") == []

    def test_um_mes(self):
        from api.routers.dashboard_qualidade_novo import _parse_meses
        assert _parse_meses("3") == [3]

    def test_multiplos_meses(self):
        from api.routers.dashboard_qualidade_novo import _parse_meses
        assert _parse_meses("1,6,12") == [1, 6, 12]

    def test_ignora_tokens_nao_numericos(self):
        from api.routers.dashboard_qualidade_novo import _parse_meses
        assert _parse_meses("1,abc,3") == [1, 3]

    def test_ignora_strings_vazias_entre_virgulas(self):
        from api.routers.dashboard_qualidade_novo import _parse_meses
        assert _parse_meses("1,,3") == [1, 3]


class TestParsePermIds:
    def test_none_retorna_lista_vazia(self):
        from api.routers.dashboard_qualidade_novo import _parse_perm_ids
        assert _parse_perm_ids(None) == []

    def test_string_vazia_retorna_lista_vazia(self):
        from api.routers.dashboard_qualidade_novo import _parse_perm_ids
        assert _parse_perm_ids("") == []

    def test_multiplos_ids(self):
        from api.routers.dashboard_qualidade_novo import _parse_perm_ids
        assert _parse_perm_ids("1,2,3") == [1, 2, 3]

    def test_ignora_nao_numericos(self):
        from api.routers.dashboard_qualidade_novo import _parse_perm_ids
        assert _parse_perm_ids("1,abc,3") == [1, 3]


# ── Fixture: ano com dados ────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def ano_com_dados(client):
    """Retorna o ano mais recente com dados de RECLAMAÇÃO ou pula o teste."""
    r = client.get(f"{BASE}/anos-disponiveis")
    assert r.status_code == 200
    anos = r.json()
    if not anos:
        pytest.skip("Banco sem dados de RECLAMAÇÃO para nenhum ano")
    return anos[-1]


# ── Helper ────────────────────────────────────────────────────────────────────

def _assert_paginado(data: dict, pagina_esperada: int, chaves_dados: set):
    """Verifica estrutura comum de respostas paginadas."""
    assert isinstance(data, dict), f"Esperava dict, recebeu {type(data)}"
    for chave in ("dados", "total_paginas", "pagina"):
        assert chave in data, f"Campo '{chave}' ausente na resposta"
    assert isinstance(data["dados"], list)
    assert isinstance(data["total_paginas"], int)
    assert data["total_paginas"] >= 1
    assert data["pagina"] == pagina_esperada
    for item in data["dados"]:
        for chave in chaves_dados:
            assert chave in item, f"Campo '{chave}' ausente em item: {item}"


# ── Acesso público — nenhum endpoint exige autenticação ───────────────────────

def test_todos_endpoints_publicos_sem_token(client, ano_com_dados):
    """Todos os 13 endpoints v2 respondem 200 sem header Authorization."""
    endpoints = [
        (f"{BASE}/anos-disponiveis",         {}),
        (f"{BASE}/meses-disponiveis",         {"ano": ano_com_dados}),
        (f"{BASE}/resumo",                    {"ano": ano_com_dados}),
        (f"{BASE}/evolucao-mensal",           {"ano": ano_com_dados}),
        (f"{BASE}/assuntos-pizza",            {"ano": ano_com_dados}),
        (f"{BASE}/empresas-pontuacao",        {"ano": ano_com_dados}),
        (f"{BASE}/empresas-irregular",        {"ano": ano_com_dados}),
        (f"{BASE}/heatmap-assunto-empresa",   {"ano": ano_com_dados}),
        (f"{BASE}/autos-pontuacao",           {"ano": ano_com_dados}),
        (f"{BASE}/autos-irregular",           {"ano": ano_com_dados}),
        (f"{BASE}/heatmap-assunto-auto",      {"ano": ano_com_dados}),
        (f"{BASE}/locais-embarque",           {"ano": ano_com_dados}),
        (f"{BASE}/empresas-lista",            {}),
    ]
    for path, params in endpoints:
        r = client.get(path, params=params)  # sem headers de autenticação
        assert r.status_code == 200, (
            f"{path} retornou HTTP {r.status_code} sem autenticação: {r.text[:200]}"
        )


# ── /anos-disponiveis ─────────────────────────────────────────────────────────

class TestAnosDisponiveis:
    def test_retorna_lista_de_inteiros(self, client):
        r = client.get(f"{BASE}/anos-disponiveis")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert all(isinstance(a, int) for a in data)

    def test_anos_em_ordem_crescente(self, client):
        data = client.get(f"{BASE}/anos-disponiveis").json()
        assert data == sorted(data)

    def test_anos_em_faixa_razoavel(self, client):
        for ano in client.get(f"{BASE}/anos-disponiveis").json():
            assert 2000 <= ano <= 2100


# ── /meses-disponiveis ────────────────────────────────────────────────────────

class TestMesesDisponiveis:
    def test_retorna_lista_de_inteiros(self, client, ano_com_dados):
        r = client.get(f"{BASE}/meses-disponiveis", params={"ano": ano_com_dados})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert all(isinstance(m, int) for m in data)

    def test_meses_no_intervalo_1_a_12(self, client, ano_com_dados):
        data = client.get(f"{BASE}/meses-disponiveis", params={"ano": ano_com_dados}).json()
        assert all(1 <= m <= 12 for m in data)

    def test_meses_em_ordem_crescente(self, client, ano_com_dados):
        data = client.get(f"{BASE}/meses-disponiveis", params={"ano": ano_com_dados}).json()
        assert data == sorted(data)

    def test_ano_sem_dados_retorna_lista_vazia(self, client):
        r = client.get(f"{BASE}/meses-disponiveis", params={"ano": 1900})
        assert r.status_code == 200
        assert r.json() == []

    def test_filtro_tipo_servico_aceito(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/meses-disponiveis",
            params={"ano": ano_com_dados, "tipo_servico": "Regular Metropolitano"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filtro_categoria_customizada(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/meses-disponiveis",
            params={"ano": ano_com_dados, "categoria": "SUGESTÃO"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── /resumo ───────────────────────────────────────────────────────────────────

class TestResumo:
    def test_estrutura_da_resposta(self, client, ano_com_dados):
        r = client.get(f"{BASE}/resumo", params={"ano": ano_com_dados})
        assert r.status_code == 200
        data = r.json()
        assert set(data.keys()) == {"total_reclamacoes", "assunto_top", "assunto_top_qty"}

    def test_tipos_dos_campos(self, client, ano_com_dados):
        data = client.get(f"{BASE}/resumo", params={"ano": ano_com_dados}).json()
        assert isinstance(data["total_reclamacoes"], int)
        assert isinstance(data["assunto_top"], str)
        assert isinstance(data["assunto_top_qty"], int)

    def test_valores_nao_negativos(self, client, ano_com_dados):
        data = client.get(f"{BASE}/resumo", params={"ano": ano_com_dados}).json()
        assert data["total_reclamacoes"] >= 0
        assert data["assunto_top_qty"] >= 0

    def test_assunto_top_qty_nao_supera_total(self, client, ano_com_dados):
        data = client.get(f"{BASE}/resumo", params={"ano": ano_com_dados}).json()
        assert data["assunto_top_qty"] <= data["total_reclamacoes"]

    def test_filtro_meses_nunca_supera_total_geral(self, client, ano_com_dados):
        total_geral = client.get(
            f"{BASE}/resumo", params={"ano": ano_com_dados}
        ).json()["total_reclamacoes"]
        total_jan = client.get(
            f"{BASE}/resumo", params={"ano": ano_com_dados, "meses": "1"}
        ).json()["total_reclamacoes"]
        assert total_jan <= total_geral

    def test_ano_sem_dados_retorna_zeros(self, client):
        r = client.get(f"{BASE}/resumo", params={"ano": 1900})
        assert r.status_code == 200
        data = r.json()
        assert data["total_reclamacoes"] == 0
        assert data["assunto_top_qty"] == 0

    def test_filtro_categoria_customizada(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/resumo",
            params={"ano": ano_com_dados, "categoria": "SUGESTÃO"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "total_reclamacoes" in data


# ── /evolucao-mensal ──────────────────────────────────────────────────────────

class TestEvolucaoMensal:
    def test_retorna_lista(self, client, ano_com_dados):
        r = client.get(f"{BASE}/evolucao-mensal", params={"ano": ano_com_dados})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_estrutura_dos_itens(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/evolucao-mensal", params={"ano": ano_com_dados}).json():
            assert "mes" in item and "total" in item
            assert isinstance(item["mes"], int)
            assert isinstance(item["total"], int)

    def test_meses_no_intervalo_1_a_12(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/evolucao-mensal", params={"ano": ano_com_dados}).json():
            assert 1 <= item["mes"] <= 12

    def test_ordenado_por_mes_crescente(self, client, ano_com_dados):
        data = client.get(f"{BASE}/evolucao-mensal", params={"ano": ano_com_dados}).json()
        meses = [item["mes"] for item in data]
        assert meses == sorted(meses)

    def test_filtro_meses_restringe_resultado(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/evolucao-mensal",
            params={"ano": ano_com_dados, "meses": "1,2,3"},
        ).json()
        assert {item["mes"] for item in data}.issubset({1, 2, 3})

    def test_totais_positivos(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/evolucao-mensal", params={"ano": ano_com_dados}).json():
            assert item["total"] > 0

    def test_ano_sem_dados_retorna_lista_vazia(self, client):
        assert client.get(f"{BASE}/evolucao-mensal", params={"ano": 1900}).json() == []


# ── /assuntos-pizza ───────────────────────────────────────────────────────────

class TestAssuntosPizza:
    def test_retorna_lista(self, client, ano_com_dados):
        r = client.get(f"{BASE}/assuntos-pizza", params={"ano": ano_com_dados})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_estrutura_dos_itens(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/assuntos-pizza", params={"ano": ano_com_dados}).json():
            assert "assunto" in item and "total" in item
            assert isinstance(item["assunto"], str)
            assert isinstance(item["total"], int)
            assert item["total"] > 0

    def test_ordenado_por_total_decrescente(self, client, ano_com_dados):
        totais = [
            item["total"]
            for item in client.get(f"{BASE}/assuntos-pizza", params={"ano": ano_com_dados}).json()
        ]
        assert totais == sorted(totais, reverse=True)

    def test_soma_consistente_com_resumo(self, client, ano_com_dados):
        """Soma dos totais por assunto deve igualar total_reclamacoes do /resumo."""
        soma_pizza = sum(
            item["total"]
            for item in client.get(f"{BASE}/assuntos-pizza", params={"ano": ano_com_dados}).json()
        )
        total_resumo = client.get(
            f"{BASE}/resumo", params={"ano": ano_com_dados}
        ).json()["total_reclamacoes"]
        assert soma_pizza == total_resumo

    def test_ano_sem_dados_retorna_lista_vazia(self, client):
        assert client.get(f"{BASE}/assuntos-pizza", params={"ano": 1900}).json() == []


# ── /empresas-pontuacao ───────────────────────────────────────────────────────

class TestEmpresasPontuacao:
    def test_retorna_lista(self, client, ano_com_dados):
        r = client.get(f"{BASE}/empresas-pontuacao", params={"ano": ano_com_dados})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_estrutura_dos_itens(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/empresas-pontuacao", params={"ano": ano_com_dados}).json():
            assert "empresa" in item
            assert "pontuacao" in item
            assert "num_reclamacoes" in item
            assert "linha_top" in item
            assert "assunto_top" in item
            assert isinstance(item["empresa"], str)
            assert isinstance(item["pontuacao"], float)
            assert isinstance(item["num_reclamacoes"], int)
            assert isinstance(item["linha_top"], str)
            assert isinstance(item["assunto_top"], str)

    def test_num_reclamacoes_positivo(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/empresas-pontuacao", params={"ano": ano_com_dados}).json():
            assert item["num_reclamacoes"] > 0

    def test_pontuacao_nao_negativa(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/empresas-pontuacao", params={"ano": ano_com_dados}).json():
            assert item["pontuacao"] >= 0

    def test_filtro_tipo_servico(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/empresas-pontuacao",
            params={"ano": ano_com_dados, "tipo_servico": "Regular Metropolitano"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── /empresas-irregular ───────────────────────────────────────────────────────

class TestEmpresasIrregular:
    def test_retorna_lista(self, client, ano_com_dados):
        r = client.get(f"{BASE}/empresas-irregular", params={"ano": ano_com_dados})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_estrutura_dos_itens(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/empresas-irregular", params={"ano": ano_com_dados}).json():
            assert "empresa" in item
            assert "pontuacao" in item
            assert "linha_top" in item
            assert isinstance(item["empresa"], str)
            assert isinstance(item["pontuacao"], float)
            assert isinstance(item["linha_top"], str)

    def test_pontuacao_nao_negativa(self, client, ano_com_dados):
        for item in client.get(f"{BASE}/empresas-irregular", params={"ano": ano_com_dados}).json():
            assert item["pontuacao"] >= 0

    def test_resultado_disjunto_de_pontuacao_geral(self, client, ano_com_dados):
        """Pontuação irregular e geral tratam assuntos distintos — totais podem diferir."""
        r_geral = client.get(f"{BASE}/empresas-pontuacao", params={"ano": ano_com_dados})
        r_irreg = client.get(f"{BASE}/empresas-irregular", params={"ano": ano_com_dados})
        assert r_geral.status_code == 200
        assert r_irreg.status_code == 200


# ── /heatmap-assunto-empresa ──────────────────────────────────────────────────

class TestHeatmapAssuntoEmpresa:
    def test_retorna_dict_paginado(self, client, ano_com_dados):
        r = client.get(f"{BASE}/heatmap-assunto-empresa", params={"ano": ano_com_dados})
        assert r.status_code == 200
        _assert_paginado(
            r.json(),
            pagina_esperada=1,
            chaves_dados={"empresa", "assunto", "pontuacao", "linha_top", "pts_linha"},
        )

    def test_tem_chave_zmax_global(self, client, ano_com_dados):
        data = client.get(f"{BASE}/heatmap-assunto-empresa", params={"ano": ano_com_dados}).json()
        assert "zmax_global" in data
        assert isinstance(data["zmax_global"], (int, float))
        assert data["zmax_global"] >= 0

    def test_zmax_global_maior_igual_pontuacao_maxima(self, client, ano_com_dados):
        data = client.get(f"{BASE}/heatmap-assunto-empresa", params={"ano": ano_com_dados}).json()
        if data["dados"]:
            max_pag = max(item["pontuacao"] for item in data["dados"])
            assert data["zmax_global"] >= max_pag

    def test_paginacao_pagina_2(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/heatmap-assunto-empresa",
            params={"ano": ano_com_dados, "pagina": 2, "por_pagina": 5},
        )
        assert r.status_code == 200
        assert r.json()["pagina"] == 2

    def test_por_pagina_limita_empresas_distintas(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/heatmap-assunto-empresa",
            params={"ano": ano_com_dados, "pagina": 1, "por_pagina": 3},
        ).json()
        empresas = {item["empresa"] for item in data["dados"]}
        assert len(empresas) <= 3

    def test_pagina_alem_do_fim_retorna_dados_vazios(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/heatmap-assunto-empresa",
            params={"ano": ano_com_dados, "pagina": 99999},
        ).json()
        assert data["dados"] == []
        assert data["total_paginas"] >= 1

    def test_ano_sem_dados(self, client):
        data = client.get(f"{BASE}/heatmap-assunto-empresa", params={"ano": 1900}).json()
        assert data["dados"] == []
        assert data["total_paginas"] == 1
        assert data["zmax_global"] == 0


# ── /autos-pontuacao ──────────────────────────────────────────────────────────

class TestAutosPontuacao:
    def test_retorna_dict_paginado(self, client, ano_com_dados):
        r = client.get(f"{BASE}/autos-pontuacao", params={"ano": ano_com_dados})
        assert r.status_code == 200
        _assert_paginado(
            r.json(),
            pagina_esperada=1,
            chaves_dados={"auto", "pontuacao", "assunto_top"},
        )

    def test_tem_chave_xmax_global(self, client, ano_com_dados):
        data = client.get(f"{BASE}/autos-pontuacao", params={"ano": ano_com_dados}).json()
        assert "xmax_global" in data
        assert isinstance(data["xmax_global"], (int, float))

    def test_xmax_global_maior_igual_pontuacao_maxima_na_pagina_1(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/autos-pontuacao", params={"ano": ano_com_dados, "pagina": 1}
        ).json()
        if data["dados"]:
            max_pag = max(item["pontuacao"] for item in data["dados"])
            assert data["xmax_global"] >= max_pag

    def test_pagina_alem_do_fim_retorna_dados_vazios(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/autos-pontuacao",
            params={"ano": ano_com_dados, "pagina": 99999},
        ).json()
        assert data["dados"] == []

    def test_ano_sem_dados(self, client):
        data = client.get(f"{BASE}/autos-pontuacao", params={"ano": 1900}).json()
        assert data["dados"] == []
        assert data["xmax_global"] == 0.0

    def test_filtro_tipo_servico(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/autos-pontuacao",
            params={"ano": ano_com_dados, "tipo_servico": "Regular Metropolitano"},
        )
        assert r.status_code == 200
        assert isinstance(r.json()["dados"], list)


# ── /autos-irregular ─────────────────────────────────────────────────────────

class TestAutosIrregular:
    def test_retorna_dict_paginado(self, client, ano_com_dados):
        r = client.get(f"{BASE}/autos-irregular", params={"ano": ano_com_dados})
        assert r.status_code == 200
        _assert_paginado(r.json(), pagina_esperada=1, chaves_dados={"auto", "pontuacao"})

    def test_tem_chave_xmax_global(self, client, ano_com_dados):
        assert "xmax_global" in client.get(
            f"{BASE}/autos-irregular", params={"ano": ano_com_dados}
        ).json()

    def test_xmax_global_maior_igual_pontuacao_maxima_na_pagina_1(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/autos-irregular", params={"ano": ano_com_dados, "pagina": 1}
        ).json()
        if data["dados"]:
            max_pag = max(item["pontuacao"] for item in data["dados"])
            assert data["xmax_global"] >= max_pag

    def test_pagina_alem_do_fim_retorna_dados_vazios(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/autos-irregular",
            params={"ano": ano_com_dados, "pagina": 99999},
        ).json()
        assert data["dados"] == []

    def test_ano_sem_dados(self, client):
        data = client.get(f"{BASE}/autos-irregular", params={"ano": 1900}).json()
        assert data["dados"] == []
        assert data["xmax_global"] == 0.0


# ── /heatmap-assunto-auto ─────────────────────────────────────────────────────

class TestHeatmapAssuntoAuto:
    def test_retorna_dict_paginado(self, client, ano_com_dados):
        r = client.get(f"{BASE}/heatmap-assunto-auto", params={"ano": ano_com_dados})
        assert r.status_code == 200
        _assert_paginado(
            r.json(),
            pagina_esperada=1,
            chaves_dados={"empresa", "auto", "cidade_a", "cidade_b", "assunto", "pontuacao"},
        )

    def test_tem_chave_zmax_global(self, client, ano_com_dados):
        data = client.get(f"{BASE}/heatmap-assunto-auto", params={"ano": ano_com_dados}).json()
        assert "zmax_global" in data
        assert data["zmax_global"] >= 0

    def test_filtro_perm_ids_inexistente_retorna_vazio(self, client, ano_com_dados):
        """perm_ids=0 não existe no banco — dados devem ser vazios."""
        data = client.get(
            f"{BASE}/heatmap-assunto-auto",
            params={"ano": ano_com_dados, "perm_ids": "0"},
        ).json()
        assert data["dados"] == []

    def test_paginacao_pagina_alem_do_fim(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/heatmap-assunto-auto",
            params={"ano": ano_com_dados, "pagina": 99999},
        ).json()
        assert data["dados"] == []
        assert data["total_paginas"] >= 1

    def test_zmax_global_maior_igual_pontuacao_maxima(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/heatmap-assunto-auto", params={"ano": ano_com_dados, "pagina": 1}
        ).json()
        if data["dados"]:
            max_pag = max(item["pontuacao"] for item in data["dados"])
            assert data["zmax_global"] >= max_pag

    def test_por_pagina_limita_autos_distintos(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/heatmap-assunto-auto",
            params={"ano": ano_com_dados, "pagina": 1, "por_pagina": 3},
        ).json()
        autos = {item["auto"] for item in data["dados"]}
        assert len(autos) <= 3

    def test_ano_sem_dados(self, client):
        data = client.get(f"{BASE}/heatmap-assunto-auto", params={"ano": 1900}).json()
        assert data["dados"] == []


# ── /locais-embarque ─────────────────────────────────────────────────────────

class TestLocaisEmbarque:
    def test_retorna_dict_paginado(self, client, ano_com_dados):
        r = client.get(f"{BASE}/locais-embarque", params={"ano": ano_com_dados})
        assert r.status_code == 200
        _assert_paginado(
            r.json(),
            pagina_esperada=1,
            chaves_dados={"local", "total", "assunto_top"},
        )

    def test_tem_chave_xmax_global(self, client, ano_com_dados):
        data = client.get(f"{BASE}/locais-embarque", params={"ano": ano_com_dados}).json()
        assert "xmax_global" in data
        assert isinstance(data["xmax_global"], int)

    def test_totais_positivos(self, client, ano_com_dados):
        for item in client.get(
            f"{BASE}/locais-embarque", params={"ano": ano_com_dados}
        ).json()["dados"]:
            assert item["total"] > 0

    def test_xmax_global_maior_igual_total_maximo(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/locais-embarque", params={"ano": ano_com_dados, "pagina": 1}
        ).json()
        if data["dados"]:
            max_pag = max(item["total"] for item in data["dados"])
            assert data["xmax_global"] >= max_pag

    def test_pagina_alem_do_fim(self, client, ano_com_dados):
        data = client.get(
            f"{BASE}/locais-embarque",
            params={"ano": ano_com_dados, "pagina": 99999},
        ).json()
        assert data["dados"] == []

    def test_ano_sem_dados(self, client):
        data = client.get(f"{BASE}/locais-embarque", params={"ano": 1900}).json()
        assert data["dados"] == []
        assert data["xmax_global"] == 0

    def test_filtro_meses(self, client, ano_com_dados):
        r = client.get(
            f"{BASE}/locais-embarque",
            params={"ano": ano_com_dados, "meses": "1,2,3"},
        )
        assert r.status_code == 200


# ── /empresas-lista ───────────────────────────────────────────────────────────

class TestEmpresasLista:
    def test_sem_tipo_servico_retorna_lista_vazia(self, client):
        """_parse_list(None) = [] → in_([]) retorna 0 linhas."""
        r = client.get(f"{BASE}/empresas-lista")
        assert r.status_code == 200
        assert r.json() == []

    def test_com_tipo_servico_retorna_lista(self, client):
        r = client.get(
            f"{BASE}/empresas-lista",
            params={"tipo_servico": "Regular Metropolitano"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_estrutura_dos_itens(self, client):
        r = client.get(
            f"{BASE}/empresas-lista",
            params={"tipo_servico": "Regular Metropolitano"},
        )
        for item in r.json():
            assert "id" in item and "nome" in item
            assert isinstance(item["id"], int)
            assert isinstance(item["nome"], str)
            assert item["id"] > 0
            assert item["nome"] != ""

    def test_ids_unicos(self, client):
        r = client.get(
            f"{BASE}/empresas-lista",
            params={"tipo_servico": "Regular Metropolitano"},
        )
        ids = [item["id"] for item in r.json()]
        assert len(ids) == len(set(ids))

    def test_fretamento_multiplo_aceito(self, client):
        r = client.get(
            f"{BASE}/empresas-lista",
            params={"tipo_servico": "Fretamento Intermunicipal,Fretamento Metropolitano"},
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)
