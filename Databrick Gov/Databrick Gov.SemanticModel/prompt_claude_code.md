# Prompt para Claude Code

Copie tudo que está entre as linhas `---` abaixo e cole no Claude Code rodando na raiz do projeto `Databrick Gov` (a pasta que contém o `.pbip` e as subpastas `.SemanticModel` / `.Report`).

**Antes de rodar:** feche o Power BI Desktop. O PBIP usa arquivos TMDL em texto e, se estiver aberto, o Power BI pode sobrescrever suas alterações quando fechar.

---

## Contexto

Estou trabalhando num projeto Power BI no formato **PBIP** (pasta `Databrick Gov.SemanticModel` com arquivos TMDL). Preciso que você adicione uma tabela Calendário, um conjunto de medidas DAX e o relacionamento necessário, editando diretamente os arquivos TMDL do semantic model.

## Estrutura do projeto

- `Databrick Gov.pbip` — entry point
- `Databrick Gov.SemanticModel/definition/` — onde vivem os TMDL
  - `model.tmdl`, `database.tmdl`, `expressions.tmdl`, `relationships.tmdl`
  - `tables/licitacoes.tmdl`
  - `tables/licitacoes_2019_2024.tmdl`
  - `tables/mapa_descricao.tmdl`
  - `cultures/pt-BR.tmdl`

## Tabelas existentes e colunas (não alterar)

**licitacoes_2019_2024** (fato, grão item): `codigoItemCompra`, `descricao`, `quantidade` (int64), `valor` (decimal), `cpfCnpjVencedor`, `tipoPessoa`, `idVencedor`, `nome`, `descComplementarItemCompra`, `descUnidadeFornecimento`, `id`, `mes/ano` (dateTime), `descricao_original`, `categoria_ia`

**mapa_descricao**: `descricao_original`, `categoria_ia`, `confianca` (double)

**licitacoes** (cabeçalho, sem relacionamento ativo): `mes/ano` (string), `id` (int64), `licitacao` (string), `dataAbertura`, `dataResultadoCompra`, `dataPublicacao`, `dataReferencia`, `situacaoCompra`, `modalidadeLicitacao`, `instrumentoLegal`, `valor` (double), `municipio`, `unidadeGestora`

**Relacionamento existente (manter):** `licitacoes_2019_2024[descricao_original]` → `mapa_descricao[descricao_original]`.

## Tarefas

### 1. Criar tabela calculada `Calendario`

Crie o arquivo `Databrick Gov.SemanticModel/definition/tables/Calendario.tmdl` com uma tabela calculada em DAX que cubra o período dos dados de `licitacoes_2019_2024[mes/ano]`, marcada como **tabela de data** (`dataCategory: Time` na coluna Date + `isDataTable: true` na tabela).

Expressão DAX da tabela:

```dax
VAR MinDate = MIN ( 'licitacoes_2019_2024'[mes/ano] )
VAR MaxDate = MAX ( 'licitacoes_2019_2024'[mes/ano] )
RETURN
ADDCOLUMNS (
    CALENDAR ( DATE ( YEAR ( MinDate ), 1, 1 ), DATE ( YEAR ( MaxDate ), 12, 31 ) ),
    "Ano",          YEAR ( [Date] ),
    "Mes",          MONTH ( [Date] ),
    "NomeMes",      FORMAT ( [Date], "MMMM", "pt-BR" ),
    "NomeMesAbrev", FORMAT ( [Date], "MMM", "pt-BR" ),
    "MesAno",       FORMAT ( [Date], "MMM/yyyy", "pt-BR" ),
    "MesAnoNumero", YEAR ( [Date] ) * 100 + MONTH ( [Date] ),
    "Trimestre",    "T" & FORMAT ( [Date], "Q" ),
    "AnoTrimestre", YEAR ( [Date] ) & " T" & FORMAT ( [Date], "Q" ),
    "InicioMes",    DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ),
    "FimMes",       EOMONTH ( [Date], 0 ),
    "DiaSemana",    FORMAT ( [Date], "dddd", "pt-BR" )
)
```

Colunas `NomeMes` e `NomeMesAbrev` devem ter `sortByColumn: Mes`. Coluna `MesAno` deve ter `sortByColumn: MesAnoNumero`. Defina `isHidden: true` nas colunas `Mes` e `MesAnoNumero` (só servem pra ordenação).

### 2. Criar tabela vazia `_Medidas` para organizar as medidas

Crie `Databrick Gov.SemanticModel/definition/tables/_Medidas.tmdl` como tabela calculada com expressão `{BLANK()}`. Oculte a única coluna gerada (`Value`). Essa tabela vai hospedar todas as medidas listadas abaixo — cada uma com `displayFolder` conforme a seção.

### 3. Adicionar medidas

Todas as medidas devem ir na tabela `_Medidas`. Use formato TMDL correto (`measure 'Nome da Medida' = ...`). Organize por `displayFolder` conforme abaixo.

**displayFolder: "01 Valores Base"**

```dax
Valor Total = SUM ( 'licitacoes_2019_2024'[valor] )
```
*format: "R$ #,##0.00"*

```dax
Qtd Itens = SUM ( 'licitacoes_2019_2024'[quantidade] )
```
*format: "#,##0"*

```dax
Qtd Licitacoes = DISTINCTCOUNT ( 'licitacoes_2019_2024'[id] )
```
*format: "#,##0"*

```dax
Qtd Fornecedores = DISTINCTCOUNT ( 'licitacoes_2019_2024'[cpfCnpjVencedor] )
```
*format: "#,##0"*

```dax
Qtd Categorias = DISTINCTCOUNT ( 'licitacoes_2019_2024'[categoria_ia] )
```
*format: "#,##0"*

```dax
Qtd Linhas = COUNTROWS ( 'licitacoes_2019_2024' )
```
*format: "#,##0"*

**displayFolder: "02 Medias e Ticket"**

```dax
Ticket Medio Licitacao = DIVIDE ( [Valor Total], [Qtd Licitacoes] )
```
*format: "R$ #,##0.00"*

```dax
Valor Medio Item = DIVIDE ( [Valor Total], [Qtd Itens] )
```
*format: "R$ #,##0.00"*

```dax
Valor Mediano Item = MEDIAN ( 'licitacoes_2019_2024'[valor] )
```
*format: "R$ #,##0.00"*

```dax
Itens por Licitacao = DIVIDE ( [Qtd Itens], [Qtd Licitacoes] )
```
*format: "#,##0.0"*

**displayFolder: "03 Time Intelligence"**

```dax
Valor Ano Anterior = CALCULATE ( [Valor Total], SAMEPERIODLASTYEAR ( Calendario[Date] ) )
```
*format: "R$ #,##0.00"*

```dax
Valor Delta YoY = [Valor Total] - [Valor Ano Anterior]
```
*format: "R$ #,##0.00"*

```dax
Valor YoY % = DIVIDE ( [Valor Delta YoY], [Valor Ano Anterior] )
```
*format: "0.0%"*

```dax
Valor Mes Anterior = CALCULATE ( [Valor Total], DATEADD ( Calendario[Date], -1, MONTH ) )
```
*format: "R$ #,##0.00"*

```dax
Valor Delta MoM = [Valor Total] - [Valor Mes Anterior]
```
*format: "R$ #,##0.00"*

```dax
Valor MoM % = DIVIDE ( [Valor Delta MoM], [Valor Mes Anterior] )
```
*format: "0.0%"*

```dax
Valor YTD = TOTALYTD ( [Valor Total], Calendario[Date] )
```
*format: "R$ #,##0.00"*

```dax
Valor YTD Ano Anterior = CALCULATE ( [Valor YTD], SAMEPERIODLASTYEAR ( Calendario[Date] ) )
```
*format: "R$ #,##0.00"*

```dax
Valor 12M Moveis =
CALCULATE ( [Valor Total], DATESINPERIOD ( Calendario[Date], LASTDATE ( Calendario[Date] ), -12, MONTH ) )
```
*format: "R$ #,##0.00"*

**displayFolder: "04 Participacao"**

```dax
% do Total Geral =
DIVIDE ( [Valor Total], CALCULATE ( [Valor Total], ALL ( 'licitacoes_2019_2024' ) ) )
```
*format: "0.0%"*

```dax
% da Categoria =
DIVIDE ( [Valor Total], CALCULATE ( [Valor Total], ALLEXCEPT ( 'licitacoes_2019_2024', 'licitacoes_2019_2024'[categoria_ia] ) ) )
```
*format: "0.0%"*

```dax
% do Ano =
DIVIDE ( [Valor Total], CALCULATE ( [Valor Total], ALLEXCEPT ( Calendario, Calendario[Ano] ) ) )
```
*format: "0.0%"*

**displayFolder: "05 Rankings"**

```dax
Rank Categoria =
IF ( HASONEVALUE ( 'licitacoes_2019_2024'[categoria_ia] ),
     RANKX ( ALL ( 'licitacoes_2019_2024'[categoria_ia] ), [Valor Total],, DESC, DENSE ) )
```
*format: "#,##0"*

```dax
Rank Fornecedor =
IF ( HASONEVALUE ( 'licitacoes_2019_2024'[nome] ),
     RANKX ( ALL ( 'licitacoes_2019_2024'[nome] ), [Valor Total],, DESC, DENSE ) )
```
*format: "#,##0"*

```dax
Fornecedor #1 Nome =
CALCULATE ( SELECTEDVALUE ( 'licitacoes_2019_2024'[nome] ),
            TOPN ( 1, VALUES ( 'licitacoes_2019_2024'[nome] ), [Valor Total], DESC ) )
```

```dax
Fornecedor #1 Valor =
MAXX ( TOPN ( 1, VALUES ( 'licitacoes_2019_2024'[nome] ), [Valor Total], DESC ), [Valor Total] )
```
*format: "R$ #,##0.00"*

```dax
Categoria #1 Nome =
CALCULATE ( SELECTEDVALUE ( 'licitacoes_2019_2024'[categoria_ia] ),
            TOPN ( 1, VALUES ( 'licitacoes_2019_2024'[categoria_ia] ), [Valor Total], DESC ) )
```

**displayFolder: "06 Concentracao"**

```dax
Valor Top 5 Fornecedores =
VAR Top5 = TOPN ( 5, VALUES ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ), [Valor Total], DESC )
RETURN CALCULATE ( [Valor Total], Top5 )
```
*format: "R$ #,##0.00"*

```dax
% Concentracao Top 5 Fornecedores =
DIVIDE ( [Valor Top 5 Fornecedores], CALCULATE ( [Valor Total], ALL ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ) ) )
```
*format: "0.0%"*

```dax
Valor Top 10 Fornecedores =
VAR Top10 = TOPN ( 10, VALUES ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ), [Valor Total], DESC )
RETURN CALCULATE ( [Valor Total], Top10 )
```
*format: "R$ #,##0.00"*

```dax
% Concentracao Top 10 Fornecedores =
DIVIDE ( [Valor Top 10 Fornecedores], CALCULATE ( [Valor Total], ALL ( 'licitacoes_2019_2024'[cpfCnpjVencedor] ) ) )
```
*format: "0.0%"*

**displayFolder: "07 Qualidade de Dados"**

```dax
Qtd Itens Sem Categoria =
CALCULATE ( [Qtd Linhas],
            'licitacoes_2019_2024'[categoria_ia] IN { "Sem Descrição", "Outros / Necessita Revisão", BLANK() } )
```
*format: "#,##0"*

```dax
% Itens Bem Categorizados = 1 - DIVIDE ( [Qtd Itens Sem Categoria], [Qtd Linhas] )
```
*format: "0.0%"*

```dax
Confianca Media = AVERAGE ( 'mapa_descricao'[confianca] )
```
*format: "0.000"*

```dax
Qtd Itens Baixa Confianca =
CALCULATE ( [Qtd Linhas],
            FILTER ( 'mapa_descricao', 'mapa_descricao'[confianca] < 0.5 && 'mapa_descricao'[confianca] > 0 ) )
```
*format: "#,##0"*

```dax
% Itens Baixa Confianca = DIVIDE ( [Qtd Itens Baixa Confianca], [Qtd Linhas] )
```
*format: "0.0%"*

**displayFolder: "08 Auxiliares"**

```dax
Valor Total Formatado =
VAR Valor = [Valor Total]
RETURN SWITCH ( TRUE (),
    Valor >= 1e9, FORMAT ( Valor / 1e9, "R$ #,##0.00" ) & " bi",
    Valor >= 1e6, FORMAT ( Valor / 1e6, "R$ #,##0.00" ) & " mi",
    Valor >= 1e3, FORMAT ( Valor / 1e3, "R$ #,##0.00" ) & " mil",
    FORMAT ( Valor, "R$ #,##0.00" ) )
```

```dax
Cor YoY =
SWITCH ( TRUE (),
    [Valor YoY %] > 0, "#16A34A",
    [Valor YoY %] < 0, "#DC2626",
    "#71717A" )
```

### 4. Adicionar relacionamento em `relationships.tmdl`

Adicionar:
- `Calendario[Date]` → `licitacoes_2019_2024[mes/ano]`
- cardinality: `one` → `many`
- crossFilteringBehavior: `OneDirection` (default)
- isActive: `true`

Gerar um GUID novo pro relacionamento. Manter o relacionamento existente com `mapa_descricao` intacto. Remover relacionamentos automáticos com `LocalDateTable_*` se existirem, pois serão substituídos pelo Calendario.

### 5. Verificação final

Antes de terminar:
1. Rode `git diff` (se for git) ou liste os arquivos modificados/criados
2. Confirme que os arquivos TMDL seguem a sintaxe correta do formato (indentação com 4 espaços, blocos `table`, `column`, `measure`, `partition`, `relationship`)
3. Confirme que não modificou os arquivos TMDL existentes das 3 tabelas originais (só criou novos e ajustou `relationships.tmdl`)
4. Me informe exatamente que arquivos foram criados/alterados

## O que NÃO fazer

- Não alterar colunas existentes nas 3 tabelas originais
- Não mexer em `Databrick Gov.SemanticModel/.pbi/*` ou `diagramLayout.json`
- Não criar medidas fora da tabela `_Medidas`
- Não inventar colunas que não estão na lista acima
- Não usar acentos nos nomes de arquivos TMDL (ex: `Medidas.tmdl`, não `Médidas.tmdl`)

## Referência TMDL rápida

Exemplo de estrutura esperada de `_Medidas.tmdl`:

```tmdl
table _Medidas
	lineageTag: <gerar-guid>

	measure 'Valor Total' = SUM ( 'licitacoes_2019_2024'[valor] )
		formatString: "R$ #,##0.00"
		lineageTag: <gerar-guid>
		displayFolder: "01 Valores Base"

	measure 'Qtd Itens' = SUM ( 'licitacoes_2019_2024'[quantidade] )
		formatString: "#,##0"
		lineageTag: <gerar-guid>
		displayFolder: "01 Valores Base"

	/// (demais medidas)

	partition _Medidas = calculated
		mode: import
		source = "{BLANK()}"

	annotation PBI_Id = <gerar-guid>
```

Quando terminar, me diga qual é o próximo passo recomendado (abrir o Power BI Desktop, validar, etc.).

---

## Notas extras (não incluir no prompt, são pra você)

- Se o Claude Code não conseguir achar algum campo, peça pra ele ler o TMDL da tabela correspondente pra confirmar o nome exato.
- Se der erro de sintaxe TMDL, abre o Power BI Desktop, faz um ajuste simples manualmente (tipo adicionar uma medida qualquer), salva, e inspeciona como ficou — esse é o padrão TMDL "oficial" que o Power BI escreve.
- Depois que o Claude Code terminar, abra o Power BI Desktop com o `.pbip`, e faça:
  1. *Modelagem → Marcar como tabela de datas* na `Calendario` (se ainda não tiver sido marcada via TMDL).
  2. Ir na visualização de Modelo e conferir se o relacionamento `Calendario[Date] → licitacoes_2019_2024[mes/ano]` ficou ativo.
  3. Soltar uma medida num card pra validar (`[Valor Total]`).
