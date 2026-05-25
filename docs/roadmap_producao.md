# Roadmap – Ida para Produção (2026)

> Criado em: 2026-05-25  
> Responsável: Thiago + equipe ARTESP

---

## Fase A – Correções e Melhorias (antes do estresse)

### A1. Seed de dados de 2026

- Gerar/importar os dados reais de ouvidorias de 2026 para o banco de produção (substituindo ou complementando o seed atual).

### A2. Bug – Nova Ouvidoria: troca para "fretamento" mantém autos vinculados

- **Problema:** ao preencher reclamações e trocar o tipo para "fretamento", o bloco de vínculo de autos permanece visível/preenchido, gerando dados inconsistentes.
- **Correção:** limpar e ocultar o seletor de autos ao detectar mudança de tipo para fretamento (usar `st.session_state` + rerun ou lógica condicional no formulário).

### A3. Resposta técnica – reorganizar UX

- Separar **edição da ouvidoria** em aba distinta da resposta técnica, reduzindo confusão para o técnico.
- Adicionar **resumo no topo** com: categorias vinculadas + autos vinculados (leitura rápida antes de responder).
- Estrutura sugerida para a página `04_Responder.py`:
  - Aba 1: "Responder" – formulário de resposta técnica.
  - Aba 2: "Editar Ouvidoria" – campos editáveis da ouvidoria.
  - Topo fixo: resumo de categorias e autos.

---

## Fase B – Testes e Usuários

### B1. Teste de estresse junto com Thiago

- Simular uso intensivo: múltiplos registros simultâneos, filtros extremos, relatórios pesados.
- Checar: tempo de resposta, erros de sessão, DetachedInstanceError, travamentos do Streamlit.
- Registrar bugs encontrados e abrir itens de correção.

### B2. Criar logins para todos os usuários respondentes

- Levantar lista de técnicos/gestores que responderão ouvidorias.
- Criar contas via `05_Admin.py` ou script, definindo: nome, e-mail, senha inicial, gerência, coordenação, tipo (gestor/técnico).
- Comunicar credenciais individualmente.

---

## Fase C – Capacitação

### C1. Reunião de treinamento com os usuários

- Demonstração ao vivo do sistema: login, criação de ouvidoria, resposta técnica, relatórios.
- Tirar dúvidas e coletar feedback inicial.

### C2. Vídeo-manual de uso

- Gravar vídeo curto (screencast) cobrindo os fluxos principais:
  1. Login e navegação
  2. Criar ouvidoria + vincular reclamações
  3. Responder como técnico
  4. Gerar relatório
- Disponibilizar link/arquivo para os usuários.

---

## Fase D – Produção (paralela às fases B e C)

> Executar em paralelo com B e C assim que o seed de 2026 estiver validado.

### D1. Preparar ambiente de produção

- Revisar variáveis `.env` para produção (host, porta, credenciais do banco).
- Garantir que o servidor de produção tem Python 3.14 + dependências instaladas.
- Rodar `python database/seed.py` com dados de 2026 no servidor de produção.

### D2. Deploy do app

- Subir `streamlit run app.py` como serviço (systemd / supervisor / Docker).
- Configurar proxy reverso (nginx ou similar) se necessário.
- Testar acesso externo antes de divulgar.

### D3. Checklist pré-go-live

- [ ] Seed de 2026 executado e validado
- [ ] Bug A2 corrigido
- [ ] UX de resposta técnica (A3) corrigida
- [ ] Logins de todos os usuários criados
- [ ] Teste de estresse concluído (B1) sem erros críticos
- [ ] Vídeo-manual gravado (C2)
- [ ] Acesso externo testado

---

## Ordem de Execução Recomendada

```
A1 → A2 → A3
        ↓
       B1 (estresse com Thiago)
        ↓
       B2 (criar logins)
       C1 + C2 (treinamento e vídeo)  ←── em paralelo com D1 + D2 (produção)
        ↓
       D3 (go-live)
```
