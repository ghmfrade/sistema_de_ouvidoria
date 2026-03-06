# Regras de Código – Sistema de Ouvidorias ARTESP

## 1. Sessões de Banco de Dados

### Use o helper correto para cada caso

```python
# LEITURA — fechar manualmente no finally
session = get_session()
try:
    resultado = session.query(Modelo).filter_by(...).all()
    dados = [{"id": r.id, "nome": r.nome} for r in resultado]  # ← converte aqui
    return dados
finally:
    session.close()

# ESCRITA — use o context manager (commit/rollback automático)
with db_session() as session:
    session.add(NovoObjeto(...))
    # commit acontece ao sair do with
```

### Nunca retorne objetos SQLAlchemy vivos

Sempre converta para `dict` **enquanto a sessão está aberta**. Retornar objetos após `session.close()` ou `session.expunge_all()` causará `DetachedInstanceError` ao acessar relacionamentos lazy.

```python
# ❌ ERRADO
session.close()
return objeto_sqlalchemy  # vai explodir ao acessar r.categoria.nome

# ✅ CORRETO
dados = {"categoria": r.categoria.nome if r.categoria else None}
session.close()
return dados
```

---

## 2. Streamlit — Formulários e Estado

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

Ao usar `st.switch_page()`, limpe o estado de sessão relacionado à página anterior para evitar dados "fantasma":

```python
st.session_state.pop("resp_recs_edit", None)
st.session_state.pop("resp_autos_checklist", None)
st.switch_page("pages/04_Responder.py")
```

---

## 3. Modelos SQLAlchemy

### Use `mapped_column` e `Mapped` (SQLAlchemy 2.0)

```python
# ✅ Estilo correto (SQLAlchemy 2.0)
class Exemplo(Base):
    __tablename__ = "exemplos"
    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    campo_opcional: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

### Cascade delete em relacionamentos pai→filho

```python
# Ao deletar Ouvidoria, deletar automaticamente reclamações, atribuições e respostas
reclamacoes: Mapped[list["Reclamacao"]] = relationship(
    back_populates="ouvidoria", cascade="all, delete-orphan"
)
```

### Não faça lazy load fora de sessão

Prefira `.joinedload()` ou acesse os dados dentro da sessão aberta.

---

## 4. Páginas Streamlit

### Estrutura padrão de cada página

```python
"""Docstring descritiva da página."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import auth
from auth import usuario_logado
from database.connection import db_session, get_session
from models import ...

st.set_page_config(page_title="...", page_icon="...", layout="wide")
auth.require_auth()   # ou auth.require_gestor() para páginas restritas

u = usuario_logado()

# Sidebar com nome do usuário + botão Sair
with st.sidebar:
    st.markdown(f"**{u.nome}**")
    ...

# Corpo da página
```

### Guards de acesso

| Função | Uso |
|---|---|
| `auth.require_auth()` | Qualquer usuário autenticado |
| `auth.require_gestor()` | Apenas gestores |

---

## 5. Nomenclatura

| Tipo | Convenção | Exemplo |
|---|---|---|
| Tabelas SQL | `snake_case` plural | `autos_linha`, `ouvidoria_tecnicos` |
| Classes Python | `PascalCase` | `AutoLinha`, `OuvidoriaTecnico` |
| Funções | `snake_case` | `carregar_ouvidorias()` |
| Chaves `session_state` | `snake_case` | `ouvidoria_id`, `resp_recs_edit` |
| Arquivos de página | `NN_NomePagina.py` | `01_Ouvidorias.py` |
| Chaves de widget Streamlit | `prefixo_descricao` | `resp_cat_42`, `trecho_orig` |

---

## 6. Detecção de Colunas em CSVs

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

# Uso
col_perm = _col(df, "Permissionária", "Permissionaria") or \
           next((c for c in df.columns if "permiss" in c.lower()), None)
```

---

## 7. Cache em Streamlit

Use `@st.cache_data(ttl=300)` para funções de leitura de dados auxiliares (categorias, cidades, permissionárias, autos). Lembre-se de invalidar o cache quando os dados mudarem:

```python
@st.cache_data(ttl=300)
def listar_tecnicos():
    ...

# Após adicionar um técnico:
listar_tecnicos.clear()
st.rerun()
```

---

## 8. Segurança

- Senhas sempre hasheadas com bcrypt — nunca armazenar texto plano.
- Não expor stacktraces ao usuário final — use `st.error("Mensagem amigável")`.
- Variáveis de ambiente em `.env` (não versionar). Usar `python-dotenv`.
- Validar campos obrigatórios antes de persistir no banco.
