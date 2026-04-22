# DashForge AI

Generate professional Power BI dashboards from natural language — no Power BI Desktop required.

DashForge AI is an AI-powered backend that converts plain-language requirements into ready-to-open `.pbip` files. It pairs a conversational requirements agent (built on Claude + Agno) with a deterministic PBIR code generation pipeline, ensuring correct output every time.

---

## What this repo contains

| Folder / File | Description |
|---|---|
| `dashforge-ai/` | Python application — FastAPI backend + AI agent + PBIP generator |
| `Databrick Gov/` | Reference dashboard: Brazilian Army procurement analysis (2019–2024) |
| `CONTRATAÇÕES - DGT.pbip` | Reference dashboard: government contracting |
| `Projeto para aprendizado/` | Learning project used as design reference ("Governança BI") |
| `projeto.pbip` | Minimal PBIP template for bootstrapping new projects |
| `pbir_research_and_learnings.md` | 4,000-line technical reference on the PBIR/TMDL file format |
| `docs/` | Architecture decisions, implementation plan, task checklist |

---

## How it works

```
User describes what they need
        ↓
RequirementsAgent (Claude + Agno)
  → asks one clarifying question at a time
  → detects gaps and prevents bad design choices
  → outputs a structured ProjectSpec (JSON)
        ↓
PBIP Generation Pipeline
  → reads Excel / CSV data
  → writes TMDL (semantic model + DAX measures)
  → writes Report JSON (visuals, pages, bindings)
  → validates against PBIR schema 2.7.0
  → packages the .pbip file
        ↓
User opens the file in Power BI Desktop
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Uvicorn (SSE for real-time streaming) |
| AI | Claude API (Anthropic) + Agno agent framework |
| Database | SQLite (dev) → PostgreSQL (prod) via SQLAlchemy + aiosqlite |
| Data | Pandas, OpenPyXL |
| Frontend (planned) | React + shadcn/ui + Tailwind CSS v4 |
| Analytics | Prophet (time-series forecasting), STL decomposition |
| Custom visuals | Deneb / Vega-Lite |
| Testing | pytest, pytest-asyncio, httpx |

---

## Project status

- [x] Phase 0 — Project setup (pyproject.toml, config, folder structure)
- [x] Research — 4,000-line PBIR/TMDL syntax reference validated against real dashboards
- [x] Reference dashboards — Databrick Gov (37 visuals, 38 DAX measures, forecast)
- [ ] Phase 1 — Build pipeline (tool modules: excel reader, TMDL writer, PBIR writer, validator, packager)
- [ ] Phase 2 — Requirements agent (conversational spec gathering)
- [ ] Phase 3 — REST API + SSE streaming
- [ ] Phase 4 — React frontend

---

## Getting started

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
git clone https://github.com/AbreuVin/DashForge-AI
cd dashforge-ai/dashforge-ai
cp .env.example .env          
pip install -e ".[dev]"
```

### Run the API

```bash
uvicorn src.api:app --reload
```

---

## Reference dashboards

### Databrick Gov — Brazilian Army Procurement (2019–2024)

Three-page analytical report covering ~6 years of procurement data:

- **Visão Geral** — KPIs, time series with linear regression forecast, category treemap, YoY comparison
- **Por Categoria** — Category profiles, scatter analysis, rankings, stacked breakdown
- **Por Fornecedor** — Pareto curve, supplier concentration (HHI-style), top-20 table

Includes time-series analysis artifacts (ACF/PACF, STL decomposition) generated with Prophet before being embedded as static forecast values in DAX.

---

## PBIR research reference

[pbir_research_and_learnings.md](pbir_research_and_learnings.md) documents everything discovered while reverse-engineering the Power BI PBIP format:

- PBIP directory layout and file roles
- TMDL syntax for tables, measures, relationships, partitions
- Report JSON schema 2.7.0 — patterns for 30+ chart types
- Color format gotchas (hex literals must use single-quoted expressions)
- DAX patterns: time intelligence, rankings, concentration metrics, rolling windows
- Power Query / M data source configuration
- Theme system and custom shadcn theme integration

This file is the source of truth used by the code generation tools.

---

## Key design decisions

**One question at a time** — The requirements agent never dumps a form on the user. It asks a single question, waits, then proceeds. This mirrors how a senior analyst interviews a stakeholder.

**ProjectSpec as source of truth** — All project metadata lives in a single versioned JSON document. Iterative changes only update the relevant section, avoiding full rebuilds.

**Research before generation** — Every visual pattern in the generator was first manually built and validated in Power BI Desktop, then formalized into code. No guessing at the schema.

**Deterministic output** — The LLM handles requirements and decisions; the file writer is pure Python with no LLM calls. This guarantees syntactically valid PBIP output.

---

## License

MIT
