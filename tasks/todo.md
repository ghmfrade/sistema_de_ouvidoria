# TODO – Sistema de Ouvidorias ARTESP

> Atualizado em: 2026-03-05

---

## ✅ Concluído (Fase 1 – Core)

- [x] Modelos SQLAlchemy (todos, incluindo `ParadaAutoLinha`)
- [x] Banco inicializado e dados importados (CSVs Latin-1)
- [x] Autenticação com bcrypt + `st.session_state`
- [x] Login (app.py)
- [x] Lista de ouvidorias com filtros, cores de status, ocultar concluídos
- [x] Botões de ação na listagem: abrir (🔍), responder (✍️), concluir/excluir (⚙)
- [x] Coluna "Coord./Gerência" com retorno automático para SUCOL após respostas
- [x] Coluna "Responsáveis" (técnicos pendentes)
- [x] Criar ouvidoria com reclamações (categoria obrigatória)
- [x] Busca de autos por trecho (EXISTS em `paradas_auto_linha`), permissionária e número
- [x] Checklist acumulada de autos
- [x] Detalhe de ouvidoria: reclamações com autos (origem, destino, empresa)
- [x] Atribuição de técnicos
- [x] Edição de ouvidoria (SEI, prazo, status)
- [x] Concluir e Excluir ouvidoria (com confirmação)
- [x] Resposta técnica: edição completa de reclamações + busca de autos + registrar resposta
- [x] Transição automática para "Retorno técnico" quando todos respondem
- [x] Admin: usuários (com coordenação dinâmica), categorias, gerências, coordenações
- [x] Ativar/Desativar usuário com refresh imediato (`st.toast` + `st.rerun`)

---

## 🔲 Fase 2 – Dashboards

### Dashboard 1 – Produtividade

- [ ] Total de ouvidorias por período (mensal/trimestral)
- [ ] Ouvidorias por status
- [ ] Tempo médio de resposta por técnico / coordenação
- [ ] Ouvidorias vencidas (prazo expirado)
- [ ] Ranking de coordenações por volume de atendimento

### Dashboard 2 – Qualidade / Fiscalização

- [ ] Autos com maior número de reclamações (top N)
- [ ] Permissionárias com maior volume de reclamações
- [ ] Mapa de reclamações por trecho (cidade A → cidade B)
- [ ] Reclamações por categoria
- [ ] Pontuação acumulada por auto de linha (soma das pontuações de `reclamacao_autos`)
- [ ] Filtros: período, gerência, categoria, permissionária

---

## 🔲 Melhorias Futuras (identificadas)

### UX / Funcionalidades

- [ ] Paginação na lista de ouvidorias (para volumes grandes)
- [ ] Exportar lista de ouvidorias para Excel/CSV
- [ ] Histórico de alterações de status por ouvidoria
- [ ] Campo "observações internas" na ouvidoria (visível só ao gestor)

### Técnico

- [ ] Índices compostos no banco para queries pesadas do dashboard
- [ ] Testes automatizados (pytest) para funções de negócio
- [ ] Script de backup do banco de dados
- [ ] Containerização (Docker Compose: app + postgres)

---

## 🐛 Bugs Conhecidos / Pontos de Atenção

- `print(encontrados)` no `02_Nova_Ouvidoria.py` linha ~219 — remover antes de produção
- Cache `@st.cache_data` nos carregamentos de dados pode exibir dados desatualizados por até 5 minutos após alterações no Admin. TTL pode ser reduzido conforme necessidade.
- O campo `pontuacao` em `reclamacao_autos` é recalculado como `1/n_autos` a cada edição da resposta técnica, perdendo valores anteriores — avaliar se deve ser auditado.
