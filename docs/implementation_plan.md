# DashForge AI — Implementation Plan

> Aplicação web que atua como um **analista de dados virtual**: coleta requisitos conversacionalmente, detecta gaps e inconsistências, valida tudo antes de construir, gera o arquivo `.pbip` e itera sobre o que já foi feito sem reconstruir do zero.

---

## Visão do Produto

**Usuário-alvo:** pessoa leiga que precisa de um dashboard de qualidade no Power BI mas não sabe usar a ferramenta.

**Fluxo principal:**
```
Usuário descreve o que quer
    → Agente faz perguntas (uma por vez) até ter tudo necessário
    → Valida a solicitação (detecta erros conceituais, dados faltando)
    → Mostra resumo do que vai ser construído (para aprovação)
    → Gera o projeto .pbip
    → Usuário pode pedir ajustes → agente itera sem reconstruir do zero
```

**O diferencial:** o agente não é só gerador de código — ele assume o papel de analista, questiona solicitações ruins, sugere melhorias, e preserva o estado do projeto entre iterações.

---

## Arquitetura

```
Browser (React + shadcn/ui)
        ↕ HTTP / WebSocket (SSE)
FastAPI Server
    ├── /api/projects          ← CRUD de projetos (estado persistido)
    ├── /api/chat              ← conversa com o agente
    ├── /api/build             ← dispara a geração do .pbip
    └── /api/download/{id}     ← retorna o ZIP do projeto
        ↕
Agent System (Agno)
    ├── RequirementsAgent      ← coleta requisitos, detecta gaps, valida
    ├── DesignAgent            ← decide layout, páginas, visuais
    ├── BuildAgent             ← gera arquivos PBIR (TMDL + JSON)
    └── ReviewAgent            ← valida o output antes de entregar
        ↕
State Store (SQLite → PostgreSQL)
    └── Project: {id, status, spec, files, conversation_history, iterations}
        ↕
PBIR Tools (src/tools/)
    ├── excel_reader.py        ← lê e perfila dados do usuário
    ├── tmdl_writer.py         ← gera model.tmdl, tabelas, medidas DAX
    ├── pbir_writer.py         ← gera visual.json com schema 2.7.0 correto
    ├── pbir_validator.py      ← valida JSON antes de salvar
    └── project_packager.py    ← monta .pbip → ZIP
```

---

## Tech Stack

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| **Backend** | Python 3.11+ + FastAPI | Async, rápido, ótimo para SSE |
| **Agentes** | Agno | Menos boilerplate, performance, decisão já tomada |
| **LLM** | Claude (Anthropic) / OpenAI configurável | Qualidade de raciocínio para análise de requisitos |
| **Estado** | SQLite (dev) → PostgreSQL (prod) | Simples de começar, fácil de migrar |
| **Frontend** | React + shadcn/ui + Tailwind v4 | Já tem tema shadcn no projeto |
| **Deploy** | Docker + Railway/Render (MVP) | Simples, gratuito para começar |

### Sobre Agno vs LangGraph

**Manter Agno.** O argumento para LangGraph seria o gerenciamento de estado em workflows complexos com muitas ramificações — mas nosso fluxo é relativamente linear. O estado do projeto vive em banco de dados (não no framework), e o Agno já tem memória de sessão embutida. LangGraph só faria sentido se o grafo de execução ficasse complexo demais para gerenciar manualmente.

**Reavalie se:** o fluxo de coleta de requisitos precisar de muitas ramificações condicionais com rollback de estado.

---

## O ProjectSpec — Coração do Sistema

O `ProjectSpec` é um documento JSON estruturado que captura **tudo** que o agente sabe sobre o projeto. É a fonte da verdade. Toda iteração começa lendo o spec, não a conversa.

```json
{
  "id": "proj_abc123",
  "version": 3,
  "status": "building | ready | iterating",
  "client": {
    "name": "João",
    "domain": "vendas",
    "technical_level": "leigo"
  },
  "data_sources": [
    {
      "file": "vendas_2024.xlsx",
      "tables": ["Vendas", "Produtos", "Metas"],
      "profile": { "rows": 12000, "date_range": "2024-01-01/2024-12-31" }
    }
  ],
  "requirements": {
    "pages": [
      {
        "name": "Visão Geral",
        "purpose": "KPIs executivos de vendas",
        "visuals": ["card_receita", "card_vendas", "bar_vendas_mensais", "pie_categorias"],
        "confirmed": true
      }
    ],
    "kpis": ["Receita Total", "Ticket Médio", "Meta vs Realizado"],
    "theme": "dark",
    "confirmed_at": "2025-04-21T14:00:00"
  },
  "open_questions": [
    "Qual o período padrão ao abrir o relatório?",
    "Precisa de filtro por região?"
  ],
  "iterations": [
    { "version": 1, "change": "adicionou KPI de ticket médio", "timestamp": "..." }
  ]
}
```

**Por que isso resolve o problema de "reconstruir do zero":** ao pedir uma alteração, o agente lê o spec, entende o estado atual, modifica apenas a parte relevante (ex: adiciona um visual na página 2), e regera apenas os arquivos afetados.

---

## O RequirementsAgent — Diferencial do Produto

Este é o agente mais importante. Ele age como um **analista sênior de dados** que:

1. **Faz uma pergunta por vez** — nunca despeja um formulário inteiro
2. **Detecta ambiguidades:** "dashboard de vendas" → pergunta: de quais vendas? período? por quê?
3. **Corrige erros conceituais:** gauge para KPI único → sugere card; pizza com muitas fatias → sugere barra
4. **Sabe quando parar de perguntar** — quando o spec tem informação suficiente para construir
5. **Resume antes de construir** — "Vou criar X com Y visuais em Z páginas. Confirma?"

```
Instructions do RequirementsAgent:
- Você é um analista de dados sênior ajudando um usuário leigo
- Faça UMA pergunta por mensagem
- Se o usuário pedir um visual inadequado para os dados, explique o problema e sugira alternativa
- Só avance para build quando tiver: fonte de dados, objetivo, páginas principais, KPIs
- Nunca use jargão técnico sem explicar
```

---

## Fases de Desenvolvimento

### Fase 0 — Setup (1-2 dias)
- [ ] Criar repo `dashforge-ai/` com estrutura de pastas
- [ ] `pyproject.toml` + dependências (fastapi, agno, anthropic, pandas, openpyxl)
- [ ] `.env.example` com variáveis necessárias
- [ ] Copiar templates PBIP base (do projeto Databrick Gov)
- [ ] Script de teste: lê um visual.json e valida com as regras do `pbir_research_and_learnings.md`

### Fase 1 — Pipeline de Build (núcleo técnico)
Objetivo: dado um `ProjectSpec` completo, gerar o `.pbip` correto.

- [ ] `excel_reader.py` — lê Excel/CSV, retorna perfil de dados (colunas, tipos, amostras)
- [ ] `tmdl_writer.py` — gera arquivos de modelo (tabelas, relacionamentos, medidas DAX)
- [ ] `pbir_writer.py` — gera `visual.json` com o schema 2.7.0 correto (usar `pbir_research_and_learnings.md`)
- [ ] `pbir_validator.py` — valida antes de salvar, evita os erros conhecidos
- [ ] `project_packager.py` — monta estrutura PBIP e gera ZIP
- [ ] **Teste de integração:** `ProjectSpec` fixo → ZIP → abrir no Power BI Desktop

### Fase 2 — Agente de Requisitos (o analista)
Objetivo: conversa em terminal (CLI) que preenche um `ProjectSpec`.

- [ ] `RequirementsAgent` com Agno — instrução de analista sênior
- [ ] Lógica de detecção de gaps (quais campos do spec ainda faltam)
- [ ] Validação de consistência (dados disponíveis vs visuais pedidos)
- [ ] Estado de conversa persistido em SQLite
- [ ] **Teste:** conversa em terminal → spec completo → chama build → gera ZIP

### Fase 3 — API + Web (FastAPI)
Objetivo: expor o sistema via API para o frontend.

- [ ] FastAPI setup com rotas básicas
- [ ] SSE endpoint para streaming das respostas do agente
- [ ] Upload de arquivo Excel
- [ ] Gerenciamento de projetos (criar, listar, carregar)
- [ ] Endpoint de download do ZIP gerado

### Fase 4 — Frontend (última prioridade)
Objetivo: interface web estilo Canva AI (inspiração nas screenshots).

- [ ] React + shadcn/ui + Tailwind
- [ ] Chat conversacional com streaming
- [ ] Preview do dashboard (wireframe React dos visuais)
- [ ] Upload de arquivo
- [ ] Histórico de projetos

---

## Princípios de Desenvolvimento

1. **Escreva código junto:** cada fase deve ser desenvolvida com o usuário aprendendo o que está sendo feito e por quê.
2. **Teste cedo no Power BI Desktop:** toda mudança no schema PBIR deve ser testada abrindo o arquivo.
3. **O `pbir_research_and_learnings.md` é o oráculo:** antes de escrever qualquer JSON de visual, consultar o que já foi descoberto.
4. **Frameworks só se trouxerem ganho real:** se Agno resolver com 10 linhas o que LangGraph resolveria com 50, mantém Agno.
5. **Estado no banco, não no framework:** o `ProjectSpec` no banco é a fonte da verdade, não a memória do agente.

---

## Conexão com a Pesquisa PBIR

O arquivo `pbir_research_and_learnings.md` documenta os aprendizados de como manipular arquivos `.pbip`. Todo padrão descoberto lá alimenta diretamente o `pbir_writer.py` e o `pbir_validator.py`. A estratégia continua: quando o agente precisar de um novo tipo de visual, primeiro testar manualmente no Power BI Desktop, descobrir o JSON gerado, e só então codificar o gerador.
