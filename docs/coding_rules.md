# Regras de Código – Sistema de Ouvidorias ARTESP

## 1. Separação de Camadas (regra principal)

```
pages/  →  utils/  →  repositories/  →  models/ + database/
```

- **pages/** nunca importa `repositories/`, nunca chama `db_session()` diretamente.
- **utils/** é o único intermediário entre páginas e banco. Pode importar de `repositories/` e `models/`.
- **repositories/** não importa `streamlit`. Não tem lógica de apresentação. Só ORM e SQL.
- **models/** não tem dependências externas além de SQLAlchemy.

```python
# ❌ ERRADO — page fazendo query direta
# pages/03_Detalhe_Ouvidoria.py
with db_session() as s:
    o = s.query(Ouvidoria).filter_by(id=oid).first()

# ✅ CORRETO — page chama utils
from utils import carregar_detalhe_ouvidoria
o, recs, rec_autos, ... = carregar_detalhe_ouvidoria(oid)
```

---

## 2. Sessões de Banco de Dados

### Use sempre `db_session()` (context manager)

```python
# Leitura — expunge_all libera objetos antes de retornar
with db_session() as s:
    objs = s.query(Modelo).options(...).all()
    s.expunge_all()
    return objs

# Escrita — commit automático ao sair do with
with db_session() as s:
    s.add(NovoObjeto(...))
```

### Nunca retorne objetos SQLAlchemy vivos fora da sessão

Após `session.close()` ou `session.expunge_all()`, atributos simples funcionam mas relacionamentos lazy causam `DetachedInstanceError`. Os loaders em `utils/` convertem para `dict` antes de retornar à page.

````python
# ❌ ERRADO
with db_session() as s:
    o = s.query(Ouvidoria).filter_by(id=oid).first()
return o   # page vai explodir ao acessar o.reclamacoes[0].categoria.nome

---

## 3. Utils — Loaders e Ops

### Loaders: cache + formatação

Loaders em `utils/loaders_*.py` são wrappers que:
1. Chamam o repositório correspondente.
2. Convertem objetos ORM para `dict` ou lista de tuplas para a UI.
3. Aplicam `@st.cache_data(ttl=N)` quando o dado é caro ou raramente muda.

```python
@st.cache_data(ttl=300)
def carregar_municipios():
    return [m.nome for m in get_municipios_sp()]
````

### Ops: fachadas de escrita

Arquivos `*_ops.py` em `utils/` são fachadas que:

1. Chamam o repositório de escrita correto.
2. Adicionam lógica de coordenação frontend (ex: invalidar cache após escrita).
3. Nunca duplicam lógica SQL — delegam tudo ao repositório.

```python
# utils/ouvidoria_ops.py
def atribuir_tecnico(ouvidoria_id, tecnico_id):
    return _atribuir_tecnico(ouvidoria_id, tecnico_id)   # delega ao repo
```

### Quando invalidar cache

Após qualquer escrita que afete dados cacheados, chame `.clear()` + `st.rerun()`:

```python
from utils import carregar_tecnicos_disponiveis
criar_usuario(...)
carregar_tecnicos_disponiveis.clear()
st.rerun()
```

---

## 4. Streamlit — Formulários e Estado

### Nunca coloque seletores dinâmicos dentro de `st.form()`

`st.form()` bloqueia reruns até o submit. Seletores que dependem uns dos outros (ex: Gerência → Coordenação) devem ficar **fora** do form:

```python
# FORA do form — atualiza ao trocar gerência
ger_sel = st.selectbox("Gerência", gerencias, key="nu_gerencia")
coords = carregar_coordenacoes(ger_map.get(ger_sel))
coord_sel = st.selectbox("Coordenação", coords, key="nu_coordenacao")

# DENTRO do form — apenas campos que não dependem de outros
with st.form("form_novo"):
    nome = st.text_input("Nome")
    criar = st.form_submit_button("Criar")
```

### Use `st.toast()` + `st.rerun()` para feedback após ações

```python
# ❌ st.success() some antes do rerun visualizar
st.success("Feito!")
st.rerun()

# ✅ st.toast() persiste após o rerun
st.toast("Feito!", icon="✅")
st.rerun()
```

### Limpe o estado ao navegar entre páginas

Ao usar `st.switch_page()`, limpe o estado de sessão relacionado à página anterior:

```python
st.session_state.pop("resp_recs_edit", None)
st.session_state.pop("resp_autos_checklist", None)
st.switch_page("pages/05_Responder.py")
```

---

## 5. Modelos SQLAlchemy

### Use `mapped_column` e `Mapped` (SQLAlchemy 2.0)

```python
class Exemplo(Base):
    __tablename__ = "exemplos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    campo_opcional: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

### Cascade delete em relacionamentos pai→filho

```python
reclamacoes: Mapped[list["Reclamacao"]] = relationship(
    back_populates="ouvidoria", cascade="all, delete-orphan"
)
```

### Não faça lazy load fora de sessão

Prefira `.joinedload()` no repositório. Acesse relacionamentos apenas enquanto a sessão (ou os objetos expunged) permitir.

---

## 6. Estrutura padrão de cada página

```python
"""Docstring descritiva da página."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from utils import carregar_detalhe_ouvidoria, atribuir_tecnico   # via utils/__init__

st.set_page_config(page_title="...", page_icon="...", layout="wide")
auth.require_auth()   # ou auth.require_gestor() para páginas restritas

u = usuario_logado()

with st.sidebar:
    st.markdown(f"**{u.nome}**")
    ...
```

### Guards de acesso

| Função                  | Uso                          |
| ----------------------- | ---------------------------- |
| `auth.require_auth()`   | Qualquer usuário autenticado |
| `auth.require_gestor()` | Apenas gestores              |

---

## 7. Nomenclatura

| Tipo                       | Convenção                                 | Exemplo                                           |
| -------------------------- | ----------------------------------------- | ------------------------------------------------- |
| Tabelas SQL                | `snake_case` plural                       | `autos_linha`, `ouvidoria_tecnicos`               |
| Classes Python             | `PascalCase`                              | `AutoLinha`, `OuvidoriaTecnico`                   |
| Funções                    | `snake_case`                              | `carregar_ouvidorias()`                           |
| Chaves `session_state`     | `snake_case`                              | `ouvidoria_id`, `resp_recs_edit`                  |
| Arquivos de página         | `NN_NomePagina.py`                        | `01_Ouvidorias.py`                                |
| Chaves de widget Streamlit | `prefixo_descricao`                       | `resp_cat_42`, `trecho_orig`                      |
| Funções de repositório     | `get_*` (leitura), verbo direto (escrita) | `get_ouvidoria_completa`, `criar_usuario`         |
| Funções de loader          | `carregar_*` ou `query_*`                 | `carregar_municipios`, `query_kpis_produtividade` |

---

## 8. Detecção de Colunas em CSVs

CSVs de dados têm colunas com caracteres especiais (acentos, °). Use o helper `_col()` em vez de acessar diretamente pelo nome:

```python
def _col(df, *candidates):
    """Retorna o primeiro nome de coluna que existe no DataFrame (case-insensitive)."""
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None

col_perm = _col(df, "Permissionária", "Permissionaria") or \
           next((c for c in df.columns if "permiss" in c.lower()), None)
```

---

## 9. Cache em Streamlit

Use `@st.cache_data(ttl=N)` nos loaders de `utils/`:

| TTL       | Usado para                                                                 |
| --------- | -------------------------------------------------------------------------- |
| `ttl=300` | Catálogos raramente alterados (municípios, permissionárias, gerências)     |
| `ttl=120` | Queries de dashboard                                                       |
| `ttl=60`  | Dados semi-dinâmicos (técnicos disponíveis, ouvidoria para permissionária) |

Após qualquer escrita que afete dados cacheados, invalide com `.clear()`.

---

## 10. Segurança

- Senhas sempre hasheadas com bcrypt — nunca armazenar texto plano.
- Não expor stacktraces ao usuário final — use `st.error("Mensagem amigável")`.
- Variáveis de ambiente em `.env` (não versionar). Usar `python-dotenv`.
- Validar campos obrigatórios antes de persistir no banco.

---

## 11. Contratos de Dados (TypedDict)

### Regra fundamental

**Repositórios de leitura NUNCA retornam instâncias SQLAlchemy fora da sessão.**
Toda conversão ORM → dados acontece dentro do bloco `with db_session() as s:`, eliminando
a necessidade de `expunge_all()` e "objetos zumbi" com estado implícito.

### Onde ficam as definições

Todos os TypedDicts do projeto estão em `repositories/types.py`.

### Funções de repositório → TypedDict

```python
# repositories/types.py
class MunicipioDict(TypedDict):
    id: int
    nome: str
    estado: str
    cod_ibge: str | None
    populacao: int | None

# repositories/municipios_repo.py
def get_municipios_sp() -> list[MunicipioDict]:
    with db_session() as s:
        munis = s.query(Municipio).filter_by(estado="SP").order_by(Municipio.nome).all()
        return [MunicipioDict(id=m.id, nome=m.nome, ...) for m in munis]
        # ✅ Sessão fecha aqui — nenhum objeto ORM sai vivo
```

### Loaders em utils/ — recebem TypedDicts, não objetos ORM

```python
# utils/loaders_catalog.py
def carregar_categorias():
    return [(c["id"], c["nome"]) for c in get_categorias() if c["ativo"]]
    # ✅ Acesso via ["key"] — sem risco de DetachedInstanceError
```

### TypedDicts aninhados (Ouvidoria)

Para entidades complexas com relacionamentos, use TypedDicts aninhados construídos
com funções helper privadas dentro do repositório:

```python
# repositories/ouvidoria_repo.py

def _to_reclamacao_dict(r: Reclamacao) -> ReclamacaoDict:
    return ReclamacaoDict(
        id=r.id,
        categoria_nome=r.categoria.nome if r.categoria else None,
        autos=[ReclamacaoAutoDict(auto_id=ra.auto.id, ...) for ra in r.autos_vinculados],
        ...
    )

def get_ouvidoria_completa(oid: int) -> OuvidoriaDetalheDict | None:
    with db_session() as s:
        o = s.query(Ouvidoria).options(joinedload(...)).filter_by(id=oid).first()
        if not o:
            return None
        return _to_detalhe(o)   # conversão dentro da sessão
```

### Exceções — retorno de primitivos/tuples é aceito

Para queries agregadas (dashboards), retornar tuples/scalars diretamente é correto
e não requer TypedDicts:

```python
# repositories/dashboard/produtividade_repo.py
def query_kpis_produtividade(...) -> tuple[int, int, int]:
    with db_session() as s:
        return s.query(func.count(), ...).one()
        # ✅ Tuples de scalars — sem objetos ORM
```

### O que é proibido

```python
# ❌ PROIBIDO — objeto ORM fora da sessão
with db_session() as s:
    o = s.query(Ouvidoria).filter_by(id=oid).first()
    s.expunge_all()
return o   # "objeto zumbi": relacionamentos lazy vão lançar DetachedInstanceError

# ❌ PROIBIDO — expunge_all() como muleta
with db_session() as s:
    objs = s.query(Modelo).options(joinedload(...)).all()
    s.expunge_all()
    return objs   # Contrato implícito; cria acoplamento frágil entre repo e loader
```
