# DashForge AI

<<<<<<< HEAD
Gere dashboards profissionais no Power BI a partir de linguagem natural — sem precisar abrir o Power BI Desktop.
=======
App that Generate professional Power BI dashboards from natural language — no Power BI Desktop required.
>>>>>>> 58c4cb0723e5567e3b69fd8b1071db60eda98395

DashForge AI é um backend com IA que converte requisitos em linguagem natural em arquivos `.pbip` prontos para abrir. Ele combina um agente conversacional de requisitos (construído com Claude + Agno) com um pipeline determinístico de geração de código PBIR, garantindo saída correta sempre.

---

## O que este repositório contém

| Pasta / Arquivo | Descrição |
|---|---|
| `dashforge-ai/` | Aplicação Python — backend FastAPI + agente de IA + gerador de PBIP |
| `Databrick Gov/` | Dashboard de referência: análise de licitações do Exército Brasileiro (2019–2024) |
| `CONTRATAÇÕES - DGT.pbip` | Dashboard de referência: contratações governamentais |
| `Projeto para aprendizado/` | Projeto de estudo usado como referência de design ("Governança BI") |
| `projeto.pbip` | Template PBIP mínimo para iniciar novos projetos |
| `pbir_research_and_learnings.md` | Referência técnica com 4.000 linhas sobre o formato PBIR/TMDL |
| `docs/` | Decisões de arquitetura, plano de implementação, checklist de tarefas |

---

## Como funciona

```
Usuário descreve o que precisa
        ↓
RequirementsAgent (Claude + Agno)
  → faz uma pergunta de cada vez
  → detecta lacunas e evita decisões ruins de design
  → gera um ProjectSpec estruturado (JSON)
        ↓
Pipeline de Geração PBIP
  → lê dados Excel / CSV
  → escreve TMDL (modelo semântico + medidas DAX)
  → escreve Report JSON (visuais, páginas, bindings)
  → valida contra o schema PBIR 2.7.0
  → empacota o arquivo .pbip
        ↓
Usuário abre o arquivo no Power BI Desktop
```

---

## Stack tecnológica

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| API | FastAPI + Uvicorn (SSE para streaming em tempo real) |
| IA | Claude API (Anthropic) + framework Agno |
| Banco de dados | SQLite (dev) → PostgreSQL (prod) via SQLAlchemy + aiosqlite |
| Dados | Pandas, OpenPyXL |
| Frontend (planejado) | React + shadcn/ui + Tailwind CSS v4 |
| Análises | Prophet (previsão de séries temporais), decomposição STL |
| Visuais customizados | Deneb / Vega-Lite |
| Testes | pytest, pytest-asyncio, httpx |

---

## Status do projeto

- [x] Fase 0 — Configuração inicial (pyproject.toml, config, estrutura de pastas)
- [x] Pesquisa — Referência PBIR/TMDL com 4.000 linhas validada contra dashboards reais
- [x] Dashboards de referência — Databrick Gov (37 visuais, 38 medidas DAX, previsão)
- [ ] Fase 1 — Pipeline de geração (módulos: leitor Excel, escritor TMDL, escritor PBIR, validador, empacotador)
- [ ] Fase 2 — Agente de requisitos (coleta conversacional de especificações)
- [ ] Fase 3 — API REST + streaming SSE
- [ ] Fase 4 — Frontend React

---

## Como começar

### Pré-requisitos

- Python 3.11+
- Uma [chave de API da Anthropic](https://console.anthropic.com/)

### Instalação

```bash
git clone https://github.com/AbreuVin/DashForge-AI
cd dashforge-ai/dashforge-ai
cp .env.example .env          # adicione sua ANTHROPIC_API_KEY
pip install -e ".[dev]"
```

### Executar a API

```bash
uvicorn src.api:app --reload
```

---

## Dashboards de referência

### Databrick Gov — Licitações do Exército Brasileiro (2019–2024)

Relatório analítico com três páginas cobrindo ~6 anos de dados de licitações:

- **Visão Geral** — KPIs, série temporal com previsão por regressão linear, treemap por categoria, comparativo YoY
- **Por Categoria** — Perfis de categoria, análise de dispersão, rankings, distribuição empilhada
- **Por Fornecedor** — Curva de Pareto, concentração de fornecedores (estilo HHI), tabela top-20

Inclui artefatos de análise de séries temporais (ACF/PACF, decomposição STL) gerados com Prophet e incorporados como valores estáticos de previsão em DAX.

---

## Referência de pesquisa PBIR

[pbir_research_and_learnings.md](pbir_research_and_learnings.md) documenta tudo que foi descoberto no processo de engenharia reversa do formato PBIP do Power BI:

- Estrutura de diretórios do PBIP e papel de cada arquivo
- Sintaxe TMDL para tabelas, medidas, relacionamentos e partições
- Schema JSON de relatório 2.7.0 — padrões para mais de 30 tipos de gráfico
- Armadilhas de formato de cor (literais hex precisam de expressões com aspas simples)
- Padrões DAX: inteligência de tempo, rankings, métricas de concentração, janelas móveis
- Configuração de fontes de dados em Power Query / M
- Sistema de temas e integração com tema customizado shadcn

Este arquivo é a fonte da verdade usada pelas ferramentas de geração de código.

---

## Decisões de design

**Uma pergunta por vez** — O agente de requisitos nunca despeja um formulário no usuário. Ele faz uma única pergunta, aguarda a resposta e então avança. Isso replica como um analista sênior entrevista um stakeholder.

**ProjectSpec como fonte da verdade** — Todos os metadados do projeto vivem em um único documento JSON versionado. Alterações iterativas atualizam apenas a seção relevante, evitando reconstruções completas.

**Pesquisa antes da geração** — Cada padrão visual do gerador foi primeiro construído e validado manualmente no Power BI Desktop, depois formalizado em código. Sem adivinhações sobre o schema.

**Saída determinística** — O LLM cuida dos requisitos e decisões; o escritor de arquivos é Python puro, sem chamadas ao LLM. Isso garante saída PBIP sintaticamente válida sempre.

---

## Licença

MIT
