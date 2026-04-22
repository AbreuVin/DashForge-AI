# DashForge AI — Task Checklist

## Fase 0 — Setup
- [ ] Criar repo `dashforge-ai/` com estrutura de pastas
- [ ] `pyproject.toml` + dependências (fastapi, agno, anthropic, pandas, openpyxl, sqlalchemy)
- [ ] `.env.example` com variáveis (ANTHROPIC_API_KEY, DATABASE_URL, etc.)
- [ ] Copiar templates PBIP base (do projeto Databrick Gov / Governança BI)
- [ ] Script de sanidade: lê um visual.json e valida as regras do pbir_research_and_learnings.md

## Fase 1 — Pipeline de Build (núcleo técnico)
- [ ] `src/tools/excel_reader.py` — perfil de dados (colunas, tipos, amostras, relacionamentos)
- [ ] `src/tools/tmdl_writer.py` — gera model.tmdl, tabelas, relacionamentos, medidas DAX
- [ ] `src/tools/pbir_writer.py` — gera visual.json com schema 2.7.0 correto
- [ ] `src/tools/pbir_validator.py` — valida JSON antes de salvar (regras do pbir_research)
- [ ] `src/tools/project_packager.py` — monta estrutura PBIP e gera ZIP
- [ ] **Teste de integração:** ProjectSpec fixo → ZIP → abrir no Power BI Desktop

## Fase 2 — Agente de Requisitos
- [ ] Definir schema do ProjectSpec (Pydantic model)
- [ ] `src/agents/requirements_agent.py` — instrução de analista sênior, uma pergunta por vez
- [ ] Lógica de gap detection (quais campos do spec ainda faltam)
- [ ] Validação de consistência (tipo de visual vs dados disponíveis)
- [ ] Estado de conversa persistido em SQLite (SQLAlchemy)
- [ ] `src/agents/design_agent.py` — decide páginas, layout, visuais
- [ ] `src/agents/build_agent.py` — orquestra os tools de Fase 1
- [ ] `src/agents/review_agent.py` — valida output antes de entregar
- [ ] **Teste CLI:** conversa em terminal → spec → build → ZIP

## Fase 3 — API (FastAPI)
- [ ] Setup FastAPI + estrutura de routers
- [ ] `POST /api/projects` — cria projeto novo
- [ ] `GET /api/projects/{id}` — carrega estado do projeto
- [ ] `POST /api/chat` — mensagem → resposta do agente (SSE streaming)
- [ ] `POST /api/upload` — upload de Excel/CSV
- [ ] `POST /api/build/{id}` — dispara geração do .pbip
- [ ] `GET /api/download/{id}` — retorna ZIP do projeto
- [ ] Teste com curl / Postman

## Fase 4 — Frontend (última prioridade)
- [ ] React + shadcn/ui + Tailwind v4 setup (Vite)
- [ ] Chat conversacional com streaming SSE
- [ ] Upload de arquivo com progresso
- [ ] Preview wireframe do dashboard (React renderiza estrutura do spec)
- [ ] Histórico de projetos
- [ ] Tema dark/light

## Decisões pendentes
- [ ] Avaliar Claude vs OpenAI como LLM principal (custo vs qualidade de requisitos)
- [ ] Definir onde hospedar (Railway / Render / Fly.io)
- [ ] Definir se preview é wireframe React ou screenshot do PBI Desktop
