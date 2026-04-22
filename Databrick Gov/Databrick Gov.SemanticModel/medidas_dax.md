# Pacote de Medidas DAX — Databrick Gov

Modelo validado contra o seu semantic model. Todas as medidas referenciam as colunas **exatamente** como estão hoje, então é só copiar e colar.

> **Tabela fato:** `licitacoes_2019_2024` (grão de item, já enriquecida com categoria_ia)
> **Tabela dim:** `mapa_descricao`
> **Tabela cabeçalho:** `licitacoes` (ainda sem relacionamento — opcional)

---

## 1. Pré-requisitos

### 1.1. Criar a tabela Calendário

No Power BI Desktop: *Modelagem → Nova tabela* e cola:

```dax
Calendario =
VAR MinDate = MIN ( 'licitacoes_2019_2024'[mes/ano] )
VAR MaxDate = MAX ( 'licitacoes_2019_2024'[mes/ano] )
RETURN
ADDCOLUMNS (
    CALENDAR ( DATE ( YEAR ( MinDate ), 1, 1 ), DATE ( YEAR ( MaxDate ), 12, 31 ) ),
    "Ano",           YEAR ( [Date] ),
    "Mes",           MONTH ( [Date] ),
    "NomeMes",       FORMAT ( [Date], "MMMM", "pt-BR" ),
    "NomeMesAbrev",  FORMAT ( [Date], "MMM",   "pt-BR" ),
    "MesAno",        FORMAT ( [Date], "MMM/yyyy", "pt-BR" ),
    "MesAnoNumero",  YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Trimestre",     "T" & FORMAT ( [Date], "Q" ),
    "AnoTrimestre",  YEAR ( [Date] ) & " T" & FORMAT ( [Date], "Q" ),
    "InicioMes",     DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ),
    "FimMes",        EOMONTH ( [Date], 0 ),
    "DiaSemana",     FORMAT ( [Date], "dddd", "pt-BR" )
)
```

### 1.2. Marcar como tabela de datas

Clica na tabela `Calendario` → *Ferramentas de Tabela → Marcar como tabela de datas → Date*.

### 1.3. Criar os relacionamentos

- `Calendario[Date]` → `licitacoes_2019_2024[mes/ano]` (1:N, filtro unidirecional, **ativo**)
- O relacionamento auto-gerado com `LocalDateTable_...` pode ser removido depois — não precisa mais.

### 1.4. Ordenar colunas de mês corretamente

Seleciona a coluna `NomeMes` → *Ferramentas de Coluna → Classificar por coluna → Mes*.
Faz o mesmo com `MesAno` → classificar por `MesAnoNumero`.

### 1.5. Criar a tabela de medidas (opcional mas recomendado)

*Inserir → Inserir Dados → Nome: "_Medidas"* → tabela vazia. Move todas as medidas pra ela depois. Só organizacional.

---

## 2. Medidas — Valores Base

```dax
Valor Total =
SUM ( 'licitacoes_2019_2024'[valor] )
```

```dax
Qtd Itens =
SUM ( 'licitacoes_2019_2024'[quantidade] )
```

```dax
Qtd Licitacoes =
DISTINCTCOUNT ( 'licitacoes_2019_2024'[id] )
```

```dax
Qtd Fornecedores =
DISTINCTCOUNT ( 'licitacoes_2019_2024'[cpfCnpjVencedor] )
```

```dax
Qtd Categorias =
DISTINCTCOUNT ( 'licitacoes_2019_2024'[categoria_ia] )
```

```dax
Qtd Linhas =
COUNTROWS ( 'licitacoes_2019_2024' )
```

---

## 3. Medidas — Médias e Ticket

```dax
Ticket Medio Licitacao =
DIVIDE ( [Valor Total], [Qtd Licitacoes] )
```

```dax
Valor Medio Item =
DIVIDE ( [Valor Total], [Qtd Itens] )
```

```dax
Valor Mediano Item =
MEDIAN ( 'licitacoes_2019_2024'[valor] )
```

```dax
Itens por Licitacao =
DIVIDE ( [Qtd Itens], [Qtd Licitacoes] )
```

---

## 4. Medidas — Time Intelligence

### Ano a Ano (YoY)

```dax
Valor Ano Anterior =
CALCULATE (
    [Valor Total],
    SAMEPERIODLASTYEAR ( Calendario[Date] )
)
```

```dax
Valor Delta YoY =
[Valor Total] - [Valor Ano Anterior]
```

```dax
Valor YoY % =
DIVIDE ( [Valor Delta YoY], [Valor Ano Anterior] )
```

### Mês a Mês (MoM)

```dax
Valor Mes Anterior =
CALCULATE (
    [Valor Total],
    DATEADD ( Calendario[Date], -1, MONTH )
)
```

```dax
Valor Delta MoM =
[Valor Total] - [Valor Mes Anterior]
```

```dax
Valor MoM % =
DIVIDE ( [Valor Delta MoM], [Valor Mes Anterior] )
```

### Acumulados

```dax
Valor YTD =
TOTALYTD ( [Valor Total], Calendario[Date] )
```

```dax
Valor YTD Ano Anterior =
CALCULATE (
    [Valor YTD],
    SAMEPERIODLASTYEAR ( Calendario[Date] )
)
```

```dax
Valor 12M Moveis =
CALCULATE (
    [Valor Total],
    DATESINPERIOD (
        Calendario[Date],
        LASTDATE ( Calendario[Date] ),
        -12,
        MONTH
    )
)
```

---

## 5. Medidas — Participação (%)

```dax
% do Total Geral =
DIVIDE (
    [Valor Total],
    CALCULATE ( [Valor Total], ALL ( 'licitacoes_2019_2024' ) )
)
```

```dax
% da Categoria Selecionada =
DIVIDE (
    [Valor Total],
    CALCULATE ( [Valor Total], ALLEXCEPT ( 'licitacoes_2019_2024', 'licitacoes_2019_2024'[categoria_ia] ) )
)
```

```dax
% do Ano =
DIVIDE (
    [Valor Total],
    CALCULATE ( [Valor Total], ALLEXCEPT ( Calendario, Calendario[Ano] ) )
)
```

---

## 6. Medidas — Rankings

```dax
Rank Categoria =
IF (
    HASONEVALUE ( 'licitacoes_2019_2024'[categoria_ia] ),
    RANKX (
        ALL ( 'licitacoes_2019_2024'[categoria_ia] ),
        [Valor Total],
        ,
        DESC,
        DENSE
    )
)
```

```dax
Rank Fornecedor =
IF (
    HASONEVALUE ( 'licitacoes_2019_2024'[nome] ),
    RANKX (
        ALL ( 'licitacoes_2019_2024'[nome] ),
        [Valor Total],
        ,
        DESC,
        DENSE
    )
)
```

```dax
Fornecedor #1 Nome =
CALCULATE (
    SELECTEDVALUE ( 'licitacoes_2019_2024'[nome] ),
    TOPN ( 1, VALUES ( 'licitacoes_2019_2024'[nome] ), [Valor Total], DESC )
)
```

```dax
Fornecedor #1 Valor =
MAXX (
    TOPN ( 1, VALUES ( 'licitacoes_2019_2024'[nome] ), [Valor Total], DESC ),
    [Valor Total]
)
```

```dax
Categoria #1 Nome =
CALCULATE (
    SELECTEDVALUE ( 'licitacoes_2019_2024'[categoria_ia] ),
    TOPN ( 1, VALUES ( 'licitacoes_2019_2024'[categoria_ia] ), [Valor Total], DESC )
)
```

---

## 7. Medidas — Concentração (Pareto)

```dax
Valor Top 5 Fornecedores =
VAR Top5 =
    TOPN ( 5, VALUES ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ), [Valor Total], DESC )
RETURN
    CALCULATE ( [Valor Total], Top5 )
```

```dax
% Concentracao Top 5 Fornecedores =
DIVIDE (
    [Valor Top 5 Fornecedores],
    CALCULATE ( [Valor Total], ALL ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ) )
)
```

```dax
Valor Top 10 Fornecedores =
VAR Top10 =
    TOPN ( 10, VALUES ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ), [Valor Total], DESC )
RETURN
    CALCULATE ( [Valor Total], Top10 )
```

```dax
% Concentracao Top 10 Fornecedores =
DIVIDE (
    [Valor Top 10 Fornecedores],
    CALCULATE ( [Valor Total], ALL ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ) )
)
```

---

## 8. Medidas — Qualidade de Dados

```dax
Qtd Itens Sem Categoria =
CALCULATE (
    [Qtd Linhas],
    'licitacoes_2019_2024'[categoria_ia]
        IN { "Sem Descrição", "Outros / Necessita Revisão", BLANK() }
)
```

```dax
% Itens Bem Categorizados =
1 - DIVIDE ( [Qtd Itens Sem Categoria], [Qtd Linhas] )
```

```dax
Confianca Media =
AVERAGE ( 'mapa_descricao'[confianca] )
```

```dax
Qtd Itens Baixa Confianca =
CALCULATE (
    [Qtd Linhas],
    FILTER (
        'mapa_descricao',
        'mapa_descricao'[confianca] < 0.5 && 'mapa_descricao'[confianca] > 0
    )
)
```

```dax
% Itens Baixa Confianca =
DIVIDE ( [Qtd Itens Baixa Confianca], [Qtd Linhas] )
```

---

## 9. Medidas — Formatação Dinâmica (opcional, fica bonito)

```dax
Valor Total Formatado =
VAR Valor = [Valor Total]
RETURN
    SWITCH (
        TRUE (),
        Valor >= 1e9, FORMAT ( Valor / 1e9, "R$ #,##0.00" ) & " bi",
        Valor >= 1e6, FORMAT ( Valor / 1e6, "R$ #,##0.00" ) & " mi",
        Valor >= 1e3, FORMAT ( Valor / 1e3, "R$ #,##0.00" ) & " mil",
        FORMAT ( Valor, "R$ #,##0.00" )
    )
```

```dax
Cor YoY =
SWITCH (
    TRUE (),
    [Valor YoY %] > 0, "#16A34A",
    [Valor YoY %] < 0, "#DC2626",
    "#71717A"
)
```

Use em *Formato → Título → Cor → Formatação condicional → Valor do campo* apontando pra `[Cor YoY]`.

---

## 10. Formatação padrão das medidas

No painel de propriedades de cada medida:

| Medida | Formato | Casas |
|---|---|---|
| `Valor Total`, `Valor Médio`, `Valor Mediano`, `Ticket Médio` | Moeda R$ | 2 |
| `Qtd *` | Número inteiro com separador | 0 |
| `% *`, `YoY %`, `MoM %` | Porcentagem | 1 |
| `Valor YoY %`, `Valor MoM %`, `% Concentracao *` | Porcentagem | 1 |
| `Rank *` | Número inteiro | 0 |
| `Confianca Media` | Decimal | 3 |

---

## 11. Dicas de uso

**KPI cards principais** (página Visão Geral):
- `Valor Total` + `Valor YoY %` (como crescimento)
- `Qtd Licitacoes` + comparativo ano anterior
- `Qtd Fornecedores`
- `Ticket Medio Licitacao`

**Gráfico de linha temporal:** `Valor Total` por `Calendario[MesAno]` — aplica o tema, fica como a linha do shadcn.

**Barras horizontais Top 10 Fornecedores:** `Valor Total` por `nome`, filtrado por `Rank Fornecedor <= 10`.

**Treemap categorias:** `Valor Total` por `categoria_ia` com rótulo mostrando `% do Total Geral`.

**Painel de qualidade:** `% Itens Bem Categorizados` e `Confianca Media` como cards, + tabela com `categoria_ia` + `Qtd Linhas` + `Confianca Media` ordenada por confiança asc (pra ver o que precisa revisar).

---

## 12. Próximos passos sugeridos

1. Testar as medidas base (`Valor Total`, `Qtd Licitacoes`) e confirmar que o total bate com o Databricks (`SELECT SUM(valor), COUNT(DISTINCT id) FROM workspace.default.licitacoes_2019_2024`)
2. Se os números não baterem, é sinal de que o `INNER JOIN` tá comendo linhas — voltar pra correção do SQL
3. Construir a página *Visão Geral* com os KPIs e o gráfico temporal
4. Iterar com as outras páginas (Categoria, Fornecedor, Qualidade)

Se precisar de medida específica que não tá aqui (ex: análise de sazonalidade, market share por categoria num ano específico, cohort de fornecedores), me avisa.
