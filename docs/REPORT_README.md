# Databrick Gov — PBIP Project README

Dashboard de análise de licitações do Exército Brasileiro (2019–2024).

---

## Arquivos criados

### Semantic Model (`Databrick Gov.SemanticModel/definition/`)

| Arquivo | Descrição |
|---|---|
| `tables/Calendario.tmdl` | Tabela de datas calculada via ADDCOLUMNS + CALENDAR, 12 colunas |
| `tables/_Medidas.tmdl` | 38 medidas DAX em 8 display folders |
| `relationships.tmdl` | 2 relacionamentos: licitacoes→mapa_descricao e licitacoes→Calendario |
| `model.tmdl` | Atualizado com refs para Calendario e _Medidas |
| `tables/licitacoes_2019_2024.tmdl` | Removido bloco `variation` que referenciava LocalDateTable deletada |

### Report (`Databrick Gov.Report/definition/`)

| Arquivo | Descrição |
|---|---|
| `report.json` | Tema shadcn-like aplicado |
| `pages/pages.json` | Ordem das 3 páginas |
| `StaticResources/SharedResources/BaseThemes/shadcn-theme.json` | Tema customizado |

#### Página 00 — Visão Geral (11 visuais)

| Visual ID | Tipo | Conteúdo |
|---|---|---|
| `txt_titulo` | textbox | Título da página |
| `slicer_ano` | slicer | Filtro por Ano (syncGroup: slicerAno) |
| `slicer_trimestre` | slicer | Filtro por Trimestre (syncGroup: slicerTrimestre) |
| `kpi_total` | card | Valor Total |
| `kpi_qtd` | card | Qtd Licitacoes |
| `kpi_ticket` | card | Ticket Medio Licitacao |
| `kpi_yoy` | card | Valor YoY % |
| `line_evolucao` | lineChart | Valor Total por MesAno |
| `bar_top5_cat` | clusteredBarChart | Top categorias por Valor Total |
| `treemap_cat` | treemap | Valor Total por descricao_original |
| `stacked_trim` | hundredPercentStackedColumnChart | Valor Total por Trimestre e Ano |

#### Página 01 — Por Categoria (13 visuais)

| Visual ID | Tipo | Conteúdo |
|---|---|---|
| `txt_titulo` | textbox | Título da página |
| `slicer_ano` | slicer | Filtro por Ano (syncGroup: slicerAno) |
| `slicer_trimestre` | slicer | Filtro por Trimestre (syncGroup: slicerTrimestre) |
| `kpi_total_cat` | card | Valor Total |
| `kpi_qtd_cat` | card | Qtd Licitacoes |
| `kpi_ticket_cat` | card | Ticket Medio Licitacao |
| `kpi_conc_cat` | card | % Concentracao Top 5 Categorias |
| `bar_cat_valor` | clusteredBarChart | Valor Total por categoria |
| `line_cat_tempo` | lineChart | Valor Total por MesAno e categoria |
| `scatter_cat` | scatterChart | Perfil categoria: Qtd vs Ticket Médio (tamanho = Valor Total) |
| `tbl_top10_cat` | tableEx | Top categorias: Rank, nome, Qtd, Valor Total, %, Ticket Médio |
| `treemap_sub` | treemap | Valor Total por subcategoria |
| `stacked_cat_ano` | hundredPercentStackedColumnChart | Mix de categorias por Ano |

#### Página 02 — Por Fornecedor (13 visuais)

| Visual ID | Tipo | Conteúdo |
|---|---|---|
| `txt_titulo` | textbox | Título da página |
| `slicer_ano` | slicer | Filtro por Ano (syncGroup: slicerAno) |
| `slicer_trimestre` | slicer | Filtro por Trimestre (syncGroup: slicerTrimestre) |
| `kpi_total_forn` | card | Valor Total |
| `kpi_qtd_forn` | card | Qtd Licitacoes |
| `kpi_ticket_forn` | card | Ticket Medio Licitacao |
| `kpi_conc_top5` | card | % Concentracao Top 5 Fornecedores |
| `kpi_conc_top10` | card | % Concentracao Top 10 Fornecedores |
| `combo_pareto` | lineClusteredColumnComboChart | Pareto de fornecedores (Valor Total + % concentração acumulada) |
| `scatter_perfil` | scatterChart | Perfil fornecedor: Qtd vs Ticket Médio (tamanho = Valor Total) |
| `tbl_top20_forn` | tableEx | Top 20: Rank, nome, CNPJ, Qtd, Valor Total, %, Ticket Médio |

---

## Visuais que recomendo finalizar no Desktop

### Filtros Top N (obrigatório para o visual fazer sentido)

| Visual | Filtro necessário |
|---|---|
| `bar_top5_cat` (Visão Geral) | Top N = 5 por Valor Total na barra |
| `tbl_top10_cat` (Por Categoria) | Top N = 10 por Valor Total na tabela |
| `combo_pareto` (Por Fornecedor) | Top N = 15 por Valor Total (eixo categoria = nome) |
| `tbl_top20_forn` (Por Fornecedor) | Top N = 20 por Valor Total na tabela |

> No Power BI Desktop: selecione o visual → Filtros → arraste o campo de valor → escolha "Top N".

### Estilo dos slicers

Todos os 6 slicers (Ano e Trimestre nas 3 páginas) foram criados como slicer padrão. Para o layout visual do mockup, aplicar:

- **Formato → Configurações de slicer → Estilo → Tile**

### Ordenação de eixos

| Visual | Ordenação recomendada |
|---|---|
| `line_evolucao` | Eixo X: MesAno ordenado por MesAnoNumero (crescente) |
| `line_cat_tempo` | Eixo X: MesAno ordenado por MesAnoNumero (crescente) |
| `stacked_trim` | Eixo X: Trimestre ordenado por valor numérico |
| `stacked_cat_ano` | Eixo X: Ano (crescente) |
| `combo_pareto` | Eixo X: nome ordenado por Valor Total (decrescente) |
| `bar_top5_cat` | Barras ordenadas por Valor Total (decrescente) |
| `bar_cat_valor` | Barras ordenadas por Valor Total (decrescente) |

### Formatação de KPI

- `kpi_yoy` (Valor YoY %): Aplicar formatação condicional de cor — verde quando positivo, vermelho quando negativo.
  - Formato → Cor do valor → Formatação condicional → Regras baseadas no campo.

### Scatter charts

Os scatter charts (`scatter_cat`, `scatter_perfil`) precisam de rótulos de dados configurados manualmente para exibir o nome dos pontos:
- Formato → Marcadores de dados → ativar e definir qual campo exibe o rótulo.

---

## Próximos passos manuais

1. **Marcar Calendario como tabela de datas**
   - Power BI Desktop → aba Modelagem → selecionar tabela Calendario → "Marcar como tabela de datas" → campo Date

2. **Aplicar estilo Tile nos slicers** (veja seção acima)

3. **Adicionar filtros Top N** nos 4 visuais listados acima

4. **Corrigir ordenação** dos eixos temporais (MesAno deve ordenar por MesAnoNumero)

5. **Formatar KPI YoY** com cor condicional

6. **Drill-through (opcional)**: Se quiser, criar uma página de detalhe de fornecedor com drill-through a partir do `tbl_top20_forn` — campo `nome` como campo de drill.

7. **Tooltip pages (opcional)**: Criar páginas de tooltip personalizadas para os scatter charts mostrando mais detalhes do ponto hovado.

8. **Publicar no Fabric**: Após validar, publicar o workspace e configurar as credenciais do dataset (se usar Databricks como fonte live).

---

## Notas técnicas

- Slicers `slicer_ano` e `slicer_trimestre` usam `syncGroup` para sincronizar entre as 3 páginas automaticamente.
- A tabela `_Medidas` não tem colunas — é usada apenas como container de medidas (sem relacionamento necessário).
- O tema shadcn foi copiado de `Shadcntheme·json` na raiz do projeto para `StaticResources/SharedResources/BaseThemes/shadcn-theme.json`.
- Todas as medidas DAX usam `USERELATIONSHIP` implicitamente pela relação `licitacoes_2019_2024[mes/ano] → Calendario[Date]`.
