# Prompt para Claude Code — Construção do Report (PBIR)

Copie tudo entre as linhas `---` abaixo e cole no Claude Code rodando na raiz do projeto (pasta que contém o `.pbip`).

**Antes de rodar:**
1. Feche o Power BI Desktop
2. Habilite o formato PBIR no Power BI Desktop: *Arquivo → Opções → Versão preliminar → Power BI Project (.pbip) — store reports using enhanced metadata format (PBIR)*. Isso precisa estar ligado pra que os arquivos do Report sejam JSON editáveis. Se você nunca salvou o projeto com PBIR ligado, o Claude Code vai precisar criar a estrutura do zero.
3. Coloque o arquivo `shadcn-theme.json` (já gerado) na pasta `Databrick Gov.SemanticModel/` ou na raiz do projeto — o prompt referencia ele.

---

## Contexto

Sou data scientist no TJBA (estágio) e estou montando um dashboard Power BI no formato **PBIP/PBIR** sobre licitações públicas do Exército brasileiro (2019-2024). O semantic model já existe e já tem medidas DAX e tabela Calendário criadas. Preciso que você crie o Report (3 páginas) editando diretamente os arquivos JSON do PBIR.

## Estrutura do projeto

```
Databrick Gov/
├── Databrick Gov.pbip                    # entry point (já existe)
├── Databrick Gov.SemanticModel/          # modelo (já existe, não mexer)
│   └── definition/
│       ├── tables/
│       │   ├── licitacoes.tmdl
│       │   ├── licitacoes_2019_2024.tmdl
│       │   ├── mapa_descricao.tmdl
│       │   ├── Calendario.tmdl           # já criada
│       │   └── _Medidas.tmdl             # já criada, contém todas medidas
│       └── relationships.tmdl
└── Databrick Gov.Report/                 # a criar/completar
    ├── definition.pbir
    ├── StaticResources/                  # onde vai o theme
    └── definition/
        ├── report.json
        ├── pages/
        │   └── pages.json
        │   └── <page-folders>/
        └── ...
```

## Formato PBIR

PBIR é o novo formato JSON dos reports PBIP (ainda em preview Microsoft, mas estável o suficiente pra edição manual). Se tiver dúvida sobre alguma propriedade específica, consulte:

- https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report
- Schema oficial: `https://developer.microsoft.com/json-schemas/fabric/item/report/definition/...` (links em cada arquivo)

Se não existir `Databrick Gov.Report/`, crie do zero seguindo o schema. Se já existir, leia primeiro pra entender a estrutura e incremente.

## Medidas já disponíveis no modelo (use essas, não invente)

Todas estão em `_Medidas`:

**Valores base:** `Valor Total`, `Qtd Itens`, `Qtd Licitacoes`, `Qtd Fornecedores`, `Qtd Categorias`, `Qtd Linhas`

**Médias:** `Ticket Medio Licitacao`, `Valor Medio Item`, `Valor Mediano Item`, `Itens por Licitacao`

**Time intelligence:** `Valor Ano Anterior`, `Valor Delta YoY`, `Valor YoY %`, `Valor Mes Anterior`, `Valor Delta MoM`, `Valor MoM %`, `Valor YTD`, `Valor YTD Ano Anterior`, `Valor 12M Moveis`

**Participação:** `% do Total Geral`, `% da Categoria`, `% do Ano`

**Rankings:** `Rank Categoria`, `Rank Fornecedor`, `Fornecedor #1 Nome`, `Fornecedor #1 Valor`, `Categoria #1 Nome`

**Concentração:** `Valor Top 5 Fornecedores`, `% Concentracao Top 5 Fornecedores`, `Valor Top 10 Fornecedores`, `% Concentracao Top 10 Fornecedores`

**Auxiliares:** `Valor Total Formatado`, `Cor YoY`

## Tabelas/colunas para bindings

- `'licitacoes_2019_2024'[categoria_ia]`, `[nome]`, `[cpfCnpjVencedor]`, `[descricao]`, `[id]`
- `'Calendario'[Date]`, `[Ano]`, `[MesAno]`, `[MesAnoNumero]`, `[Trimestre]`, `[NomeMes]`
- `'mapa_descricao'[categoria_ia]`, `[confianca]`

## Configuração global do Report

- **Dimensões de página:** 1280 × 720 (16:9, tipo `PageViewType: FitToPage`)
- **Background da página:** `#FAFAFA`
- **Tema:** aplicar o `shadcn-theme.json`. Copie o arquivo pra `Databrick Gov.Report/StaticResources/SharedResources/BaseThemes/shadcn-theme.json` e referencie em `report.json` como `customTheme`
- **Fonte padrão:** Segoe UI / Segoe UI Semibold (já está no tema)

## Layout grid (use pra posicionar visuais)

- Margem externa: 24px
- Gutters entre visuais: 16px
- Grid útil: 1232 × 672 (após margens)

---

## Página 1 — "Visão Geral"

**Arquivo:** `definition/pages/00_visao_geral/page.json`
**displayName:** `"Visão Geral"`
**name/id:** `00_visao_geral`
**ordinal:** 0

### Header (y=24, h=56)

1. **Textbox** (x=24, y=24, w=600, h=32)
   - Texto: `Licitações do Exército`
   - Tamanho: 20pt, cor `#09090B`, fonte `Segoe UI Semibold`

2. **Textbox** (x=24, y=56, w=600, h=20)
   - Texto: `2019 – 2024 · Fonte: Portal da Transparência · Órgão 52111`
   - Tamanho: 11pt, cor `#71717A`, fonte `Segoe UI`

3. **Slicer Ano** (x=900, y=32, w=170, h=40)
   - Campo: `Calendario[Ano]`
   - Estilo: Tile/Chip, permite múltipla seleção
   - Orientação: horizontal

4. **Slicer Trimestre** (x=1086, y=32, w=170, h=40)
   - Campo: `Calendario[Trimestre]`
   - Estilo: Tile/Chip, permite múltipla seleção

### KPI Cards (y=96, h=120)

Quatro cards do tipo `card` (ou `cardVisual` — o "New Card" — preferível), 292×120 cada, com gutter 16.

5. **Card 1 — Valor Total** (x=24, y=96, w=292, h=120)
   - Campo principal: `[Valor Total Formatado]`
   - Label: "Valor Total"
   - Abaixo: `[Valor YoY %]` com seta ↑/↓ e cor condicional usando `[Cor YoY]`

6. **Card 2 — Qtd Licitações** (x=332, y=96, w=292, h=120)
   - Campo: `[Qtd Licitacoes]`
   - Label: "Licitações"

7. **Card 3 — Qtd Fornecedores** (x=640, y=96, w=292, h=120)
   - Campo: `[Qtd Fornecedores]`
   - Label: "Fornecedores"

8. **Card 4 — Ticket Médio** (x=948, y=96, w=292, h=120)
   - Campo: `[Ticket Medio Licitacao]`
   - Label: "Ticket Médio"

### Main chart (y=232, h=280)

9. **Line chart — Evolução mensal** (x=24, y=232, w=856, h=280)
   - Eixo X: `Calendario[MesAno]` (ordenado por `MesAnoNumero`)
   - Linhas: `[Valor Total]` (cor `#2563EB`), `[Valor Ano Anterior]` (cor `#A1A1AA`, tracejada)
   - Title: "Evolução mensal do valor licitado"
   - Legend: top, fonte 10pt
   - Markers: off
   - Stroke width: 2

### Right column (y=232, h=280)

10. **Clustered bar chart — Top 5 Categorias** (x=896, y=232, w=360, h=280)
    - Eixo Y: `licitacoes_2019_2024[categoria_ia]`
    - Valor: `[Valor Total]`
    - Filtro de visual: Top N por `[Valor Total]`, N=5, DESC
    - Title: "Top 5 categorias"
    - Cor: `#18181B`

### Bottom row (y=528, h=168)

11. **Table — Top 10 Fornecedores** (x=24, y=528, w=856, h=168)
    - Colunas: `licitacoes_2019_2024[nome]` (rebatizada "Fornecedor"), `[Qtd Licitacoes]`, `[Valor Total]`, `[% do Total Geral]`
    - Filtro: Top 10 por `[Valor Total]`
    - Ordenação: `[Valor Total]` DESC
    - Title: "Top 10 fornecedores"

12. **Card — Valor YTD** (x=896, y=528, w=170, h=80)
    - Campo: `[Valor YTD]` (formato compacto tipo R$ bi/mi)

13. **Card — Valor 12M Móveis** (x=1086, y=528, w=170, h=80)
    - Campo: `[Valor 12M Moveis]`

14. **Card — % YoY** (x=896, y=616, w=340, h=80)
    - Campo: `[Valor YoY %]` grande, cor `[Cor YoY]`
    - Abaixo, label "vs ano anterior"

---

## Página 2 — "Por Categoria"

**Arquivo:** `definition/pages/01_por_categoria/page.json`
**displayName:** `"Por Categoria"`
**ordinal:** 1

### Header

Mesmo header da página 1 (Título: "Análise por Categoria", subtítulo igual, slicers de Ano e Trimestre).

### KPI Cards (y=96, h=100)

1. **Card — Categoria líder** (x=24, y=96, w=292, h=100)
   - Campo: `[Categoria #1 Nome]`
   - Label: "Categoria com maior valor"

2. **Card — Qtd Categorias** (x=332, y=96, w=292, h=100)
   - Campo: `[Qtd Categorias]`
   - Label: "Categorias distintas"

3. **Card — % Bem Categorizados** (x=640, y=96, w=292, h=100)
   - Campo: `[% Itens Bem Categorizados]`
   - Label: "Cobertura da IA"

4. **Card — Confiança Média** (x=948, y=96, w=292, h=100)
   - Campo: `[Confianca Media]`
   - Label: "Confiança média"

### Main visuals (y=212, h=340)

5. **Treemap — Valor por Categoria** (x=24, y=212, w=620, h=340)
   - Agrupador: `licitacoes_2019_2024[categoria_ia]`
   - Valor: `[Valor Total]`
   - Data labels: nome + `[% do Total Geral]`
   - Title: "Distribuição de valor por categoria"

6. **100% stacked column chart — Mix por Ano** (x=664, y=212, w=592, h=340)
   - Eixo X: `Calendario[Ano]`
   - Legenda/serie: `licitacoes_2019_2024[categoria_ia]`
   - Valor: `[Valor Total]` (normalizado 100%)
   - Filtro de visual: apenas top 8 categorias por `[Valor Total]` + "Outros" (se possível; senão só top 8)
   - Title: "Mix de categorias ao longo dos anos"

### Detail table (y=568, h=128)

7. **Table — Detalhe por categoria** (x=24, y=568, w=1232, h=128)
   - Colunas: `categoria_ia`, `[Qtd Licitacoes]`, `[Qtd Itens]`, `[Valor Total]`, `[Ticket Medio Licitacao]`, `[% do Total Geral]`
   - Ordenação: `[Valor Total]` DESC

---

## Página 3 — "Por Fornecedor"

**Arquivo:** `definition/pages/02_por_fornecedor/page.json`
**displayName:** `"Por Fornecedor"`
**ordinal:** 2

### Header

Mesmo header (Título: "Análise por Fornecedor", slicers).

Adicionar um slicer extra de Categoria:

1. **Slicer Categoria** (x=704, y=32, w=180, h=40)
   - Campo: `licitacoes_2019_2024[categoria_ia]`
   - Estilo: Dropdown
   - Permite filtrar os visuais da página por categoria

### KPI Cards (y=96, h=100)

2. **Card — Qtd Fornecedores** (x=24, y=96, w=292, h=100)
   - `[Qtd Fornecedores]`

3. **Card — Fornecedor líder** (x=332, y=96, w=292, h=100)
   - `[Fornecedor #1 Nome]`
   - Label pequeno abaixo: `[Fornecedor #1 Valor]` (formatado compacto)

4. **Card — % Top 5** (x=640, y=96, w=292, h=100)
   - `[% Concentracao Top 5 Fornecedores]`
   - Label: "Concentração Top 5"

5. **Card — % Top 10** (x=948, y=96, w=292, h=100)
   - `[% Concentracao Top 10 Fornecedores]`
   - Label: "Concentração Top 10"

### Pareto (y=212, h=340)

6. **Line and clustered column chart — Pareto** (x=24, y=212, w=860, h=340)
   - Eixo X: `licitacoes_2019_2024[nome]`
   - Colunas: `[Valor Total]` (cor `#2563EB`)
   - Linha: `[% Concentracao Top 10 Fornecedores]` cumulativo (cor `#DC2626`)
   - Filtro visual: Top 15 por `[Valor Total]`
   - Title: "Pareto de fornecedores — Top 15"
   - Sort: `[Valor Total]` DESC

### Scatter (y=212, h=340)

7. **Scatter chart** (x=900, y=212, w=356, h=340)
   - Detalhe (ponto): `licitacoes_2019_2024[nome]`
   - Eixo X: `[Qtd Licitacoes]`
   - Eixo Y: `[Ticket Medio Licitacao]`
   - Tamanho: `[Valor Total]`
   - Title: "Perfil dos fornecedores"
   - Axis labels: "Nº Licitações" / "Ticket Médio"

### Top 20 table (y=568, h=128)

8. **Table — Top 20 Fornecedores** (x=24, y=568, w=1232, h=128)
   - Colunas: `[Rank Fornecedor]`, `nome`, `cpfCnpjVencedor`, `[Qtd Licitacoes]`, `[Valor Total]`, `[% do Total Geral]`, `[Ticket Medio Licitacao]`
   - Filtro visual: Top 20 por `[Valor Total]`
   - Sort: `[Valor Total]` DESC

---

## Interações entre visuais (todas as páginas)

Deixar default "highlight" (não "filter") nos gráficos → KPIs. Isso é o padrão do Power BI, não precisa mexer salvo exceção.

## Bookmarks

Não precisa criar bookmarks nessa versão inicial.

## Checklist pra você (Claude Code)

1. Criar scaffolding do Report se não existir
2. Copiar o `shadcn-theme.json` pra pasta de temas do Report
3. Aplicar o tema no `report.json`
4. Criar as 3 páginas com as dimensões e background corretos
5. Criar cada visual nas posições especificadas, com os bindings corretos
6. Validar que:
   - Todos os nomes de medidas existem (conferir no TMDL)
   - Todos os nomes de colunas existem
   - Arquivos JSON são válidos (parse OK)
   - Nenhum caractere especial quebrou os nomes de pasta (sem acentos em nomes de arquivo)
7. Ao terminar, gerar um `REPORT_README.md` listando:
   - Arquivos criados
   - Visuais com alguma limitação ou que recomendo finalizar no Desktop
   - Próximos passos manuais (ex: ajustar sort, formatar data label, adicionar drill-through se quiser)

## O que NÃO fazer

- Não alterar nada em `Databrick Gov.SemanticModel/`
- Não criar medidas novas (usar só as listadas)
- Não inventar colunas que não estão listadas na seção "Tabelas/colunas para bindings"
- Não publicar no Service, só deixar pronto localmente
- Não tentar criar visuais customizados (Deneb, etc) — só nativos Power BI
- Não usar acentos em nomes de arquivos ou pastas do Report (use `02_por_fornecedor`, não `02_por_fornecedor_análise`)

## Se travar

Se alguma propriedade do PBIR estiver obscura, ou se o formato mudou, me avise e deixe o visual como "TODO manual" no `REPORT_README.md` com as instruções pra eu fazer no Power BI Desktop. É melhor entregar 80% funcionando + lista clara do resto do que entregar JSON quebrado.

---

## Notas extras (não copiar no prompt, são pra você, Vinícius)

1. **PBIR ainda é preview** — mesmo com o Claude Code fazendo bem, é comum o Power BI Desktop abrir o projeto e "reorganizar" alguns arquivos na primeira vez que você salva. Isso é normal.

2. **Depois que o Claude Code terminar:**
   - Abra o `.pbip` no Power BI Desktop
   - Confira se as 3 páginas aparecem com o layout certo
   - Se algum visual estiver vazio ou errado, clique nele e rebind os campos manualmente (leva 30s cada)
   - Salve. O Power BI vai normalizar os arquivos PBIR

3. **Se o Claude Code falhar na criação dos visuais JSON** (é possível, o formato é complexo), peça pra ele só:
   - Criar as 3 páginas em branco com os títulos certos
   - Aplicar o tema
   - Gerar um TODO com os visuais a montar
   
   Aí você monta no Desktop seguindo a spec. Ainda economiza tempo.

4. **Próximo passo depois disso:** validar números (SUM(valor) no Databricks = Valor Total no BI), polir o visual, adicionar drill-through entre páginas.
