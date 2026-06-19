# PBIR/PBIP — Research & Learnings

All patterns, gotchas, and discoveries from hands-on experimentation with Power BI PBIP files.

---

## 1. Project Structure (PBIR Format)

```
projeto.pbip                              ← entry point
├── projeto.Report/
│   ├── definition.pbir                   ← version + semantic model reference
│   ├── definition/
│   │   ├── report.json                   ← themes, settings
│   │   ├── version.json                  ← PBIR version (2.0.0)
│   │   └── pages/
│   │       ├── pages.json                ← page order + active page
│   │       └── <pageId>/
│   │           ├── page.json             ← page definition
│   │           └── visuals/
│   │               └── <visualId>/
│   │                   └── visual.json   ← individual visual
│   └── StaticResources/                  ← themes, images
├── projeto.SemanticModel/
│   └── definition/
│       ├── model.tmdl                    ← data model root
│       ├── database.tmdl                 ← compat level
│       ├── tables/<tableName>.tmdl       ← one file per table
│       └── cultures/pt-BR.tmdl           ← localization
└── .gitignore
```

---

## 2. Color Format — The #1 Gotcha

> [!CAUTION]
> Plain hex strings like `"color": "#FFFFFF"` are **silently ignored** by Power BI Desktop. They get replaced with `"solid": {}` (theme default) on save.

### ❌ Wrong — plain string (silently ignored)
```json
"color": {
  "solid": {
    "color": "#162447"
  }
}
```

### ✅ Correct — Literal expression with single-quoted hex
```json
"color": {
  "solid": {
    "color": {
      "expr": {
        "Literal": {
          "Value": "'#162447'"
        }
      }
    }
  }
}
```

### ✅ Also valid — ThemeDataColor reference (PBI generates this)
```json
"color": {
  "solid": {
    "color": {
      "expr": {
        "ThemeDataColor": {
          "ColorId": 1,
          "Percent": 0
        }
      }
    }
  }
}
```

**Rule**: All property values in PBIR use the `expr → Literal → Value` wrapper. Hex colors must be wrapped in **single quotes** inside the Value string: `"'#FF0000'"`.

---

## 3. TMDL Syntax Patterns

### Calculated Tables

> [!WARNING]
> The keyword `calculatedTable` does NOT exist in TMDL. Use a `partition` block.

```tmdl
table SampleData
    lineageTag: <guid>

    column MyColumn
        lineageTag: <guid>
        isNameInferred
        sourceColumn: [MyColumn]

    measure MyMeasure = SUM(SampleData[Value])
        formatString: #,##0
        lineageTag: <guid>

    partition SampleData = calculated
        mode: import
        source =
                DATATABLE(
                    "MyColumn", STRING,
                    "Value", DOUBLE,
                    {
                        {"Row1", 100},
                        {"Row2", 200}
                    }
                )
```

Key discoveries:
- Use `partition <name> = calculated` + `source =` (not `expression =`)
- Columns use `isNameInferred` + `sourceColumn: [ColumnName]` (with brackets)
- PBI auto-generates `lineageTag` GUIDs for columns on first load
- PBI removes `dataType` from columns — they're inferred from the calculated table

### Multi-line DAX Measures

> [!WARNING]
> `lineageTag` at the same indentation as expression lines gets parsed as DAX!

```tmdl
# ❌ Wrong — lineageTag parsed as part of DAX expression
    measure MyMeasure =
        VAR x = 1
        RETURN x
        lineageTag: <guid>

# ✅ Correct — expression at 3 tabs, properties at 2 tabs
    measure MyMeasure =
            VAR x = 1
            RETURN x
        lineageTag: <guid>
```

**Rule**: Multi-line expressions must be indented **one level deeper** than properties to disambiguate from TMDL keywords.

### Backtick-Fenced DAX Syntax (Discovered in Governança BI)

> [!IMPORTANT]
> Power BI Desktop uses **triple backticks** (`` ``` ``) to fence multi-line DAX in both measures and calculated table partitions. This is an alternative to the indentation-based approach above.

```tmdl
	measure 'Disponibilidade %' = ```
		VAR MinutosIndisponiveisNoContexto = [Total Minutos Indisponíveis]
		VAR DiasNoContexto = COUNTROWS('dCalendario')
		VAR TotalMinutosNoContexto = DiasNoContexto * 1440
		RETURN
		    IF(
		        DiasNoContexto = 0,
		        BLANK(),
		        1 - DIVIDE( MinutosIndisponiveisNoContexto, TotalMinutosNoContexto )
		    )
		```
		formatString: 0.00%;-0.00%;0.00%
		lineageTag: <guid>
```

Also works for calculated table partitions:
```tmdl
	partition dCalendario = calculated
		mode: import
		source = ```
			VAR MinhaDataMinima = MIN('Tabela'[Data])
			VAR MinhaDataMaxima = MAX('Tabela'[Data])
			RETURN
			    ADDCOLUMNS(
			        CALENDAR(MinhaDataMinima, MinhaDataMaxima),
			        "Ano", YEAR([Date]),
			        "Mês Num", MONTH([Date]),
			        "Nome Mês", FORMAT([Date], "mmmm")
			    )
			```
```

> [!TIP]
> The backtick syntax is what PBI Desktop generates when it saves. Both approaches (backticks and indentation-only) work correctly.

### Power Query/M Partitions (`partition = m`)

> [!IMPORTANT]
> Real data sources (SharePoint, SQL, Excel, etc.) use `partition = m` with Power Query/M code — NOT `partition = calculated`.

```tmdl
	partition 'MeuDados' = m
		mode: import
		source =
			let
			    Fonte = SharePoint.Tables("https://site.sharepoint.com/sites/MeuSite", [Implementation="2.0", ViewMode="All"]),
			    #"tabela-id" = Fonte{[Id="tabela-guid-aqui"]}[Items],
			    #"Colunas Removidas" = Table.RemoveColumns(#"tabela-id", {"ID", "Título", "Modificado", "Criado"}),
			    #"Tipo Alterado" = Table.TransformColumnTypes(#"Colunas Removidas", {{"Data", type date}, {"Valor", Int64.Type}})
			in
			    #"Tipo Alterado"

	annotation PBI_NavigationStepName = Navegação
	annotation PBI_ResultType = Table
```

**Partition types**: `calculated` (DAX/DATATABLE), `m` (Power Query/M)

### Calculated Columns (Inline DAX)

Calculated columns use inline DAX directly in the column definition:
```tmdl
	column '% Executado' = 'MinhaTabela'[REALIZADO] / 'MinhaTabela'[PREVISTO]
		formatString: 0.00%;-0.00%;0.00%
		lineageTag: <guid>
		summarizeBy: sum
		annotation SummarizationSetBy = Automatic

	column 'Data Chave' = DATE([ANO], 1, 1)
		formatString: General Date
		lineageTag: <guid>
		summarizeBy: none
		annotation SummarizationSetBy = Automatic
```

### Column Properties (Full Reference)

| Property | Example | Notes |
|----------|---------|-------|
| `dataType` | `string`, `int64`, `double`, `decimal`, `dateTime` | Data type |
| `formatString` | `0`, `0.00%`, `#,0.00`, `Long Date`, `General Date` | Display format |
| `lineageTag` | `<guid>` | Unique identifier |
| `summarizeBy` | `sum`, `none` | Default aggregation |
| `sourceColumn` | `Column Name` | Source column name (without brackets for M sources) |
| `isNameInferred` | (flag) | Auto-inferred name (calculated tables only) |
| `sortByColumn` | `'Mês Num'` | Sort this column by another |
| `dataCategory` | `Years`, `Months`, `DayOfMonth`, `PaddedDateTableDates` | Semantic category |
| `isHidden` | (flag) | Column is hidden from users |
| `changedProperty` | `= DataType`, `= IsHidden`, `= SortByColumn` | Tracks manual changes |

### `variation` Block (Date Column Auto-Hierarchy)

Date columns auto-generate local date tables via `variation`:
```tmdl
	column 'Data Início'
		dataType: dateTime
		formatString: Long Date
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: Data Início
		variation Variation
			isDefault
			relationship: <relationship-guid>
			defaultHierarchy: LocalDateTable_<guid>.'Hierarquia de datas'
		annotation SummarizationSetBy = Automatic
		annotation UnderlyingDateTimeDataType = Date
```

### `hierarchy` Block (Date Hierarchies)

```tmdl
	hierarchy 'Data da Resposta Hierarquia'
		lineageTag: <guid>

		level 'Data da Resposta'
			lineageTag: <guid>
			column: 'Data da Resposta'

		changedProperty = IsHidden
```

System date tables have a standard 4-level hierarchy:
```tmdl
	hierarchy 'Hierarquia de datas'
		lineageTag: <guid>

		level Ano
			lineageTag: <guid>
			column: Ano

		level Trimestre
			lineageTag: <guid>
			column: Trimestre

		level Mês
			lineageTag: <guid>
			column: Mês

		level Dia
			lineageTag: <guid>
			column: Dia

		annotation TemplateId = DateHierarchy
```

### Table-Level Properties

| Property | Notes |
|----------|-------|
| `isHidden` | Table hidden from users |
| `isPrivate` | System table (e.g., DateTableTemplate) |
| `showAsVariationsOnly` | Auto-generated local date tables |
| `changedProperty = IsHidden` | Tracks manual hide |

> [!WARNING]
> **`isDataTable` does NOT exist in TMDL.** Using it causes `UnknownKeyword` parse error.
> "Mark as date table" is done via Power BI Desktop UI (Modelagem → Marcar como tabela de datas)
> or via annotation. The `dataCategory: Time` on the date column is the only TMDL-side config needed.

> [!WARNING]
> **Power BI reads ALL `.tmdl` files in `tables/`, not just those referenced in `model.tmdl`.**
> If a LocalDateTable file with `showAsVariationsOnly` exists on disk but has no `variation` pointing
> to it (e.g. after you delete the relationship), Power BI will error even if you removed its `ref`
> from `model.tmdl`. Fix: **delete the `.tmdl` file from disk**.

### Annotations (Metadata)

Common PBI-generated annotations:
```tmdl
	annotation SummarizationSetBy = Automatic
	annotation PBI_FormatHint = {"isGeneralNumber":true}
	annotation PBI_FormatHint = {"isDateTimeCustom":true}
	annotation PBI_FormatHint = {"currencyCulture":"pt-BR"}
	annotation UnderlyingDateTimeDataType = Date
	annotation PBI_NavigationStepName = Navegação
	annotation PBI_ResultType = Table
	annotation __PBI_TemplateDateTable = true
	annotation DefaultItem = DateHierarchy
	annotation TemplateId = Year
```

---

## 3.1. Relationships (relationships.tmdl)

```tmdl
relationship <guid>
	fromColumn: 'SourceTable'.'ColumnName'
	toColumn: 'TargetTable'.'ColumnName'
```

### Relationship Properties

| Property | Values | Notes |
|----------|--------|-------|
| `crossFilteringBehavior` | `bothDirections` | Default is single direction (omitted) |
| `joinOnDateBehavior` | `datePartOnly` | Date-only join (ignores time) |
| `toCardinality` | `many` | Many-to-many (default is many-to-one, omitted) |

> [!WARNING]
> **`cardinality: manyToOne` does NOT exist.** Causes `UnknownKeyword` parse error.
> Many-to-one is the default — simply omit the property. Only `toCardinality: many` exists (for many-to-many).

> [!WARNING]
> **When replacing a LocalDateTable relationship with a custom Calendario relationship:**
> 1. Remove the old relationship from `relationships.tmdl`
> 2. Remove the `variation` block from the source column (e.g. `mes/ano`) in its `.tmdl` file —
>    the variation stores the relationship GUID and will cause a dangling-reference error if left
> 3. Delete the orphaned `LocalDateTable_<guid>.tmdl` file from disk (removing `ref` from
>    `model.tmdl` is NOT enough — PBI still reads the file)

### Example: Various Relationship Types
```tmdl
# Simple (many-to-one, single direction)
relationship <guid>
	fromColumn: 'Vendas'.'Data'
	toColumn: 'Calendario'.'Date'

# Bi-directional
relationship <guid>
	crossFilteringBehavior: bothDirections
	fromColumn: 'Categorias'.'Data Chave'
	toColumn: 'Calendario'.'Date'

# Many-to-many + bi-directional
relationship <guid>
	crossFilteringBehavior: bothDirections
	toCardinality: many
	fromColumn: 'Calendario'.'Ano'
	toColumn: 'Dotação'.'Ano'

# Date-only join
relationship <guid>
	joinOnDateBehavior: datePartOnly
	fromColumn: 'Contratos'.'Data Vigência'
	toColumn: LocalDateTable_<guid>.Date
```

---

## 3.2. model.tmdl Extended Reference

```tmdl
model Model
	culture: pt-BR
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: pt-BR
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

annotation PBI_QueryOrder = ["Table1","Table2","Table3"]
annotation __PBI_TimeIntelligenceEnabled = 1
annotation PBI_ProTooling = ["DevMode"]

ref table 'Table1'
ref table 'Table2'
ref table dCalendario

ref cultureInfo pt-BR
```

> [!NOTE]
> `PBI_QueryOrder` controls the order tables appear in Power Query Editor. `PBI_ProTooling = ["DevMode"]` is set for PBIP projects.

---

## 4. Visual Container Schema (v2.6.0)

### Required properties
```json
{
  "$schema": "...visualContainer/2.6.0/schema.json",
  "name": "unique_visual_id",       // required
  "position": {                      // required
    "x": 40, "y": 80,               // required
    "height": 180, "width": 370,    // required
    "z": 1000,                      // stacking order
    "tabOrder": 0                   // keyboard nav
  },
  "visual": { ... }                  // or "visualGroup"
}
```

### Visual Configuration (v2.2.0)

```json
"visual": {
  "visualType": "card",              // required: card, clusteredBarChart, etc.
  "query": {
    "queryState": {
      "Values": {                    // role name (varies by visual type)
        "projections": [{
          "field": {
            "Measure": {
              "Expression": {
                "SourceRef": { "Entity": "TableName" }
              },
              "Property": "MeasureName"
            }
          },
          "queryRef": "TableName.MeasureName"
        }]
      }
    }
  },
  "objects": { ... },                // visual-specific formatting
  "visualContainerObjects": { ... }  // container formatting (bg, border, title)
}
```

### Visual Container Objects (formatting that works)

| Object | Properties | Notes |
|--------|-----------|-------|
| `background` | `show`, `color`, `transparency` | Card background |
| `border` | `show`, `color`, `radius` | Rounded corners with `radius` |
| `title` | `show`, `text`, `fontColor`, `fontSize`, `fontFamily`, `bold` | Visual title |
| `visualHeader` | `show` | Hide the hover header icons |
| `padding` | `top`, `left` | Internal padding |

### Visual-specific Objects (for `card` type)

| Object | Properties | Notes |
|--------|-----------|-------|
| `labels` | `color`, `fontSize`, `fontFamily` | Main value display |
| `categoryLabels` | `show`, `color`, `fontSize` | Subtitle under the value |

### Visual-specific Objects (for `cardVisual` — new card)

> [!IMPORTANT]
> The new `cardVisual` type uses role name `Data` (not `Values` like the old `card`). It also uses `selector: {"id": "default"}` on most objects.

| Object | Properties | Notes |
|--------|-----------|-------|
| `value` | `show`, `horizontalAlignment`, `fontColor` | Main value display |
| `accentBar` | `show`, `position` | Accent decoration bar |
| `outline` | `show` | Card outline |
| `layout` | `rectangleRoundedCurveCustomStyle`, `backgroundShow`, `backgroundFillColor`, `backgroundTransparency` | Card shape/layout |
| `fillCustom` | `fillColor` | Custom fill color |
| `label` | `fontColor` | Category label |

```json
// cardVisual query uses "Data" role (not "Values"):
"query": {
  "queryState": {
    "Data": {
      "projections": [{
        "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "TABLE" } }, "Property": "MEASURE" } },
        "queryRef": "TABLE.MEASURE",
        "nativeQueryRef": "Display Name",
        "displayName": "Display Name"
      }]
    }
  }
}
```

---

## 4.1. Slicer Visual Schema

```json
{
  "$schema": "...visualContainer/2.6.0/schema.json",
  "name": "unique_id",
  "position": { "x": 48, "y": 7, "z": 1000, "height": 50, "width": 686, "tabOrder": 1000 },
  "visual": {
    "visualType": "slicer",
    "query": {
      "queryState": {
        "Values": {
          "projections": [{
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "TABLE" } }, "Property": "COLUMN" } },
            "queryRef": "TABLE.COLUMN",
            "nativeQueryRef": "COLUMN",
            "active": true
          }]
        }
      }
    },
    "objects": {
      "data": [{
        "properties": {
          "mode": { "expr": { "Literal": { "Value": "'Dropdown'" } } },
          "isInvertedSelectionMode": { "expr": { "Literal": { "Value": "true" } } }
        }
      }],
      "general": [{
        "properties": {
          "orientation": { "expr": { "Literal": { "Value": "0D" } } }
        }
      }],
      "selection": [{
        "properties": {
          "selectAllCheckboxEnabled": { "expr": { "Literal": { "Value": "true" } } },
          "strictSingleSelect": { "expr": { "Literal": { "Value": "false" } } }
        }
      }],
      "items": [{
        "properties": {
          "textSize": { "expr": { "Literal": { "Value": "15D" } } },
          "bold": { "expr": { "Literal": { "Value": "true" } } },
          "fontColor": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 1, "Percent": 0 } } } } },
          "background": { "solid": { "color": { "expr": { "ThemeDataColor": { "ColorId": 0, "Percent": 0 } } } } }
        }
      }],
      "header": [{
        "properties": {
          "textSize": { "expr": { "Literal": { "Value": "12D" } } },
          "show": { "expr": { "Literal": { "Value": "false" } } }
        }
      }]
    },
    "visualContainerObjects": {
      "background": [{ "properties": { "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0097B2'" } } } } } } }],
      "border": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } }, "radius": { "expr": { "Literal": { "Value": "25D" } } } } }],
      "title": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
      "padding": [{ "properties": { "left": { "expr": { "Literal": { "Value": "20D" } } }, "top": { "expr": { "Literal": { "Value": "0D" } } } } }],
      "dropShadow": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }]
    },
    "syncGroup": {
      "groupName": "SlicerGroupName",
      "fieldChanges": true,
      "filterChanges": true
    },
    "drillFilterOtherVisuals": true
  },
  "parentGroupName": "parent_group_id"
}
```

### Slicer objects reference

| Object | Property | Values | Notes |
|--------|----------|--------|-------|
| `data` | `mode` | `'Dropdown'`, `'List'` | Display mode |
| `data` | `isInvertedSelectionMode` | `true`/`false` | "Select All" default behavior |
| `general` | `orientation` | `0D` (vertical), `1D` (horizontal) | Slicer orientation |
| `selection` | `selectAllCheckboxEnabled` | `true`/`false` | Show "Select All" checkbox |
| `selection` | `strictSingleSelect` | `true`/`false` | Single selection only |
| `items` | `textSize`, `bold`, `fontColor`, `background` | — | Dropdown item formatting |
| `header` | `textSize`, `show`, `fontColor`, `background` | — | Slicer header formatting |

### `syncGroup` (Cross-Page Slicer Sync)

```json
"syncGroup": {
  "groupName": "Ano",       // Slicers with the same groupName sync across pages
  "fieldChanges": true,      // Sync field changes
  "filterChanges": true      // Sync filter selection changes
}
```

---

## 4.2. Textbox Visual Schema

```json
{
  "$schema": "...visualContainer/2.6.0/schema.json",
  "name": "unique_id",
  "position": { "x": 14, "y": 16, "z": 2000, "height": 35, "width": 50, "tabOrder": 2000 },
  "visual": {
    "visualType": "textbox",
    "objects": {
      "general": [{
        "properties": {
          "paragraphs": [{
            "textRuns": [{
              "value": "My Text Here",
              "textStyle": {
                "fontSize": "12pt",
                "color": "#ffffff"
              }
            }],
            "horizontalTextAlignment": "center"
          }]
        }
      }]
    },
    "visualContainerObjects": {
      "background": [{
        "properties": {
          "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0097B2'" } } } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```

> [!NOTE]
> Textbox uses plain color strings in `textStyle` (not the `expr → Literal → Value` pattern). Only `visualContainerObjects` uses the expression pattern.

---

## 4.3. Shape Visual Schema

```json
{
  "$schema": "...visualContainer/2.6.0/schema.json",
  "name": "unique_id",
  "position": { "x": 0, "y": 0, "z": 0, "height": 547, "width": 746, "tabOrder": 1000 },
  "visual": {
    "visualType": "shape",
    "objects": {
      "shape": [{
        "properties": {
          "tileShape": { "expr": { "Literal": { "Value": "'rectangle'" } } }
        }
      }],
      "rotation": [{
        "properties": {
          "shapeAngle": { "expr": { "Literal": { "Value": "0L" } } },
          "angle": { "expr": { "Literal": { "Value": "270D" } } }
        }
      }],
      "fill": [{
        "properties": {
          "fillColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0097B2'" } } } } }
        },
        "selector": { "id": "default" }
      }],
      "outline": [{
        "properties": {
          "lineColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#007DA4'" } } } } }
        },
        "selector": { "id": "default" }
      }],
      "text": [
        { "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } },
        {
          "properties": {
            "text": { "expr": { "Literal": { "Value": "'MY TEXT'" } } },
            "fontSize": { "expr": { "Literal": { "Value": "8D" } } },
            "bold": { "expr": { "Literal": { "Value": "true" } } }
          },
          "selector": { "id": "default" }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

### Shape object reference

| Object | Property | Values | Notes |
|--------|----------|--------|-------|
| `shape` | `tileShape` | `'rectangle'`, `'rectangleRounded'` | Shape type |
| `rotation` | `shapeAngle` | `0L` | Rotation in legacy format |
| `rotation` | `angle` | `270D` | Actual rotation degrees |
| `fill` | `fillColor` | Color expr | Background fill |
| `outline` | `lineColor` | Color expr | Border line color |
| `text` | `show`, `text`, `fontSize`, `bold` | — | Text overlay on shape |

> [!NOTE]
> Shape objects use `selector: { "id": "default" }` on `fill`, `outline`, and `text` blocks.

---

## 4.4. Image Visual Schema

```json
{
  "$schema": "...visualContainer/2.6.0/schema.json",
  "name": "unique_id",
  "position": { "x": 0, "y": 0, "z": 4500, "height": 149, "width": 120, "tabOrder": 0 },
  "visual": {
    "visualType": "image",
    "objects": {
      "general": [{
        "properties": {
          "imageUrl": {
            "expr": {
              "ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": "MyImage123456789.png"
              }
            }
          }
        }
      }]
    },
    "visualContainerObjects": {
      "title": [{
        "properties": {
          "text": { "expr": { "Literal": { "Value": "'Image Label'" } } }
        }
      }],
      "visualLink": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "type": { "expr": { "Literal": { "Value": "'PageNavigation'" } } },
          "navigationSection": { "expr": { "Literal": { "Value": "'target_page_name'" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  },
  "howCreated": "InsertVisualButton"
}
```

### Image source: `ResourcePackageItem`

Images are referenced from `report.json` → `resourcePackages`:
```json
// In report.json:
"resourcePackages": [{
  "name": "RegisteredResources",
  "type": "RegisteredResources",
  "items": [
    { "name": "MyImage123456789.png", "path": "MyImage123456789.png", "type": "Image" }
  ]
}]
```

Image files are stored in: `projeto.Report/StaticResources/RegisteredResources/`

### `visualLink` (Page Navigation Action)

```json
"visualLink": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "type": { "expr": { "Literal": { "Value": "'PageNavigation'" } } },
    "navigationSection": { "expr": { "Literal": { "Value": "'target_page_name'" } } },
    "tooltip": { "expr": { "Literal": { "Value": "'Click to navigate'" } } }
  }
}]
```

---

## 4.5. Visual Group (Container)

```json
{
  "$schema": "...visualContainer/2.6.0/schema.json",
  "name": "group_unique_id",
  "position": { "x": 1568, "y": 83, "z": 4500, "height": 543, "width": 122, "tabOrder": 4000 },
  "visualGroup": {
    "displayName": "Group Display Name",
    "groupMode": "ScaleMode"
  },
  "parentGroupName": "outer_group_id"
}
```

### Nesting visuals in groups: `parentGroupName`

Any visual container can belong to a group by setting `parentGroupName`:
```json
{
  "name": "child_visual_id",
  "position": { ... },
  "visual": { ... },
  "parentGroupName": "group_unique_id"
}
```

Visual groups can be nested (groups inside groups) with `parentGroupName` referencing another group's `name`.

### `howCreated` property

Tracks how the visual was inserted: `"InsertVisualButton"`. This is auto-added by PBI Desktop.

---

## 4.6. Additional Container Objects

| Object | Properties | Notes |
|--------|-----------|-------|
| `dropShadow` | `show` | Drop shadow effect |
| `visualLink` | `show`, `type`, `navigationSection`, `tooltip` | Page navigation action |
| `general` | `keepLayerOrder`, `altText` | Layer order + accessibility |
| `padding` | `top`, `left`, `bottom`, `right` | All use `"ND"` format |

### Dynamic Title from Measure

Visual titles can be driven by a DAX measure instead of static text:
```json
"title": [{
  "properties": {
    "text": {
      "expr": {
        "Measure": {
          "Expression": { "SourceRef": { "Entity": "TABLE" } },
          "Property": "TITLE_MEASURE"
        }
      }
    },
    "fontSize": { "expr": { "Literal": { "Value": "20D" } } },
    "bold": { "expr": { "Literal": { "Value": "true" } } },
    "alignment": { "expr": { "Literal": { "Value": "'center'" } } }
  }
}]
```

---

## 4.7. Selector Patterns (Conditional Formatting)

### `selector: {"id": "default"}`
Used for default formatting on shapes, new cards, etc.:
```json
"fill": [{
  "properties": { "fillColor": { ... } },
  "selector": { "id": "default" }
}]
```

### `selector: {"metadata": "..."}`
Used for coloring data series by their query reference:
```json
"dataPoint": [{
  "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0097B2'" } } } } } },
  "selector": { "metadata": "Sum(4 iGovTIC.MÉDIAS ESTADUAIS)" }
}]
```

### `selector: {"data": [...]}` — Conditional by value
Used to color specific data values differently:
```json
"dataPoint": [{
  "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00C800'" } } } } } },
  "selector": {
    "data": [{
      "scopeId": {
        "Comparison": {
          "ComparisonKind": 0,
          "Left": {
            "Column": {
              "Expression": { "SourceRef": { "Entity": "TABLE" } },
              "Property": "COLUMN"
            }
          },
          "Right": { "Literal": { "Value": "'ValueToMatch'" } }
        }
      }
    }]
  }
}]
```

`ComparisonKind`: 0 = Equal

---

## 4.8. Chart Visual Objects Reference

### Chart query roles

| Visual Type | Roles |
|-------------|-------|
| `clusteredColumnChart` | `Category`, `Y`, `Series` |
| `lineClusteredColumnComboChart` | `Category`, `Y`, `Y2` |
| `lineStackedColumnComboChart` | `Category`, `Y`, `Y2` |
| `card` | `Values` |
| `cardVisual` (new) | `Data` |
| `slicer` | `Values` |
| `htmlContent...` | `content` |
| `deneb...` | `dataset` |

### Common chart objects

| Object | Key Properties |
|--------|---------------|
| `categoryAxis` | `fontSize`, `bold`, `labelColor`, `showAxisTitle`, `gridlineShow`, `innerPadding` |
| `valueAxis` | `fontSize`, `bold`, `show`, `showAxisTitle`, `secShow` (secondary), `labelPrecision` |
| `labels` | `show`, `fontSize`, `bold`, `color`, `labelDensity`, `labelPosition` (`'OutsideEnd'`) |
| `legend` | `show`, `showTitle`, `position` (`'TopRight'`), `labelColor` |
| `dataPoint` | `fill` (with optional `selector`) |
| `lineStyles` | `strokeWidth`, `lineChartType` (`'linear'`), `strokeLineJoin` |
| `zoom` | `show`, `showOnValueAxis` |

### Reference Lines (`y1AxisReferenceLine`)

```json
"y1AxisReferenceLine": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "displayName": { "expr": { "Literal": { "Value": "'Meta'" } } },
    "value": { "expr": { "Literal": { "Value": "90D" } } },
    "lineColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00E600'" } } } } },
    "transparency": { "expr": { "Literal": { "Value": "0D" } } },
    "dataLabelShow": { "expr": { "Literal": { "Value": "true" } } },
    "dataLabelText": { "expr": { "Literal": { "Value": "'Name'" } } },
    "dataLabelColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#00EA00'" } } } } }
  },
  "selector": { "id": "2" }
}]
```

Multiple reference lines use sequential `selector.id`: `"2"`, `"3"`, `"4"`, etc.

### `HierarchyLevel` field type (for chart axes)

```json
"field": {
  "HierarchyLevel": {
    "Expression": {
      "Hierarchy": {
        "Expression": { "SourceRef": { "Entity": "TABLE" } },
        "Hierarchy": "HierarchyName"
      }
    },
    "Level": "LevelName"
  }
}
```

### `Aggregation` field type (explicit aggregation)

```json
"field": {
  "Aggregation": {
    "Expression": {
      "Column": {
        "Expression": { "SourceRef": { "Entity": "TABLE" } },
        "Property": "COLUMN"
      }
    },
    "Function": 0
  }
}
```

`Function`: 0 = Sum, 1 = Avg, 2 = Min, 3 = Max, 4 = Count, 5 = CountNonNull

## 5. Page Schema (v2.0.0)

> [!WARNING]
> The old `config` property is **invalid** in PBIR v2.0.0 — use `objects` instead.

```json
{
  "$schema": "...page/2.0.0/schema.json",
  "name": "dashboard01",
  "displayName": "Dashboard",
  "displayOption": "FitToPage",
  "height": 720,
  "width": 1280,
  "pageBinding": {
    "name": "hex_id_here",
    "type": "Default",
    "parameters": []
  },
  "objects": {
    "background": [
      {
        "properties": {
          "color": {
            "solid": {
              "color": {
                "expr": {
                  "Literal": { "Value": "'#1B1B2F'" }
                }
              }
            }
          }
        }
      }
    ],
    "outspace": [
      {
        "properties": {
          "color": {
            "solid": {
              "color": {
                "expr": {
                  "Literal": { "Value": "'#1B1B2F'" }
                }
              }
            }
          }
        }
      }
    ]
  }
}
```

> [!NOTE]
> `pageBinding` is auto-generated by PBI Desktop. `outspace` controls the color outside the page area (when the viewport is larger than the page).

---

## 6. Pages Metadata

```json
{
  "$schema": "...pagesMetadata/1.0.0/schema.json",
  "pageOrder": ["page1_id", "page2_id"],
  "activePageName": "page2_id"
}
```

- Page/visual IDs can be human-readable names (e.g., `dashboard01`)
- PBI preserves your custom names after save

---

## 7. HTML Content Visual — Deep Dive

### Available Visuals (4 Options)

| Visual | Developer | Certified | External URLs | Export PDF/PPT |
|--------|-----------|-----------|---------------|----------------|
| **HTML Content (Lite)** | Daniel Marsh-Patrick | ✅ Yes | ❌ No | ✅ Yes |
| **HTML Content (Regular)** | Daniel Marsh-Patrick | ❌ No | ✅ Yes | ❌ No |
| **HTML VizCreator Cert** | BI Samurai | ✅ Yes | ❌ No | ✅ Yes |
| **HTML VizCreator Flex** | BI Samurai | ❌ No | ✅ Yes | ❌ No |

> [!TIP]
> For the **Figma → HTML/CSS → Power BI** workflow, start with **HTML Content (Regular)** for maximum flexibility. Switch to Lite/Cert for production reports that need PDF export.

### Supported CSS Features

Since the visual renders in a **browser sandbox**, it supports virtually all modern CSS:

| Feature | Supported | Notes |
|---------|-----------|-------|
| **Flexbox** | ✅ | Full support for layouts |
| **CSS Grid** | ✅ | Complex grid layouts work |
| **Gradients** | ✅ | `linear-gradient`, `radial-gradient` |
| **Box Shadows** | ✅ | `box-shadow` for depth effects |
| **Border Radius** | ✅ | Rounded corners |
| **CSS Animations** | ✅ | `@keyframes`, `transition` |
| **Custom Fonts** | ⚠️ | Inline `@font-face` with data URLs only (certified) |
| **SVG** | ✅ | All tags except `<use>`, `<script>`, `<foreignObject>` |
| **Images** | ⚠️ | Data URLs only (certified) / External URLs (uncertified) |
| **Backdrop Filter** | ✅ | Glassmorphism effects |
| **CSS Variables** | ✅ | `var(--custom-prop)` |

### Supported HTML Tags (Lite/Certified)

`<a>`, `<div>`, `<span>`, `<p>`, `<h1>`-`<h6>`, `<table>`, `<tr>`, `<td>`, `<th>`,
`<ul>`, `<ol>`, `<li>`, `<img>` (data URLs), `<br>`, `<hr>`, `<strong>`, `<em>`,
`<b>`, `<i>`, `<u>`, `<code>`, `<pre>`, `<blockquote>`, `<sub>`, `<sup>`, all SVG tags

### Limitations

- **Sandbox**: Runs in an iframe with `null://` origin — no access to `powerbi.com` DOM
- **CORS**: Cannot embed content from sites with CORS restrictions
- **PBI Desktop vs Service**: Rendering may differ (Desktop is not a full browser)
- **Performance**: Re-renders entirely on every slicer/filter change
- **No JavaScript**: Cannot execute `<script>` tags (security)
- **No external URLs** in certified versions (images must be base64 data URLs)
- `<a href="#bookmark">` links don't work (sandbox has no origin)

### How Data Flows: DAX → HTML

```
DAX Measure → returns HTML string → HTML Content visual renders it
```

The visual accepts **one field** that contains an HTML string. This can be:
1. A DAX **measure** that builds HTML dynamically from data
2. A **column** in a table containing pre-built HTML strings
3. A **calculated column** combining data + HTML formatting

### Figma → HTML/CSS → Power BI Workflow

```mermaid
flowchart LR
    A["🎨 Figma Design"] --> B["💻 HTML/CSS Export"]
    B --> C["📝 Convert to DAX Measure\n(HTML string)"]
    C --> D["📊 Power BI\nHTML Content Visual"]
```

**Step-by-step:**
1. Design the visual card/component in **Figma**
2. Export as **HTML/CSS** (manually or via Figma plugins)
3. Convert the HTML to a **DAX measure** that returns the HTML string
4. Parameterize the HTML with DAX expressions (swap hardcoded values with `FORMAT([Measure], ...)`)
5. Add the **HTML Content visual** to your report
6. Bind the DAX measure to the visual's data field
7. Extract the resulting `visual.json` as a **template for code generation**

---

## 8. PBI Desktop Behavior on Load

What PBI Desktop does when it opens a PBIP project:

1. **Validates JSON** against the declared `$schema`
2. **Strips unrecognized properties** (e.g., `config` → error)
3. **Replaces plain color strings** with `"solid": {}` (theme default)
4. **Regenerates column definitions** with `isNameInferred`, auto lineageTags
5. **Adds `filterConfig`** blocks to visuals automatically
6. **Re-indents JSON** to 2-space indentation
7. **Reorders certain properties** (e.g., `height` before `width`)

---

## 9. JSON Schemas Reference

All schemas published at: [github.com/microsoft/json-schemas/fabric/item/report/definition](https://github.com/microsoft/json-schemas/tree/main/fabric/item/report/definition)

| Schema | Version | Purpose |
|--------|---------|---------|
| `visualContainer` | 2.6.0 | Individual visual definition |
| `visualConfiguration` | 2.2.0 | Visual type, query, objects |
| `page` | 2.0.0 | Page layout and background |
| `pagesMetadata` | 1.0.0 | Page ordering |
| `report` | 3.1.0 | Report settings, themes |
| `versionMetadata` | 1.0.0 | PBIR format version |
| `formattingObjectDefinitions` | 1.4.0 | Formatting property types |
| `semanticQuery` | 1.3.0 | Data query expressions |

---

## 10. Useful DAX Patterns for Code Generation

### Calculated table with sample data
```dax
DATATABLE(
    "Column1", STRING,
    "Column2", DOUBLE,
    {
        {"value1", 100},
        {"value2", 200}
    }
)
```

### HTML measure for HTML Content visual
```dax
"<div style='...'>" &
"<h2>" & FORMAT([Measure], "#,##0") & "</h2>" &
"</div>"
```

---

## 11. HTML Content Visual — Template (Extracted from PBI Desktop)

> [!IMPORTANT]
> This is the exact JSON that Power BI Desktop generates for the HTML Content visual. Use this as a reusable template for code generation.

### visual.json Template
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.6.0/schema.json",
  "name": "YOUR_UNIQUE_ID_HERE",
  "position": {
    "x": 40,
    "y": 310,
    "z": 2001,
    "height": 180,
    "width": 280,
    "tabOrder": 2001
  },
  "visual": {
    "visualType": "htmlContent443BE3AD55E043BF878BED274D3A6855",
    "query": {
      "queryState": {
        "content": {
          "projections": [
            {
              "field": {
                "Measure": {
                  "Expression": {
                    "SourceRef": {
                      "Entity": "TABLE_NAME"
                    }
                  },
                  "Property": "MEASURE_NAME"
                }
              },
              "queryRef": "TABLE_NAME.MEASURE_NAME",
              "nativeQueryRef": "MEASURE_NAME"
            }
          ]
        }
      }
    },
    "visualContainerObjects": {
      "background": [
        {
          "properties": {
            "show": {
              "expr": { "Literal": { "Value": "true" } }
            },
            "transparency": {
              "expr": { "Literal": { "Value": "100D" } }
            }
          }
        }
      ]
    },
    "drillFilterOtherVisuals": true
  }
}
```

Key differences from built-in card visual:
- `visualType`: `htmlContent443BE3AD55E043BF878BED274D3A6855` (unique ID for the public visual)
- Query role: `content` (not `Values` like cards)
- Has `nativeQueryRef` in projections
- Background transparency: `100D` (fully transparent — the HTML provides its own background)
- Has `drillFilterOtherVisuals: true`

---

## 12. Custom Visual Registration in report.json

Custom visuals (from AppSource marketplace) are registered in `report.json`:

```json
{
  "publicCustomVisuals": [
    "htmlContent443BE3AD55E043BF878BED274D3A6855"
  ]
}
```

> [!IMPORTANT]
> To programmatically add an HTML Content visual, you must ALSO add the visual type ID to the `publicCustomVisuals` array in `report.json`. Without this, PBI won't recognize the visual type.

The visual type ID format: `htmlContent` + `443BE3AD55E043BF878BED274D3A6855` (AppSource GUID).

### Resource Packages (Images, Themes) in report.json

```json
{
  "resourcePackages": [
    {
      "name": "SharedResources",
      "type": "SharedResources",
      "items": [{
        "name": "CY24SU06",
        "path": "BaseThemes/CY24SU06.json",
        "type": "BaseTheme"
      }]
    },
    {
      "name": "RegisteredResources",
      "type": "RegisteredResources",
      "items": [
        { "name": "MyImage123456789.png", "path": "MyImage123456789.png", "type": "Image" },
        { "name": "MyTheme5193027847108278.json", "path": "MyTheme5193027847108278.json", "type": "Image" }
      ]
    }
  ]
}
```

- `SharedResources`: Base themes stored in `StaticResources/SharedResources/BaseThemes/`
- `RegisteredResources`: Custom images + themes stored in `StaticResources/RegisteredResources/`
- Image files referenced via `ResourcePackageItem` in image visual `objects.general.imageUrl`

---

## 13. PBI Desktop Auto-Normalization Patterns

When Power BI Desktop opens and saves a PBIP project, it normalizes several things:

### z-index (`z` property)
- PBI uses **increments of ~1000** for z-ordering
- First visual: `z: 0`, second: `z: 1000`, third: `z: 2000`, new: `z: 2001`
- Our original `z: 1000` for all 3 cards was renumbered to 0, 1000, 2000

### Tab Order (`tabOrder` property)
- Also uses **increments of 1000**: 0, 1000, 2000
- Our original `tabOrder: 0, 1, 2` was renumbered to 0, 1000, 2000

### filterConfig
- PBI **auto-generates** a `filterConfig` block for each visual
- Contains a unique `name` (hex ID) and the bound field reference
- Filter `type` is typically `"Advanced"`

### Summary of auto-generated properties
| Property | Behavior |
|----------|----------|
| `z` | Renumbered with 1000 increments |
| `tabOrder` | Renumbered with 1000 increments |
| `filterConfig` | Auto-added with unique name |
| `drillFilterOtherVisuals` | Set to `true` by default |
| `howCreated` | Set to `"InsertVisualButton"` on new visuals |
| `pageBinding` | Auto-added to pages with name/type/parameters |
| Column `isNameInferred` | Added to calculated table columns |
| Column `sourceColumn` | Wrapped in brackets: `[ColumnName]` |
| Column `annotation SummarizationSetBy` | Set to `Automatic` |
| Column `changedProperty` | Tracks manual changes (DataType, IsHidden, etc.) |
| TMDL `expression` | Changed to `source` in calculated partitions |
| JSON indentation | Normalized to 2-space indent |

---

## 14. Using SVG Icon Libraries (Lucide / Heroicons / Feather)

> [!TIP]
> Inline SVG icons are the **best replacement for emojis** in HTML Content visuals. They're crisp, scalable, color-customizable, and work in both certified and uncertified versions.

### Why SVG icons > Emojis
- ✅ Consistent rendering across PBI Desktop and Service
- ✅ Color-customizable via `stroke` attribute
- ✅ Scales perfectly at any size
- ✅ Works in certified HTML Content (Lite)
- ❌ Emojis can look different across OS/browsers

### Template: Inline SVG Icon
```html
<svg width='16' height='16' viewBox='0 0 24 24'
  fill='none' stroke='#A78BFA' stroke-width='2'
  stroke-linecap='round' stroke-linejoin='round'>
  <!-- path data here -->
</svg>
```

### Icon Reference (Lucide icons used in our cards)

| Icon | Name | SVG Path | Used In |
|------|------|----------|---------|
| 💲 | DollarSign | `<line x1='12' y1='1' x2='12' y2='23'/><path d='M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'/>` | HtmlGlassCard |
| 👥 | Users | `<path d='M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2'/><circle cx='9' cy='7' r='4'/><path d='M22 21v-2a4 4 0 0 0-3-3.87'/><path d='M16 3.13a4 4 0 0 1 0 7.75'/>` | HtmlNeonCard |
| 🎯 | Target | `<circle cx='12' cy='12' r='10'/><circle cx='12' cy='12' r='6'/><circle cx='12' cy='12' r='2'/>` | HtmlProgressCard |
| 📊 | BarChart2 | `<line x1='18' y1='20' x2='18' y2='10'/><line x1='12' y1='20' x2='12' y2='4'/><line x1='6' y1='20' x2='6' y2='14'/>` | HtmlSparkCard |
| 💓 | Activity | `<polyline points='22 12 18 12 15 21 9 3 6 12 2 12'/>` | HtmlStatusCard |
| ✓ | Check | `<polyline points='20 6 9 17 4 12'/>` | HtmlGaugeCard |

### DAX Pattern: Icon + Label
```dax
"<div style='display:flex; align-items:center; gap:8px;'>" &
"<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='#A78BFA' stroke-width='2' stroke-linecap='round'>" &
"<line x1='12' y1='1' x2='12' y2='23'/>" &
"<path d='M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6'/>" &
"</svg>" &
"<span style='font-size:11px; color:rgba(255,255,255,0.5);'>Receita</span></div>"
```

### Component Libraries in HTML Content Visual

| Library | Works? | Notes |
|---------|--------|-------|
| **Lucide SVG** | ✅ | Inline paths, no CDN needed |
| **Animate.css** | ✅ | Paste `@keyframes` in `<style>` block |
| **Google Fonts** | ⚠️ | `@import url(...)` — uncertified only |
| **Bootstrap CSS** | ⚠️ | Inline the CSS — no JS components |
| React/Vue/Angular | ❌ | Require JavaScript (blocked in sandbox) |
| D3.js / Chart.js | ❌ | Require JavaScript |

---

## 15. Responsive / Dynamic Sizing in HTML Content Visuals

> [!CAUTION]
> **MANDATORY RULE**: ALL HTML Content visuals must ALWAYS use responsive sizing. Never use fixed `px` values alone. Always wrap with `min()`, `clamp()`, or use viewport units.

> [!IMPORTANT]
> The HTML Content visual renders inside its own **iframe**. This means `100vh` = full visual height and `100vw` = full visual width. Use these to make HTML fill any container size.

### The Responsive Root Container (Required for EVERY card)
```css
/* ALWAYS start every card with this on the root div */
width: 100%;
height: 100vh;
box-sizing: border-box;
display: flex;
flex-direction: column;
justify-content: center;    /* or align-items:center for horizontal */
padding: min(24px, 4vh) min(24px, 4vw);
```

### CSS Functions Reference

| Function | Syntax | Best For |
|----------|--------|----------|
| `min()` | `min(28px, 6vw)` | Cap max size — shrinks on small containers |
| `max()` | `max(12px, 2vw)` | Cap min size — grows on large containers |
| `clamp()` | `clamp(10px, 3vw, 20px)` | Both min and max bounds |
| `100vh` | `height: 100vh` | Fill full container height |
| `100vw` | `width: 100vw` | Fill full container width |

### DAX Example: Responsive Gauge Card
```dax
"<div style='...height:100vh; display:flex; flex-direction:column; justify-content:center;'>" &
"<div style='width:min(120px,30vw,30vh); height:min(120px,30vw,30vh);'>" &
"<svg width='100%' height='100%' viewBox='0 0 120 120'>...</svg>" &
"</div></div>"
```

**Key**: SVG with `width='100%' height='100%'` + `viewBox` scales perfectly at any size.

---

## 16. HTML-to-DAX Conversion Patterns

### Conversion Checklist
1. ✅ Use **single quotes** for all HTML attributes (`style='...'` not `style="..."`)
2. ✅ Each line → a DAX string concatenated with `&`
3. ✅ Replace hardcoded values with `FORMAT([Measure], "pattern")`
4. ✅ CSS classes → **inline styles** (or use `<style>` block for animations)
5. ✅ `::before`/`::after` → nested `<div>` elements
6. ✅ `:hover` effects → **don't work** in PBI (no JS for interactions)
7. ✅ Wrap measure in `VAR`/`RETURN` for readability

### DAX String Escaping Rules

| Character | In DAX String | Notes |
|-----------|--------------|-------|
| Double quote `"` | `""` | Doubled inside DAX strings |
| Single quote `'` | `'` | Works normally — **use for HTML** |
| Ampersand `&` | `&` (in HTML) / `&` (DAX concat) | Context matters |
| Line break | Not needed | HTML ignores whitespace |

### Template: Complete DAX HTML Measure
```tmdl
	measure HtmlMyCard =
			VAR _valor = [MyMeasure]
			VAR _meta = 1000
			VAR _percent = DIVIDE(_valor, _meta, 0) * 100
			RETURN
			"<div style='font-family:Segoe UI,sans-serif; background:#12121F; border-radius:16px; padding:24px; color:white; width:100%; height:100vh; box-sizing:border-box; display:flex; flex-direction:column; justify-content:center;'>" &
			"<p style='margin:0 0 8px; font-size:12px; color:#6B7280;'>Label</p>" &
			"<div style='font-size:28px; font-weight:700;'>" & FORMAT(_valor, "#,##0") & "</div>" &
			"<div style='background:rgba(255,255,255,0.06); border-radius:6px; height:8px; margin-top:12px;'>" &
			"<div style='height:100%; border-radius:6px; background:linear-gradient(90deg,#8B5CF6,#06B6D4); width:" & FORMAT(_percent, "0") & "%;'></div></div>" &
			"</div>"
		lineageTag: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
```

### Common FORMAT Patterns
| Format | Example | Output |
|--------|---------|--------|
| `"#,##0"` | `FORMAT(1250000, "#,##0")` | `1.250.000` |
| `"0.0"` | `FORMAT(94.5, "0.0")` | `94,5` |
| `"0"` | `FORMAT(85.7, "0")` | `86` |
| `"R$ #,##0"` | `FORMAT(1250000, "R$ #,##0")` | `R$ 1.250.000` |
| `"0.0%"` | `FORMAT(0.945, "0.0%")` | `94,5%` |

---

## 17. Card Design Catalog (7 Proven Designs)

All designs tested and working in Power BI HTML Content visual:

### 1. Glassmorphism Card
- **Look**: Frosted glass, radial gradient glow, gradient text
- **CSS**: `backdrop-filter:blur(20px)`, `rgba` backgrounds, `-webkit-background-clip:text`
- **Measure**: `HtmlGlassCard`

### 2. Neon Glow Card
- **Look**: Bottom gradient bar, icon circle, percentage badge
- **CSS**: `linear-gradient` bottom bar via `position:absolute; bottom:0`, rounded icon with `box-shadow` glow
- **Measure**: `HtmlNeonCard`

### 3. Progress Bar Card
- **Look**: Horizontal progress bar, percentage, remaining info
- **CSS**: Nested `<div>` with `width:N%`, `linear-gradient` fill, `flexbox` meta row
- **Measure**: `HtmlProgressCard`

### 4. Sparkline Card
- **Look**: Mini bar chart, trend indicator
- **CSS**: `flexbox` with `align-items:flex-end`, each bar `height:N%`, `linear-gradient(to top, ...)`
- **Measure**: `HtmlSparkCard`

### 5. Status Grid Card
- **Look**: Pulsing dot, 2×2 metrics grid
- **CSS**: `@keyframes` animation, `display:grid; grid-template-columns:1fr 1fr`
- **Measure**: `HtmlStatusCard`
- **Note**: Uses `<style>` block for `@keyframes` — works in uncertified version

### 6. SVG Gauge Ring
- **Look**: Circular progress ring, percentage center
- **CSS/SVG**: `stroke-dasharray` + `stroke-dashoffset` for arc, `linearGradient` for color
- **Math**: `dashoffset = 339.292 × (1 - percent/100)` where `339.292 = 2πr` (r=54)
- **Measure**: `HtmlGaugeCard`

### 7. Original Gradient Card
- **Look**: Purple gradient background, progress bar, meta text
- **CSS**: `linear-gradient(135deg, ...)`, `box-shadow` for depth
- **Measure**: `HtmlCardReceita`

### Design System — Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Page Background | Very dark | `#0F0F1A` or `#1B1B2F` |
| Card Background | Dark blue | `#12121F` or `#162447` |
| Card Border | Subtle | `#1E1E3A` or `rgba(255,255,255,0.04)` |
| Primary Text | White | `#FFFFFF` |
| Secondary Text | Muted | `#9CA3AF` or `#6B7280` |
| Accent Purple | Violet | `#8B5CF6` or `#6366F1` |
| Accent Cyan | Teal | `#06B6D4` or `#00D9FF` |
| Accent Green | Success | `#4ADE80` |
| Accent Red | Error | `#F87171` |
| Accent Gold | Warning | `#FFD700` |
| Accent Pink | Highlight | `#EC4899` or `#E43F5A` |

---

## 18. Semantic Model Patterns (TMDL)

### Complete Table Structure
```tmdl
table TableName
	lineageTag: <guid>

	// --- Measures ---
	measure SimpleMeasure = SUM(TableName[Column])
		formatString: #,##0
		lineageTag: <guid>

	measure FilteredMeasure = CALCULATE(SUM(TableName[Value]), TableName[Category] = "X")
		formatString: R$ #,##0
		lineageTag: <guid>

	// Multi-line DAX with backtick fencing (preferred by PBI Desktop)
	measure ComplexMeasure = ```
		VAR _x = [SimpleMeasure]
		VAR _total = CALCULATE([SimpleMeasure], ALL(TableName))
		RETURN
		    DIVIDE(_x, _total, 0)
		```
		formatString: 0.00%;-0.00%;0.00%
		lineageTag: <guid>

	// Multi-line DAX with indentation-only
	measure HtmlMeasure =
			VAR _x = [SimpleMeasure]
			RETURN
			"<div>" & FORMAT(_x, "#,##0") & "</div>"
		lineageTag: <guid>

	// --- Calculated Columns ---
	column PercentColumn = TableName[Realizado] / TableName[Previsto]
		formatString: 0.00%;-0.00%;0.00%
		lineageTag: <guid>
		summarizeBy: sum
		annotation SummarizationSetBy = Automatic

	column DateKey = DATE([Ano], 1, 1)
		formatString: General Date
		lineageTag: <guid>
		summarizeBy: none
		annotation SummarizationSetBy = Automatic

	// --- Columns (from data source or calculated table) ---
	column ColumnName
		dataType: string
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: Column Name
		annotation SummarizationSetBy = Automatic

	column DateColumn
		dataType: dateTime
		formatString: Long Date
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: Date Column
		variation Variation
			isDefault
			relationship: <relationship-guid>
			defaultHierarchy: LocalDateTable_<guid>.'Hierarquia de datas'
		annotation SummarizationSetBy = Automatic
		annotation UnderlyingDateTimeDataType = Date

	column SortedColumn
		lineageTag: <guid>
		summarizeBy: none
		sourceColumn: Month Name
		sortByColumn: MonthNumber
		annotation SummarizationSetBy = Automatic

	// --- Columns (auto-generated by PBI for calculated tables) ---
	column InferredColumn
		lineageTag: <guid>
		isNameInferred
		sourceColumn: [InferredColumn]

	// --- Partition: Calculated (DAX) ---
	partition TableName = calculated
		mode: import
		source =
				DATATABLE(
					"Column1", STRING,
					"Column2", DOUBLE,
					{
						{"Row1", 100},
						{"Row2", 200}
					}
				)

	// --- Partition: M (Power Query - real data sources) ---
	// partition TableName = m
	//     mode: import
	//     source =
	//         let
	//             Fonte = SharePoint.Tables("https://site.sharepoint.com/sites/MySite"),
	//             Table = Fonte{[Id="guid"]}[Items]
	//         in
	//             Table

	annotation PBI_NavigationStepName = Navegação
	annotation PBI_ResultType = Table
```

### TMDL Indentation Rules (Critical!)

| Element | Indentation |
|---------|-------------|
| `table` keyword | 0 tabs |
| Properties (`lineageTag`) | 1 tab |
| `measure`, `column`, `partition` | 1 tab |
| Measure properties (`formatString`, `lineageTag`) | 2 tabs |
| Multi-line DAX expressions | 3 tabs |
| Partition `source =` expression | 4 tabs |

> [!CAUTION]
> If a multi-line DAX expression shares the same indentation as `lineageTag`, PBI parses `lineageTag` as DAX code and throws a syntax error!

### DAX Patterns for Measures

```dax
// Simple aggregation
SUM(Table[Column])

// Filtered aggregation
CALCULATE(SUM(Table[Value]), Table[Category] = "X")

// Percentage calculation
DIVIDE([Measure1], [Measure2], 0) * 100

// Difference from target
VAR _valor = [ActualMeasure]
VAR _meta = CALCULATE(SUM(Table[Meta]), Table[Cat] = "X")
RETURN DIVIDE(_valor - _meta, _meta, 0) * 100

// SVG gauge math (circle circumference)
VAR _percent = [MyPercent]
VAR _circumference = 339.292   // 2 × π × radius (r=54)
VAR _dashoffset = _circumference * (1 - _percent / 100)
```

### model.tmdl Reference
```tmdl
model Model
	culture: pt-BR
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: pt-BR
	dataAccessOptions
		legacyRedirects
		returnErrorValuesAsNull

annotation PBI_QueryOrder = ["Table1","Table2","Table3"]
annotation __PBI_TimeIntelligenceEnabled = 1
annotation PBI_ProTooling = ["DevMode"]

ref table TableName
ref table 'Table With Spaces'

ref cultureInfo pt-BR
```

> [!NOTE]
> Each table gets its own `.tmdl` file in `definition/tables/`. The `model.tmdl` only contains `ref table` references. Table names with spaces must be wrapped in single quotes. `PBI_QueryOrder` controls order in Power Query Editor.

---

## 19. Quick Reference — Files to Edit for Common Tasks

| Task | Files to Edit |
|------|--------------|
| Add new page | `pages/<id>/page.json` + `pages/pages.json` |
| Add built-in visual | `pages/<page>/visuals/<id>/visual.json` |
| Add HTML Content visual | Same as above + `report.json` (`publicCustomVisuals`) |
| Add image visual | visual.json + `report.json` (`resourcePackages`) + image file in `StaticResources/RegisteredResources/` |
| Add slicer | visual.json (+ `syncGroup` for cross-page sync) |
| Add visual group | visual.json with `visualGroup` + set `parentGroupName` on child visuals |
| Add DAX measure | `tables/<table>.tmdl` |
| Add calculated column | `tables/<table>.tmdl` (inline DAX in column definition) |
| Add new table | `tables/<name>.tmdl` + `model.tmdl` (`ref table`) |
| Add relationship | `relationships.tmdl` |
| Change page background | `pages/<id>/page.json` → `objects.background` |
| Change active page | `pages/pages.json` → `activePageName` |
| Change theme | `report.json` → `themeCollection` |
| Add page navigation | visual.json → `visualContainerObjects.visualLink` |
| Add reference line | visual.json → `objects.y1AxisReferenceLine` |

---

## 20. CSS Animations in HTML Content Visual

> [!TIP]
> CSS animations work perfectly in the HTML Content visual! Use a `<style>` block at the top of the HTML string for `@keyframes` and class definitions, then reference classes in the HTML body.

### Animation Techniques That Work

| Technique | @keyframes | Best For |
|-----------|-----------|----------|
| **Rotating gradient border** | `borderRotate` | Eye-catching card borders |
| **Glow pulse** | `glowPulse` | Highlighting key numbers |
| **Fill bar** | `fillBar` | Progress bars that animate on load |
| **Fade-in slide up** | `fadeSlideUp` | Staggered element reveals |
| **Breathing background** | `breathe` | Subtle "alive" card backgrounds |
| **Shimmer** | `shimmer` | Loading skeleton effects |
| **SVG ring draw** | `drawRing` | Animated circular gauges |
| **Pulse dot** | `pulse` | Status indicators |

### Reusable @keyframes Library

```css
/* 1. Rotating gradient border — shifts gradient position */
@keyframes borderRotate {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 2. Glow pulse — text shadow intensity */
@keyframes glowPulse {
  0%, 100% { text-shadow: 0 0 20px rgba(99,102,241,0.3); }
  50% { text-shadow: 0 0 40px rgba(99,102,241,0.8), 0 0 60px rgba(99,102,241,0.4); }
}

/* 3. Fill bar — width from 0% to target */
@keyframes fillBar { from { width: 0%; } }

/* 4. Fade-in slide up — opacity + translateY */
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 5. Breathing background — gradient position shift */
@keyframes breathe {
  0%, 100% { background-position: 0% 50%; opacity: 0.8; }
  50% { background-position: 100% 50%; opacity: 1; }
}

/* 6. Shimmer — loading skeleton effect */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* 7. Pulse dot — scale + opacity for status indicators */
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.8); }
}

/* 8. SVG ring draw — stroke-dashoffset from full to target */
@keyframes drawRing { from { stroke-dashoffset: 339.292; } }
```

### DAX Pattern: Animated Card with `<style>` Block

```tmdl
measure HtmlAnimatedCard =
    VAR _val = [MyMeasure]
    RETURN
    "<style>" &
    "@keyframes fb{from{width:0%}}" &
    "@keyframes gp{0%,100%{text-shadow:0 0 20px rgba(99,102,241,0.3)}50%{text-shadow:0 0 40px rgba(99,102,241,0.8)}}" &
    ".ab{animation:fb 1.5s ease-out forwards}" &
    ".gn{animation:gp 2s ease-in-out infinite}" &
    "</style>" &
    "<div style='...'>" &
    "<div class='gn'>" & FORMAT(_val, "#,##0") & "</div>" &
    "<div class='ab' style='width:" & FORMAT(_val, "0") & "%;...'></div>" &
    "</div>"
```

### Staggered Animations with `animation-delay`

Apply different delays to create sequential reveal effects:
```html
<div class='anim-row' style='animation-delay:0.2s;'>Row 1</div>
<div class='anim-row' style='animation-delay:0.4s;'>Row 2</div>
<div class='anim-row' style='animation-delay:0.6s;'>Row 3</div>
```

### Rotating Gradient Border Pattern

The most eye-catching effect — a border that shifts colors continuously:
```html
<!-- Outer wrapper: the gradient border -->
<div style='padding:2px; border-radius:20px;
  background:linear-gradient(270deg,#6366F1,#06B6D4,#EC4899,#8B5CF6);
  background-size:300% 300%;
  animation:borderRotate 4s ease infinite;'>
  <!-- Inner card: solid dark background -->
  <div style='background:#12121F; border-radius:18px; padding:24px;'>
    Content here
  </div>
</div>
```

> [!WARNING]
> **Important notes about animations in PBI:**
> - Animations replay every time the visual re-renders (slicer change, filter, etc.)
> - `<style>` blocks with `@keyframes` require the **uncertified** HTML Content visual (not Lite)
> - Use `animation-fill-mode: forwards` for one-shot animations (bars stay at target width)
> - Use `infinite` for continuous effects (glow, breathing, rotating border)
> - Keep animation names short in DAX to reduce string length

---

## 21. Deneb Visual — Interactive Custom Visuals (Research)

> [!IMPORTANT]
> **Deneb** is a free, open-source (MIT) custom visual that lets you create fully interactive data visualizations using **Vega** or **Vega-Lite** JSON specifications. It supports **cross-filtering**, **tooltips**, and **selections** — unlike the HTML Content visual.

### Key Differences: HTML Content vs Deneb

| Feature | HTML Content | Deneb |
|---------|-------------|-------|
| **Rendering** | HTML/CSS in iframe | Vega/Vega-Lite (SVG/Canvas) |
| **Cross-filtering** | ❌ None | ✅ Full support |
| **Tooltips** | ❌ CSS only | ✅ PBI native tooltips |
| **Click selection** | ❌ No JS | ✅ Via `__selected__` field |
| **Animations** | ✅ CSS @keyframes | ⚠️ Limited (transitions only) |
| **Custom layout** | ✅ Full HTML/CSS | ⚠️ Chart-focused |
| **Spec language** | HTML string in DAX | Vega-Lite JSON |
| **AI agent friendly** | ✅ DAX string gen | ✅ Pure JSON gen |
| **Free** | ✅ Yes | ✅ Yes (MIT) |
| **AppSource** | ✅ Yes | ✅ Yes |

### Cross-Filtering Architecture

1. Enable "Expose cross-filtering values for dataset rows" in visual settings
2. Deneb adds a `__selected__` field to each data row
3. Use `__selected__` to encode opacity/color (selected vs dimmed)
4. Clicks on marks automatically filter other visuals on the page

```json
{
  "encoding": {
    "opacity": {
      "condition": {"test": {"field": "__selected__", "equal": "on"}, "value": 1},
      "value": 0.3
    }
  }
}
```

### Vega-Lite Spec Format (What AI Generates)

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {"name": "dataset"},
  "mark": {"type": "bar", "cornerRadiusTopLeft": 4, "cornerRadiusTopRight": 4},
  "encoding": {
    "x": {"field": "Categoria", "type": "nominal"},
    "y": {"field": "Valor", "type": "quantitative"},
    "color": {"field": "Categoria", "type": "nominal"},
    "opacity": {
      "condition": {"test": {"field": "__selected__", "equal": "on"}, "value": 1},
      "value": 0.3
    },
    "tooltip": [
      {"field": "Categoria", "type": "nominal"},
      {"field": "Valor", "type": "quantitative", "format": ",.0f"}
    ]
  }
}
```

### PBIP Integration (Confirmed from actual visual.json)

> [!IMPORTANT]
> We extracted and validated the exact Deneb PBIP structure. The Vega-Lite spec is stored as an escaped JSON string inside `objects.vega[].properties.jsonSpec`.

#### Query Role Name
- Deneb uses a **single role** called `dataset` (not `Values`/`Category` like built-in visuals)
- All fields (columns + measures) go into the same `dataset` projections array

#### Spec Storage
```
objects.vega[0].properties.jsonSpec.expr.Literal.Value = "'{ escaped JSON string }'"
```
- The JSON spec is **escaped** (quotes become `\"`, newlines become `\n`)
- The entire string is wrapped in **single quotes**: `"'{ ... }'"` (same pattern as colors!)

#### Full visual.json Template (Reusable)
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.6.0/schema.json",
  "name": "YOUR_UNIQUE_ID",
  "position": { "x": 30, "y": 480, "z": 7000, "height": 220, "width": 390, "tabOrder": 7000 },
  "visual": {
    "visualType": "deneb7E15AEF80B9E4D4F8E12924291ECE89A",
    "query": {
      "queryState": {
        "dataset": {
          "projections": [
            {
              "field": { "Column": { "Expression": { "SourceRef": { "Entity": "TABLE" } }, "Property": "COLUMN_NAME" } },
              "queryRef": "TABLE.COLUMN_NAME", "nativeQueryRef": "COLUMN_NAME"
            },
            {
              "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "TABLE" } }, "Property": "MEASURE_NAME" } },
              "queryRef": "TABLE.MEASURE_NAME", "nativeQueryRef": "MEASURE_NAME"
            }
          ]
        }
      }
    },
    "objects": {
      "stateManagement": [{ "properties": {
        "viewportHeight": { "expr": { "Literal": { "Value": "220D" } } },
        "viewportWidth": { "expr": { "Literal": { "Value": "390D" } } }
      }}],
      "editor": [{ "properties": {
        "previewScrollbars": { "expr": { "Literal": { "Value": "false" } } },
        "theme": { "expr": { "Literal": { "Value": "'dark'" } } }
      }}],
      "vega": [{ "properties": {
        "provider": { "expr": { "Literal": { "Value": "'vegaLite'" } } },
        "jsonSpec": { "expr": { "Literal": { "Value": "'ESCAPED_VEGALITE_JSON'" } } },
        "jsonConfig": { "expr": { "Literal": { "Value": "'{}'" } } },
        "isNewDialogOpen": { "expr": { "Literal": { "Value": "false" } } },
        "enableTooltips": { "expr": { "Literal": { "Value": "true" } } },
        "enableContextMenu": { "expr": { "Literal": { "Value": "true" } } },
        "enableHighlight": { "expr": { "Literal": { "Value": "true" } } },
        "enableSelection": { "expr": { "Literal": { "Value": "true" } } },
        "selectionMaxDataPoints": { "expr": { "Literal": { "Value": "50D" } } },
        "selectionMode": { "expr": { "Literal": { "Value": "'simple'" } } },
        "version": { "expr": { "Literal": { "Value": "'6.4.1'" } } }
      }}]
    },
    "visualContainerObjects": {
      "padding": [{ "properties": {
        "top": { "expr": { "Literal": { "Value": "0D" } } },
        "left": { "expr": { "Literal": { "Value": "0D" } } },
        "bottom": { "expr": { "Literal": { "Value": "0D" } } },
        "right": { "expr": { "Literal": { "Value": "0D" } } }
      }}]
    },
    "drillFilterOtherVisuals": true
  }
}
```

#### Interactivity Flags (all in `objects.vega[].properties`)

| Property | Value | Effect |
|----------|-------|--------|
| `enableTooltips` | `true` | Native PBI tooltips on hover |
| `enableContextMenu` | `true` | Right-click context menu |
| `enableHighlight` | `true` | Cross-highlight from other visuals |
| `enableSelection` | `true` | Click-to-select (cross-filtering) |
| `selectionMaxDataPoints` | `50D` | Max selectable points (1-250) |
| `selectionMode` | `'simple'` | Simple or advanced selection |

#### Python Script: Escape Vega-Lite Spec for PBIP
```python
import json

def escape_spec_for_pbip(spec_dict):
    """Convert a Vega-Lite dict to the escaped string format PBIP expects."""
    json_str = json.dumps(spec_dict, indent=2)
    # Escape backslashes first, then quotes
    escaped = json_str.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
    return f"'{escaped}'"
```

*Last updated: 2026-03-06*

---

## 22. Deneb Spec Escaping — The #1 Gotcha

> [!CAUTION]
> **Never use `\\n` in Deneb jsonSpec strings!** They are treated as literal backslash-n characters, NOT whitespace. This causes `JSON parse error at position 1` in the Deneb editor.

### ❌ Wrong — `\\n` newlines (causes parse error)
```json
"Value": "'{\\n  \\\"$schema\\\": \\\"https://vega.github.io/schema/vega-lite/v5.json\\\",\\n  \\\"data\\\": ...}'"
```

### ✅ Correct — compact single-line JSON (no newlines)
```json
"Value": "'{\"$schema\": \"https://vega.github.io/schema/vega-lite/v5.json\", \"data\": {\"name\": \"dataset\"}, \"mark\": \"bar\", ...}'"
```

### Escaping Rules for Deneb jsonSpec in visual.json

| Character | In the file | What it becomes | Notes |
|-----------|------------|-----------------|-------|
| `"` (inner JSON quote) | `\"` | `"` | Standard escape |
| `'` (in expressions) | `\\u0027` | `'` | For filter expressions like `datum.Category === 'Device'` |
| Newlines | **DON'T USE** | — | Causes parse errors |
| The outer wrapper | `"'{...}'"` | `'{...}'` | Single-quoted string value |

### Python Script (Updated — NO newlines!)
```python
import json

def escape_spec_for_pbip(spec_dict):
    """Convert a Vega-Lite dict to the escaped string format PBIP expects."""
    # Compact single-line JSON — NO indent, NO newlines
    json_str = json.dumps(spec_dict, separators=(',', ': '))
    # Escape quotes for embedding in JSON Value string
    escaped = json_str.replace('"', '\\"')
    # Replace single quotes in expressions with unicode escape
    escaped = escaped.replace("'", "\\u0027")
    return f"'{escaped}'"
```

### First-Time Initialization Required

> [!WARNING]
> Deneb visuals created from JSON **require manual initialization**:
> 1. Open PBI Desktop, click on the blank Deneb visual
> 2. Click "..." → "Edit" to open the Deneb editor
> 3. The spec should be loaded — click **"Create"** or **"Apply"**
> 4. After this one-time step, the visual renders correctly going forward

This is NOT needed for HTML Content visuals — they render immediately.

---

## 23. Creating Pages from JSON — Complete Workflow

### Step-by-step: Add a new page via IDE

1. **Create page folder**: `pages/<page_name>/page.json`
2. **Create visuals folder**: `pages/<page_name>/visuals/`
3. **Create each visual**: `pages/<page_name>/visuals/<visual_id>/visual.json`
4. **Register the page**: Add `<page_name>` to `pages/pages.json` → `pageOrder` array
5. **Set active (optional)**: Set `activePageName` in `pages/pages.json`

### Light Theme Color Palette (Proven)

| Role | Color | Hex |
|------|-------|-----|
| Page Background | Soft gray | `#F7F9FB` |
| Card Background | White | `#FFFFFF` |
| Card Border | Very light gray | `#F1F5F9` |
| Primary Text | Near black | `#1C1C1C` |
| Muted Text | Slate gray | `#64748B` |
| Accent Blue | Bright blue | `#3B82F6` |
| Dark Card BG | Near black | `#1F2937` |
| Accent Purple | Violet | `#A855F7` |
| Accent Green | Emerald | `#10B981` |
| Axis/Grid Lines | Light slate | `#E2E8F0` |

### Light Theme KPI Card Pattern (DAX)

```tmdl
	measure LightKpiViews =
			VAR _value = SUM(MonthlyMetrics[ThisYear])
			VAR _change = DIVIDE(_value - SUM(MonthlyMetrics[LastYear]), SUM(MonthlyMetrics[LastYear]), 0) * 100
			RETURN
			"<div style='font-family:Segoe UI,sans-serif; background:#3B82F6; border-radius:16px; padding:min(16px,3vh) min(20px,3vw); color:white; width:100%; height:100vh; box-sizing:border-box; display:flex; flex-direction:column; justify-content:space-between;'>" &
			"<div style='display:flex; justify-content:space-between; align-items:center;'>" &
			"<span style='font-size:clamp(10px,2.5vw,13px); opacity:0.85;'>Views</span>" &
			"<svg width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='rgba(255,255,255,0.7)' stroke-width='2'><polyline points='22 12 18 12 15 21 9 3 6 12 2 12'/></svg>" &
			"</div>" &
			"<div style='font-size:clamp(20px,5vw,32px); font-weight:700;'>" & FORMAT(_value, "#,##0") & "</div>" &
			"<div style='font-size:clamp(9px,2vw,11px); opacity:0.75; text-align:right;'>+" & FORMAT(_change, "0.00") & "%</div>" &
			"</div>"
		lineageTag: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
```

---

## 24. Visual Container Objects — Extended Patterns

### Border with Rounded Corners (from PBI Desktop)

When you add borders in PBI Desktop, it generates this structure:

```json
"border": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } },
    "color": {
      "solid": {
        "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } }
      }
    },
    "radius": { "expr": { "Literal": { "Value": "20D" } } },
    "width": { "expr": { "Literal": { "Value": "2D" } } }
  }
}]
```

### Border with ThemeDataColor (PBI auto-generates this)
```json
"color": {
  "solid": {
    "color": {
      "expr": {
        "ThemeDataColor": { "ColorId": 0, "Percent": 0 }
      }
    }
  }
}
```

### Visual Tooltip Transparency
```json
"visualTooltip": [{
  "properties": {
    "transparency": { "expr": { "Literal": { "Value": "100D" } } }
  }
}]
```

### Background Show = false (hides card background entirely)
```json
"background": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "false" } } },
    "transparency": { "expr": { "Literal": { "Value": "100D" } } }
  }
}]
```

### Drop Shadow
```json
"dropShadow": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "true" } } }
  }
}]
```

> [!TIP]
> PBI reformats all JSON to **2-space indent** on save. Our 4-space files get normalized automatically.

---

## 25. Deneb vs HTML+CSS vs Standard Visuals — Decision Guide

### When to use each tool

| Use Case | Best Tool | Why |
|----------|-----------|-----|
| KPI cards, headers, info panels | **HTML+CSS** | Beautiful styling, CSS animations, easy to edit in DAX |
| Filter drawers, navigation panels | **HTML+CSS** + **Bookmarks** | Full CSS control + toggle via bookmark actions |
| Standard charts (bar, line, pie) | **Standard PBI visuals** | Native cross-filtering, zero overhead |
| Custom charts (Sankey, org tree, beeswarm) | **Deneb (Vega-Lite)** | Impossible with standard visuals |
| Animated data viz (bar chart race) | **Deneb (Vega)** | Only option, but very high complexity |
| Slicers and filters | **Standard PBI slicer** | Native cross-filtering, easy to style |

### Avoid These Anti-Patterns

- ❌ Using Deneb for simple bar/line charts (standard visuals do this better)
- ❌ Using HTML+CSS for data-driven charts (DAX string concat for chart paths is unmaintainable)
- ❌ Using `\\n` in Deneb jsonSpec values (causes parse errors)
- ❌ Using full Vega when Vega-Lite is sufficient (3-5x more code)
- ❌ Putting many Deneb visuals on one page (cold-start performance hit per visual)

### Deneb Animation: Vega vs Vega-Lite

| Feature | Vega-Lite | Vega |
|---------|-----------|------|
| Static charts | ✅ Simple | ✅ Verbose |
| Transitions on data change | ❌ None | ✅ Timer events |
| Bar chart race | ❌ Impossible | ✅ Yes (complex) |
| Particle effects | ❌ Impossible | ✅ Yes (complex) |
| Code complexity | Low (~30 lines) | High (100-500 lines) |
| IDE editability | Moderate | Difficult |

### Community Resources

| Resource | URL | Content |
|----------|-----|---------|
| Deneb Showcase (PBI-David) | github.com/PBI-David/Deneb-Showcase | 25+ examples with animated visuals |
| Deneb Official Docs | deneb-viz.github.io | Full documentation |
| Kerry Kolosko blog | kerrykolosko.com | PBI visualization tutorials |
| Vega-Lite Examples | vega.github.io/vega-lite/examples | Complete example gallery |

### Key Limitation: Deneb Sandbox

- Each Deneb visual runs in its **own isolated sandbox** (iframe)
- Multiple Deneb visuals = **cold-start delay** per visual on page load
- **10K row limit** by default (configurable but impacts performance)
- **No external URLs** — can't load fonts, images, or external data
- Certified by Microsoft — works in PBI Service, PDF export, email

---

## 26. Dashboard Design Reference Library (from Screenshots)

> [!TIP]
> These patterns were extracted from real dashboard designs. Use them as a reference when creating new Power BI pages.

### Design A — Purple Monochromatic (CRM/Business)

**Color Palette:**

| Role | Hex |
|------|-----|
| Background | `#F8F7FC` |
| Sidebar | `#F3F0FA` |
| Card BG | `#FFFFFF` |
| Primary/Accent | `#7C3AED` (purple) |
| Secondary | `#A78BFA` (light purple) |
| Tertiary | `#C4B5FD` (lilac) |
| Text Primary | `#1F2937` |
| Text Muted | `#6B7280` |

**Key Patterns:**
- **Monochromatic palette** — all chart colors are shades of one hue (purple)
- **Icon circles** — icons inside soft tinted circles (`background:rgba(124,58,237,0.1); border-radius:50%`)
- **Donut charts** — for categorical breakdowns (Inquiry Breakdown, Income per Quarter)
- **Stacked bar chart** — shows composition over time (Income Source per Month)
- **Date range pills** — `border:1px solid #E5E7EB; border-radius:8px; padding:6px 14px`

**New techniques:**
- Monochromatic = professional look, easy to generate (just vary lightness of one hue)
- Multiple chart types on one page: donut + bar + stacked bar + line

---

### Design B — Olive Green Financial Dashboard

**Color Palette:**

| Role | Hex |
|------|-----|
| Background | `#FAFAF5` |
| Card BG | `#FFFFFF` |
| Accent Primary | `#84A059` (olive green) |
| Accent Dark | `#3D5A1E` (dark olive) |
| Accent Light | `#C5D8A8` (light sage) |
| Text Primary | `#1A1A1A` |
| Text Muted | `#6B7280` |
| Negative | `#DC2626` |

**Key Patterns:**
- **Greeting header** — "Good Morning, [Name]!" + "Today is [DayOfWeek], [Date]" — personal touch
- **KPI strip (not cards)** — multiple KPIs in a single card separated by vertical dividers (`border-left:1px solid #E5E7EB`)
- **Three-dot menu (···)** on cards — implies interactivity (can be decorative in PBI)
- **Growth rate + arrow** — `↑22%` in green = positive, `↓5%` in red = negative
- **Merged stats in chart area** — "Highest monthly revenue: $5,800 (+18%)" inside the chart card itself
- **Donut chart with right-side legend** — legend items positioned beside the chart, not below

**New technique: KPI Strip (single card with dividers)**
```html
<div style='display:flex; gap:0;'>
  <div style='flex:1; padding:16px; border-right:1px solid #E5E7EB;'>
    <div style='font-size:12px; color:#6B7280;'>Net Profit</div>
    <div style='font-size:24px; font-weight:700; color:#3D5A1E;'>$14,840</div>
    <div style='font-size:11px; color:#84A059;'>Growth rate ↑22%</div>
  </div>
  <div style='flex:1; padding:16px;'>
    <!-- next KPI -->
  </div>
</div>
```

---

### Design C — Navy Financial KPI Dashboard

**Color Palette:**

| Role | Hex |
|------|-----|
| Header BG | `#1E2A5E` (dark navy) |
| Background | `#F5F5F0` (warm off-white) |
| Card BG | `#FFFFFF` |
| Accent | `#4A6FA5` (steel blue) |
| Chart Colors | `#7B9AC7` (light blue), `#2D4A7A` (dark blue) |
| Table Header | `#1E2A5E` |
| Table Alt Row | `#F0F4FA` |

**Key Patterns:**
- **Illustrated header** — decorative character illustrations in the title bar (unique branding)
- **Category tab labels** — colored pill labels above each chart ("Revenue Distribution" in a rounded pill)
- **Full data table** — alternating row colors below charts, with negative values in red
- **Three-chart row** — pie + line + bar side-by-side

**New technique: Data table with alternating rows (HTML)**
```html
<table style='width:100%; border-collapse:collapse; font-size:12px;'>
  <tr style='background:#1E2A5E; color:white;'>
    <th style='padding:8px; text-align:left;'>Month</th>
    <th>Revenue</th><th>Expenses</th>
  </tr>
  <tr style='background:#F0F4FA;'>
    <td style='padding:8px; font-weight:600; color:#1E2A5E;'>January</td>
    <td>$20,000</td><td>$15,000</td>
  </tr>
  <tr style='background:#FFFFFF;'>
    <td style='padding:8px; font-weight:600; color:#1E2A5E;'>February</td>
    <td>$22,000</td><td>$16,000</td>
  </tr>
</table>
```

---

### Design D — Sage Green KPI Tracker

**Color Palette:**

| Role | Hex |
|------|-----|
| Background | `#E8EDDF` (sage cream) |
| Card BG | `#F5F5EE` (warm white) |
| Card Border | `#D4D9C7` (sage border) |
| Accent Primary | `#606C38` (forest green) |
| Accent Light | `#A3B18A` (light olive) |
| Progress Bar BG | `#D4D9C7` |
| Alert Red | `#BC4749` |
| Check Green | `#606C38` |
| Text Primary | `#283618` |

**Key Patterns:**
- **Semi-circular gauges** — half-donut charts for KPIs (New Leads, SQL Rate, Demo Conv, Sales Cycle)
  - Percentage + trend arrow inside the gauge
  - Big number below the gauge arc
- **Checklist cards** — ✅ items (Weekly Target) and ❌ items (Blockers) with status icons
- **Progress bars with labels** — Team 1: 77% with label + bar + percentage
- **Period badge** — "Q1 2026" in a rounded pill at top-left
- **Horizontal bar chart** — Primary Metric comparison (Revenue, Pipeline, Win Rate, Team Quota)

**New technique: Semi-circular gauge (SVG)**
```html
<svg viewBox='0 0 120 70' style='width:100%;'>
  <!-- Background arc -->
  <path d='M 10 65 A 50 50 0 0 1 110 65' fill='none' stroke='#D4D9C7' stroke-width='10' stroke-linecap='round'/>
  <!-- Filled arc (percentage) -->
  <path d='M 10 65 A 50 50 0 0 1 85 20' fill='none' stroke='#606C38' stroke-width='10' stroke-linecap='round'/>
  <!-- Center text -->
  <text x='60' y='55' text-anchor='middle' font-size='14' font-weight='700' fill='#283618'>68%</text>
  <text x='60' y='67' text-anchor='middle' font-size='8' fill='#6B7280'>▲ 15%</text>
</svg>
```

**New technique: Progress bar with label (HTML)**
```html
<div style='display:flex; align-items:center; gap:8px; margin:4px 0;'>
  <span style='width:60px; font-size:11px; color:#283618;'>Team 1</span>
  <span style='font-size:10px; color:#606C38;'>▲</span>
  <span style='font-size:11px; color:#283618;'>77%</span>
  <div style='flex:1; background:#D4D9C7; border-radius:4px; height:8px;'>
    <div style='width:77%; height:100%; background:#606C38; border-radius:4px;'></div>
  </div>
</div>
```

---

### Design E — Navy Gantt Chart

**Color Palette:**

| Role | Hex |
|------|-----|
| Background | `#F5F0E8` (warm cream) |
| Header BG | `#1E2A5E` (dark navy) |
| Bar Color | `#2D3A6E` (navy) |
| Grid Lines | `#E0D8F0` (light lavender) |
| Grid Alt Column | `#E8E0F5` (lavender tint) |
| Text Primary | `#1E2A5E` |
| Decorative | `#4A5AA8` (medium blue) |

**Key Patterns:**
- **Gantt/Timeline layout** — tasks as horizontal bars spanning time periods
- **Grouped task categories** — bold section headers (Planning, Design, Development, Testing)
- **Alternating column shading** — light/dark purple columns for months
- **Decorative icons** — star/snowflake motifs for branding

> [!IMPORTANT]
> Gantt charts are very hard to do with standard PBI visuals. Best approach: **Deneb (Vega)** with a custom bar mark, or **HTML Content** with CSS grid/flexbox.

---

### Master Design Token Library (All Dashboards Combined)

**Reusable Color Palettes by Theme:**

| Theme | BG | Card | Accent | Dark | Light |
|-------|-----|------|--------|------|-------|
| Purple CRM | `#F8F7FC` | `#FFF` | `#7C3AED` | `#4C1D95` | `#C4B5FD` |
| Olive Finance | `#FAFAF5` | `#FFF` | `#84A059` | `#3D5A1E` | `#C5D8A8` |
| Navy Corporate | `#F5F5F0` | `#FFF` | `#4A6FA5` | `#1E2A5E` | `#7B9AC7` |
| Sage Tracker | `#E8EDDF` | `#F5F5EE` | `#606C38` | `#283618` | `#A3B18A` |
| Health Warm | `#F0F4FA` | `#FFF` | `#F4A261` | `#2D3436` | `#FFDAB9` |
| Blue Tech | `#F7F9FB` | `#FFF` | `#3B82F6` | `#1F2937` | `#93C5FD` |
| Dark SnowUI | `#0F0F1A` | `#12121F` | `#8B5CF6` | `#0A0A14` | `#6366F1` |

**New Reusable Components (from all dashboards):**

| Component | Best Tool | Complexity |
|-----------|-----------|------------|
| KPI card with icon | HTML+CSS | Low |
| KPI strip (dividers) | HTML+CSS | Low |
| Semi-circular gauge | HTML+CSS (SVG) | Medium |
| Progress bar row | HTML+CSS | Low |
| Status badge pill | HTML+CSS | Low |
| Checklist (✅/❌) | HTML+CSS | Low |
| Data table (alt rows) | HTML+CSS | Medium |
| Donut chart | Standard PBI / Deneb | Low-Medium |
| Bar/Line/Area chart | Standard PBI | Low |
| Stacked bar chart | Standard PBI | Low |
| Gantt chart | Deneb (Vega) | High |
| Greeting header | HTML+CSS (textbox) | Low |

---

## 27. Layout Wireframe Patterns (from Templates)

> [!TIP]
> These wireframes focus on **structural layout** — grid arrangements, sidebar patterns, and KPI card styling. Use these as blueprints when arranging visuals on a Power BI page.

### Layout F — Vibrant Multi-Color KPIs (Purple Sidebar)

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#C5B9F2` (lavender) |
| Content BG | `#FFFFFF` |
| Sidebar | `#6C3FC5` (deep purple) |
| KPI 1 | `#6B8CF5` (cornflower blue) |
| KPI 2 | `#9B72E8` (medium purple) |
| KPI 3 | `#F27FAE` (pink) |
| KPI 4 | `#F5B731` (golden yellow) |

**Key Patterns:**
- **Each KPI card a different vibrant color** — creates a playful, energetic feel
- **Sidebar with icon navigation** — icons only, compact width (~50px)
- **Filter icon (🔽) + collapse (≪)** in the top-right
- **Title in bold uppercase** — "REALIZADO VS. META"

---

### Layout G — Teal/Green Sidebar with Card Grid

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#D8E8E4` (mint/teal gradient background) |
| Content BG | `#F5F7F6` (off-white) |
| Sidebar | `#3BB08F` (teal green) |
| Card BG | `#FFFFFF` |
| Icon Accent | `#3BB08F` |
| Text | `#3BB08F` (sidebar), `#6B7280` (content) |

**Key Patterns:**
- **Sidebar with text labels** — icons + PAGE1/PAGE2/PAGE3 labels
- **3 KPI cards across top** — each with a small icon in the top-left corner
- **2×2 grid below** — for larger chart cards
- **Hamburger menu (≡)** in top-right
- **Generous padding** — cards have large gaps between them

**Grid Layout (PBI Position Mapping):**
```
┌─────────┬───────────┬───────────┬───────────┐
│ SIDEBAR │  KPI 1    │  KPI 2    │  KPI 3    │  y:30, h:90
│ (50px)  ├───────────┴───────────┼───────────┤
│         │  Chart 1 (wide)       │ Chart 2   │  y:140, h:160
│         ├───────────┬───────────┼───────────┤
│         │  Chart 3              │ Chart 4   │  y:320, h:200
└─────────┴───────────┴───────────┴───────────┘
```

---

### Layout H — Dark Mode with Gradient KPI Cards

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#1A1F2E` (very dark charcoal-blue) |
| Card BG | `#232A3A` (dark card) |
| Card Border | `#2E3648` (subtle dark border) |
| KPI Gradient 1 | `linear-gradient(135deg, #2563EB, #1A1F2E)` (blue fade) |
| KPI Gradient 2 | `linear-gradient(135deg, #EA580C, #1A1F2E)` (orange fade) |
| KPI Gradient 3 | `linear-gradient(135deg, #6B7280, #1A1F2E)` (silver fade) |
| Sidebar Icons | `#4B5563` (muted gray) |
| Active Icon | `#3B82F6` (bright blue) |

**Key Patterns:**
- **Gradient KPI cards** — each card has a diagonal gradient fading from a color to the background
- **3×3 equal grid** — uniform card sizes across the page
- **Collapsible sidebar** — `>>` icon to expand, icon-only when collapsed
- **Cards blend into background** — very subtle border, almost invisible separation

**CSS for gradient KPI card:**
```css
background: linear-gradient(135deg, rgba(37,99,235,0.6) 0%, rgba(37,99,235,0) 60%);
border: 1px solid rgba(255,255,255,0.05);
border-radius: 16px;
```

---

### Layout I — Deep Navy/Purple Dark Mode

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#0F1129` (deep navy) |
| Card BG | `#1A1D3A` (dark purple-navy) |
| Card Border | `#252850` (muted purple border) |
| KPI Gradient 1 | `linear-gradient(135deg, #7C3AED, #1A1D3A)` (purple fade) |
| KPI Gradient 2 | `linear-gradient(135deg, #4B5563, #1A1D3A)` (gray fade) |
| Right Panel | `#141630` (darkest navy) |
| Sidebar | `#0D0F24` (near-black) |

**Key Patterns:**
- **Tall right panel** — spans full height, darker than main content area (for filters, details, or KPI summary)
- **3 KPI cards + right panel** — top row has 3 small gradient cards + tall right panel
- **Monochromatic dark** — all purple/navy shades, no bright accent cards
- **Glass-like borders** — `rgba(255,255,255,0.03)` borders on cards

**CSS for deep navy card:**
```css
background: #1A1D3A;
border: 1px solid rgba(255,255,255,0.03);
border-radius: 16px;
box-shadow: 0 4px 24px rgba(0,0,0,0.3);
```

---

### Layout J — Two-Panel (Light + Dark Navy Sidebar)

**Color Palette:**

| Role | Hex |
|------|-----|
| Content BG | `#E8ECF5` (light lavender) |
| Card BG | `#FFFFFF` |
| Right Panel | `#1E2A5E` (dark navy) |
| KPI Gradient 1 | `linear-gradient(135deg, #7C3AED, #1A1D3A)` (purple) |
| KPI Gradient 2 | `linear-gradient(135deg, #EA580C, #1A1D3A)` (orange) |
| Sidebar | `#2D3A6E` (medium navy) |

**Key Patterns:**
- **Split layout: ~70% light / ~30% dark** — light content area with a dark navy right panel
- **KPI cards with gradient** — same gradient technique but on a light background
- **Fewer KPIs (2)** — when right panel takes significant space, reduce KPI count
- **Clean card separation** — white cards on lavender background, subtle shadows

---

### Page Layout Templates Summary

| Layout | Style | Grid | Sidebar | Right Panel | Best For |
|--------|-------|------|---------|-------------|----------|
| F | Vibrant multi-color | 4 KPI + content | Purple (icon-only) | No | Playful/KPI-heavy |
| G | Clean teal | 3 KPI + 2×2 | Teal (icon+text) | No | Standard dashboard |
| H | Dark gradient | 3×3 grid | Dark (collapsible) | No | Modern dark theme |
| I | Deep navy | 3 KPI + 2+1 | Navy (collapsible) | Yes (tall) | Executive view |
| J | Light+dark split | 2 KPI + 2+1 | Navy (collapsible) | Yes (navy) | Mixed theme |

### Collapsible Sidebar Pattern (PBI Implementation)

In Power BI, the sidebar is typically:
1. An **HTML Content visual** with icon SVGs (for the collapsed state)
2. A **bookmark** to toggle between collapsed (icon-only) and expanded (icon+text) states
3. Position: `x:0, y:0, height:720, width:50` (collapsed) or `width:160` (expanded)
4. High `z` value to layer above other visuals

---

## 28. Advanced Layout Patterns — Part 2

### Layout K — Dark Purple with Gold Accent Panel

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#2A2344` (dark purple) |
| Top Nav BG | `#1E1A38` (darker purple) |
| Card BG | `#352E50` (medium purple) |
| Card Border | `#433B60` (muted purple) |
| KPI 1 | `linear-gradient(135deg, #6B8CF5, #352E50)` (blue-purple) |
| KPI 2 | `linear-gradient(135deg, #9B72E8, #352E50)` (purple) |
| KPI 3 | `linear-gradient(135deg, #C08B8B, #352E50)` (mauve) |
| KPI 4 | `linear-gradient(135deg, #8B7660, #352E50)` (brown) |
| Accent Panel | `#D4A853` (gold/amber) |
| Nav Icons | `#6BB8C4` (teal, active) |

**Key Patterns:**
- **Top navigation bar** — horizontal bar with hamburger + centered icons (home, chart, settings)
- **KPI cards with colored circle indicators** — small colored dot on the right side of each card
- **Gold accent panel** — tall right panel in warm gold for highlighting featured content or KPIs
- **No sidebar** — navigation moved to top bar instead

**New technique: Top navigation bar (vs sidebar)**
```
┌──────────────────────────────────────────┐
│  ≡     🏠  📈  ⚙️                        │  h: 30px, dark bar
├────────┬────────┬────────┬────────┬──────┤
│ KPI 1  │ KPI 2  │ KPI 3  │ KPI 4  │      │  h: 80px
├────────┴────────┼────────┴────────┤ GOLD │
│  Chart 1        │  Chart 2        │ PANEL│  h: 200px
├────────┬────────┼────────┬────────┤      │
│ Chart 3│ Chart 4│ Chart 5│ Chart 6│      │  h: 200px
└────────┴────────┴────────┴────────┴──────┘
```

---

### Layout L — Ice Blue Minimal (5 KPIs)

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#EDF4FA` (ice blue) |
| Card BG | `#FFFFFF` |
| Card Border | `#D6E6F2` (light blue border) |
| Sidebar BG | `#EDF4FA` (matches page) |
| Icon Accent | `#5CB8C8` (teal) |
| Text | `#6B7280` |

**Key Patterns:**
- **5 KPI cards across top** — more KPIs than the typical 3-4 layout
- **Ultra-minimal styling** — barely visible borders, no shadows
- **Icon-only sidebar** with 7 icons (hamburger, home, chart, settings, globe, LinkedIn, etc.)
- **Social media icons in sidebar** — useful for linking to external profiles
- **3×3 grid for charts** — very spacious with generous gaps

---

### Layout M — People Analytics (Teal Gradient, Multi-Page)

> [!IMPORTANT]
> This is a **multi-page system** — same sidebar/branding across pages with different content. Very common in real enterprise dashboards.

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#C5DED6` (mint/sage gradient) |
| Content BG | `#FFFFFF` (white card container) |
| Header/Analysis | `#2A8C87` (teal) |
| Sidebar | `#2A8C87` → `#1F6E6A` (teal gradient) |
| Active Nav | `#FFFFFF` (white bg on active) |
| Inactive Nav | transparent |
| KPI Icon BG | `#FFE0E6` (pink), `#FFF0D4` (amber), `#E0F0FF` (blue) |
| Text Primary | `#1A3A3A` (dark teal) |
| Text Subtitle | `#2A8C87` (teal) |
| Section Title | `#1A3A3A` bold uppercase |

**Key Patterns:**
- **Two-column layout** — left column for KPI cards, right section for analysis charts
- **"ANALISAR" filter bar** — dedicated slicer/filter section with rounded container and icon
- **Category column headers** — bold uppercase labels above each chart column (POR GÊNERO, POR FAIXA ETÁRIA)
- **Character illustrations** — decorative people illustrations in sidebar/corners (branding)
- **Multi-page sidebar navigation** — "Overview" and "Frequência" with active state (white bg)
- **Colored icon circles** — each KPI has a distinct pastel circle background

**Page variants in same system:**

| Page | Title | KPI Count | Analysis Columns | Bottom Charts |
|------|-------|-----------|-----------------|---------------|
| Overview | OVERVIEW | 3 | 3 (POR, GÊNERO, FAIXA ETÁRIA) | % TURNOVER + Timeline |
| Frequência | FREQUÊNCIA | 2 | 4 (ESCOLARIDADE, GÊNERO, FAIXA ETÁRIA, ETINIA) | 2× % HORAS EXTRAS |

**New technique: Multi-page design system**
- Keep sidebar, branding, and color scheme **identical** across pages
- Change only the content area + page title
- Active page gets white background in sidebar, inactive is transparent
- Each page can have different KPI count and chart layout

**CSS for teal gradient header section:**
```css
background: linear-gradient(135deg, #2A8C87, #1F6E6A);
border-radius: 20px;
padding: 24px;
color: white;
```

**CSS for filter bar:**
```css
background: #FFFFFF;
border-radius: 30px;
padding: 8px 20px;
display: flex;
align-items: center;
gap: 8px;
box-shadow: 0 2px 8px rgba(0,0,0,0.08);
```

---

### Layout N — Contratos SETIM (Card-Shaped Filters)

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#C5DED6` (mint/sage) |
| Content BG | `#FFFFFF` |
| Header Section | `#2A8C87` (teal) |
| Sidebar | `#2A8C87` (teal, thin strip) |
| Filter Cards | `#FFFFFF` (white, stacked) |
| Filter Card Border | `#E5E7EB` (light gray) |
| Text | `#1A3A3A` (dark teal) |

**Key Patterns:**
- **Card-shaped filter buttons** — 6 white rounded cards stacked vertically in left column (acting as slicers/filters)
- **Large teal header area** — takes ~40% of top space for hero KPI or featured visual
- **"EXECUÇÃO MENSAL" section** — bottom white area with tab/button label
- **Minimal sidebar** — very thin teal strip on far left

**New technique: Stacked card filters**
```
┌────────┬──────────────────────────────┐
│ Title  │                              │
│        │     TEAL HEADER AREA         │  h: 250px
├────────┤    (hero KPI / feature)      │
│ Card 1 │                              │
├────────┼──────────────────────────────┤
│ Card 2 │                              │
├────────┤  EXECUÇÃO MENSAL             │  h: 250px
│ Card 3 │  (main content / table)      │
├────────┤                              │
│ Card 4 │                              │
├────────┤                              │
│ Card 5 │                              │
├────────┴──────────────────────────────┘
```

In PBI, each "filter card" would be a **standard slicer** or **button with bookmark** — positioned as individual visuals with uniform size and spacing.

---

### Updated Layout Templates Summary

| Layout | Style | Grid | Navigation | Accent | Best For |
|--------|-------|------|------------|--------|----------|
| K | Dark purple + gold | 4 KPI + 2×3 + gold panel | Top bar (icons) | Gold right panel | Executive dark |
| L | Ice blue minimal | 5 KPI + 3×2 | Sidebar (7 icons) | Teal icons | Clean analytics |
| M | Teal People Analytics | 3 KPI left + 3 charts right | Sidebar (pages) | Teal gradient | HR/enterprise multi-page |
| N | Teal SETIM | 6 filter cards + hero + content | Thin sidebar | Teal header | Gov/contract tracking |

### New Component Library (from this batch)

| Component | HTML/CSS Pattern | Notes |
|-----------|-----------------|-------|
| Top nav bar | `display:flex; height:30px; bg:#1E1A38` | Alternative to sidebar |
| KPI with color dot | `circle: w:16px h:16px border-radius:50%` | Status indicator on card |
| Gold/accent tall panel | Full-height colored panel on right | Feature spotlight |
| Stacked card filters | Uniform white cards, 100% width, stacked | Alternative to slicers |
| "ANALISAR" filter bar | Rounded pill container with icon | Filter/slicer grouping |
| Multi-page nav | Active=white bg, Inactive=transparent | Sidebar page switching |
| Character illustrations | Positioned at corners/sidebar | Branding/personality |

---

### Layout O — Dark Charcoal with Teal Accent + Top Nav

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#1E2530` (dark charcoal) |
| Card BG | `#283040` (slightly lighter charcoal) |
| Card Border | `#334050` (subtle border) |
| KPI Strip BG | `#283040` (same as card) |
| KPI Icons | `#5CB8C8` (teal) |
| Right Panel | `#4A8A8C` (muted teal) |
| Top Nav | `#1E2530` (matches page) |
| Social Icons | `#5CB8C8` (globe, LinkedIn) |

**Key Patterns:**
- **5 KPI icons in horizontal strip** — single row with small icon-only KPI indicators
- **Top nav with social icons on right** — globe 🌐 + LinkedIn icons at far right
- **Teal right accent panel** — tall, spans both chart rows
- **2 wide + 2 wide grid** — two chart cards per row, evenly split

---

### Layout P — Teal Sidebar with Mixed Gradient KPIs

**Color Palette:**

| Role | Hex |
|------|-----|
| Page BG | `#D8EAE5` (mint green) |
| Content BG | `#E8ECF5` (lavender) |
| Card BG | `#FFFFFF` |
| Sidebar | `#004D4D` (very dark teal) |
| Right Panel | `#004D4D` (dark teal, ~30% width) |
| KPI 1 | `linear-gradient(135deg, #006D5B, #003D3D)` (dark teal) |
| KPI 2 | `linear-gradient(135deg, #B84820, #4A1A0A)` (rust orange) |
| KPI 3 | `linear-gradient(135deg, #00897B, #004D4D)` (bright teal) |

**Key Patterns:**
- **Mixed gradient KPI colors** — teal + orange + teal creates variety without being chaotic
- **Collapsible dark sidebar** — `>>` icon to expand
- **Dark right panel** — same color as sidebar, creates visual "bookend" framing
- **Content sandwiched** — light lavender content between dark sidebar and dark right panel

**CSS for rust/orange gradient:**
```css
background: linear-gradient(135deg, #B84820 0%, #4A1A0A 100%);
border-radius: 12px;
```

---

### Layout Q — Navy Header with Lens Flare Glow

**Color Palette:**

| Role | Hex |
|------|-----|
| Header BG | `#0D1B3E` (deep navy) |
| Header Glow | `radial-gradient(ellipse at 50% 0%, rgba(100,140,255,0.15), transparent 70%)` |
| Page BG | `#E8ECF0` (light silver-blue) |
| Card BG | `#FFFFFF` |
| Card Top Accent | `#2A4080` (dark blue) |
| KPI Pill BG | `#1A2D5A` (navy) |
| Footer | `#D8DCE4` (light gray) |

**Key Patterns:**
- **No sidebar** — full-width layout, navigation in header only
- **Lens flare/glow effect** — subtle radial gradient centered at top of header creates a cinematic glow
- **KPI pills in header** — 2 small rounded KPI cards + wide stats bar within the dark header
- **3-column equal cards** — three white cards of identical size, each with a blue accent top band
- **Light gray footer strip** — subtle footer area at bottom

**CSS for lens flare glow:**
```css
background: #0D1B3E;
position: relative;
/* Pseudo-element for glow */
background-image: radial-gradient(
  ellipse at 50% 0%,
  rgba(100, 140, 255, 0.15) 0%,
  transparent 70%
);
```

**New technique: Card with colored top accent band**
```css
border-radius: 12px;
overflow: hidden;
/* Blue band at top */
border-top: 4px solid #2A4080;
/* Or use a pseudo-element for thicker band */
```

---

### Complete Layout Catalog (A-Q Summary)

| ID | Name | Theme | Navigation | Unique Feature |
|----|------|-------|------------|----------------|
| A | Purple CRM | Light mono-purple | Left sidebar | Monochromatic palette |
| B | Olive Finance | Light olive-green | None | KPI strip with dividers |
| C | Navy Financial | Light + navy header | None | Data table + alternating rows |
| D | Sage Tracker | Light sage-green | None | Semi-circular SVG gauges |
| E | Navy Gantt | Light + navy | None | Gantt timeline chart |
| F | Vibrant Multi-Color | Lavender + vibrant | Purple sidebar | Each KPI a different color |
| G | Teal Grid | Mint/teal | Teal sidebar (text) | 3 KPI + 2×2 grid |
| H | Dark Gradient | Dark charcoal | Dark collapsible | Gradient fade KPI cards |
| I | Deep Navy | Deep navy/purple | Navy collapsible | Tall right panel + glass borders |
| J | Light+Dark Split | Lavender + navy | Navy collapsible | 70/30 light-dark split |
| K | Dark Purple Gold | Dark purple | Top nav bar | Gold accent panel |
| L | Ice Blue | Ice blue minimal | 7-icon sidebar | 5 KPIs, ultra-minimal |
| M | People Analytics | Teal gradient | Multi-page sidebar | Enterprise multi-page system |
| N | SETIM Contracts | Mint + teal | Thin teal strip | Card-shaped filter buttons |
| O | Dark Charcoal Teal | Dark charcoal | Top nav + social | Teal right panel + social icons |
| P | Teal Mixed Gradients | Mint layered | Dark teal collapsible | Orange+teal gradient mix |
| Q | Navy Lens Flare | Navy + silver | Header only | Lens flare glow + 3-col cards |

---

## 29. Rules of Engagement: Visual Technology Strategy

> [!IMPORTANT]
> The golden rule for building premium Power BI dashboards: **Use each technology where it shines. Don't force one tool for everything.** 
> Use the following rubric to decide which technology to use for a given component.

### 🏢 HTML Content Visual (HTML + CSS)
**Best for:** Layout, Structure, Text, and Micro-Interaction

- ✅ **Use for**: 
  - KPI Cards (especially with gradients or complex layouts)
  - Custom Headers & Titles
  - Filter Drawers & Sidebars (paired with Bookmarks)
  - Layout Panels (e.g., placing a dark background panel behind charts)
  - Simple inline SVG graphics (like the semi-circular gauges) that can be generated with string concatenation.
- ❌ **Do NOT use for**: 
  - Interactive data charts (bar, line, scatter) — you lose cross-filtering and tooltips.
  - Complex visualizations — generating complex SVG paths purely via DAX string concatenation is unmaintainable.
- 💡 **Superpower**: Full CSS support (`@keyframes` animations, hover effects, flexbox layouts, gradients, borders, shadows).

### 📊 Standard Power BI Visuals
**Best for:** Standard Analytics & Interactive Drill-down

- ✅ **Use for**: 
  - Line Charts, Bar Charts, Column Charts, Scatter Plots, Matrices
  - Slicers (native slicers are required for cross-filtering out-of-the-box)
  - Any time the user MUST cross-filter other visuals by clicking a data point.
- ❌ **Do NOT use for**: 
  - KPI Cards (they lack CSS styling capabilities and look "boxy")
  - Highly customized aesthetic layouts.
- 💡 **Superpower**: Zero maintenance, maximum performance, native interactivity, built-in tooltips.

### 🎨 Deneb (Vega-Lite)
**Best for:** Unorthodox Data Viz & High-Density Insights

- ✅ **Use for**: 
  - Custom chart types (Sankey, Beeswarm, Joyplots, Org Trees, Gantt charts)
  - High-density visual tables (like sparklines inside tables)
  - When you need absolute pixel-perfect control over every axis, tick mark, and data label in a chart.
- ❌ **Do NOT use for**: 
  - Simple bar/line charts (use standard visuals — they load faster and handle cross-filtering easier).
  - KPI Cards (HTML is much easier to write and maintain via DAX than a JSON spec).
  - Anything that needs CSS transitions or `@keyframes` (Deneb does not support CSS).
- 💡 **Superpower**: Grammar of graphics allows building any static data visualization imaginable from scratch.

### 🚀 Deneb (Vega)
**Best for:** Animated Data Storytelling

- ✅ **Use for**: 
  - Complex animated sequences (Bar chart races, simulation particles, timer-based data progression).
- ❌ **Do NOT use for**: 
  - Anything else. Vega syntax is 3-5x more verbose and complex than Vega-Lite. Only pay this complexity cost if animation is an absolute hard requirement.
- 💡 **Superpower**: Full event streaming and timer loops natively.

### The Hybrid Dashboard Workflow

1. **Base Layer**: Standard PBI Background or simple HTML rectangular panels for structure.
2. **Navigation/Framing**: HTML Content visuals for Sidebars, Filter Drawers, and Headers with CSS hover effects.
3. **Primary KPIs**: HTML Content visual measures returning HTML strings for beautifully styled gradient cards.
4. **Primary Analysis**: Standard PBI bar/line charts placed inside transparent areas for maximum interactivity.
5. **Specialty Viz (Optional)**: 1 or 2 Deneb (Vega-Lite) charts reserved strictly for custom plots (like a Gantt or Bullet chart).
6. **Interaction**: Use PBI Bookmarks over HTML visuals to toggle states (like opening a drawer).

---

## 30. PBIR Deep Dive: Native Slicers & Stateful Bookmarks

> [!CAUTION]
> When building custom UI flows (like a Filter Drawer), it is a mistake to think of Bookmarks purely as "Visibility Toggles." In Power BI PBIR schema, **Bookmarks are Dashboard State Snapshots.**

### Native Slicer Architecture in PBIR
When a user interacts with a standard Power BI slicer (e.g., selecting "Beta" in the Team dropdown), the state is not saved in a simple string. It is saved in the visual's `objects.general.filter` property as an Abstract Syntax Tree (AST).

**Example of an active Slicer selection (`Team = 'Beta'`):**
```json
"objects": {
  "general": [
    {
      "properties": {
        "filter": {
          "filter": {
            "Version": 2,
            "From": [{"Name": "s", "Entity": "SalesTeamData", "Type": 0}],
            "Where": [
              {
                "Condition": {
                  "In": {
                    "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "s"}}, "Property": "Team"}}],
                    "Values": [[{"Literal": {"Value": "'Beta'"}}]]
                  }
                }
              }
            ]
          }
        }
      }
    }
  ]
}
```

### Stateful Bookmarks
Because slicers mutate the data state, Bookmarks have to accurately capture whether they intend to **restore data state** or **just toggle UI layout**. 

A true "Dashboard State Snapshot" Bookmark (like one created manually in PBI Desktop) doesn't just toggle a `visualContainerGroup`'s `isHidden` property. It maps through every single `visualContainer` on the page and caches the exact active filters (`byExpr`) assigned to them.

**Example of a Stateful Bookmark (`explorationState.sections.page_name.visualContainers.visual_name`):**
```json
"visualContainers": {
  "my_bar_chart": {
    "filters": {
      "byExpr": [
        {
          "name": "random_guid",
          "type": "Categorical",
          "expression": {
            "Column": {
              "Expression": {"SourceRef": {"Entity": "TrafficData"}},
              "Property": "Category"
            }
          },
          "howCreated": 0
        }
      ]
    }
  }
}
```

### The Takeaway for PBIR Code Editing
1. **Never hand-write data filters in PBIR JSON**: The AST for `objects.general.filter` inside slicers, or `filters.byExpr` inside bookmarks, is far too rigid and complex to manually guess. 
2. **If you need a Data Snapshot**: Let the user create the slicers and the bookmarks via the Power BI Desktop GUI. 
3. **If you are only doing UI Animation (like opening a drawer)**: You can hand-write a bare-bones bookmark JSON that **ONLY** contains a `visualContainerGroups` array toggling `isHidden`, avoiding the `visualContainers` filter snapshot entirely. Ensure `options.suppressData` is set to `true` to prevent the bookmark from accidentally resetting user slicer selections when they open the drawer.

---

## Section 31: Best Practices for Programmatic Generation of PBIR & TMDL

When programmatically generating `.pbip` files (TMDL semantic models and JSON report definitions), it is crucial to adhere perfectly to schema versions and parsing rules. If these files are malformed, Power BI Desktop will fail to open the project entirely.

### 1. TMDL Lexing and Indentation Strictness
TMDL (Tabular Model Definition Language) does not use brackets for scope; it uses whitespace (indentation) similarly to Python or YAML. Moreover, the parser reads literal newlines and tabs to construct the object tree *before* evaluating DAX expressions.
*   **The Error**: `TMDL Format Error: Parsing error type - Indentation`
*   **The Cause**: We generated DAX string literals (e.g., HTML code inside double quotes `""`) that spanned multiple lines and contained raw literal tabs and spaces. The TMDL AST lexer interpreted those literal tabs inside the DAX string as structural object properties, completely breaking the parser.
*   **The Rule**: 
    1.  **NEVER** use raw multi-line strings (e.g., `" \n \t "`) for DAX measures when programmatically generating `.tmdl` files.
    2.  Instead, completely flatten strings onto a single line without raw newlines/tabs, OR use DAX string concatenation on subsequent lines (with proper `&` operators), or use the explicit TMDL multi-line formula syntax (`'''`). The safest programmatic method is compressing all DAX HTML into a single-line string.
    3.  All properties belonging to an object (e.g., `formatString`, `lineageTag`) must be indented exactly one tab further than the parent object declaration.

### 2. GUID Lineage Tags
TMDL requires unique identifiers (`lineageTag`) for all objects to resolve dependencies and metadata state.
*   **The Error**: Model load failure or corruption warnings.
*   **The Cause**: Accidentally using invalid hex characters (e.g., `#` instead of `a-f` or `0-9`) in a generated GUID.
*   **The Rule**: Whenever generating a mock `lineageTag` for new tables, columns, or measures in TMDL, the string must strictly enforce the `8-4-4-4-12` hex format (e.g., `f9e8d7c6-b5a4-0000-0001-1234567890ab`).

### 3. PBIR Schema Version Compatibility
Power BI projects are tightly bound to specific JSON schema versions.
*   **The Error**: `Can't resolve schema '1.0.0' in 'pages/pages.json'. This report was edited in a newer version of Power BI.`
*   **The Cause**: We overwrote the registry file (`pages.json`) using a schema version (`pages/1.0.0`) that was newer than the version the project was originally built on (`pagesMetadata/1.0.0`). The newer schema expects an array of page *objects*, while the older one expects an array of strings (`pageOrder`). 
*   **The Rule**: Always dynamically ingest the existing `$schema` URL and mirror its required object structure before applying `replace_file_content` macros. Do not assume the newest schema version is applicable unless explicitly prompted to upgrade the project.

---

## Section 34: Data Storytelling & Visual Narrative (Governança BI)
**Origin:** Extracted from the user's "Governança BI" dashboard (`Projeto para aprendizado`) page and visual JSON topologies.

The dashboard uses a highly structured narrative to convey the overall health and maturity of an IT organization (in this case, a Tribunal). It breaks the story into 4 distinct pillars (pages), each answering a specific question about IT Governance:

### 1. The Bedrock: System Uptime (Page: PJe 1° e 2° Grau)
*   **The Question:** "Are the core machines running?"
*   **The Story:** This acts as the baseline. It uses a custom Gauge Dial (`dg5...`) and a Combo Chart (`lineClusteredColumnComboChart`) to plot the current system availability strictly against an SLA target line (90%). It relies heavily on dynamic DAX bounds (`targetstart`, `targetend`, `mediastart`) to definitively tell the user if the systems are currently healthy. 

### 2. Strategic Benchmarking (Page: iGovTIC)
*   **The Question:** "How are we doing compared to everyone else?"
*   **The Story:** The narrative shifts from raw operational metrics to strategic standing. Utilizing a Line Chart (`lineChart`) and a Combo Chart, it juxtaposes the Tribunal's own iGovTIC evaluation score (`VALOR`) against the national average of other courts (`MÉDIAS ESTADUAIS`). Reference threshold lines explicitly map the score to maturity bands—*Satisfatório (40)*, *Aprimorado (70)*, and *Excelência (90)*—while tracking the state ranking over time.

### 3. The Human Element (Page: Service Desk)
*   **The Question:** "Are our users actually happy?"
*   **The Story:** Having established that systems run and strategy is sound, the narrative focuses on the end-user. A Clustered Column Chart (`clusteredColumnChart`) displays Service Desk survey responses over time. The storytelling here leans heavily on cognitive color mapping: exact survey strings (Excelente, Muito Bom, Bom, Razoável, Ruim) are hardcoded in the visual JSON to display as a color gradient from bright green (`#00C800`) to pure red (`#FF0000`).

### 4. Efficient Execution (Page: Capacitações / Budget)
*   **The Question:** "Are we actually executing our plans?"
*   **The Story:** The final pillar evaluates internal efficiency. A Combo Chart plots planned actions (`PREVISTO`) versus what was successfully carried out (`REALIZADO`) over the years. To ensure the story is instantly understandable, dynamic labels using the DAX measure `% Executado` are placed prominently over the bars, immediately highlighting any execution gaps.---

## Section 33: DAX Logical Patterns for Advanced KPIS (Governança BI Layout)
**Origin:** Extracted from the user's "Governança BI" dashboard (`Projeto para aprendizado`) semantic model `.tmdl` files.

The user utilizes several common DAX patterns to calculate their metrics. When generating models for dashboards, these are the proven formulas to use:

### 1. Context-Clearing Percentages (ALLEXCEPT)
To calculate a percentage of a total while ignoring *some* slicers but respecting others, the user uses `ALLEXCEPT` to establish the denominator context. This is visible in the `'Percentual de Respostas'` measure:
```dax
VAR TotalGeralNoPeriodo =
    CALCULATE(
        [Total de Respostas]/100,
        ALLEXCEPT(
            '5 Satisfação Service Desk',
            '5 Satisfação Service Desk'[Data da Resposta], 
            'dCalendario'[Ano],            
            '5 Satisfação Service Desk'[Pergunta]        
        )
    )
RETURN
    IF(TotalGeralNoPeriodo = 0, BLANK(), DIVIDE(RespostasNoPeriodo, TotalGeralNoPeriodo))
```

### 2. Time-Based Availability Calculations
The dashboard calculates a "System Availability %" by dividing the summed unavailable minutes by the *total possible minutes in the filtered context*. It checks how many days are active in the `dCalendario` filter context:
```dax
VAR MinutosIndisponiveisNoContexto = [Total Minutos Indisponíveis]
VAR DiasNoContexto = COUNTROWS('dCalendario')
VAR TotalMinutosNoContexto = DiasNoContexto * 1440 -- (1440 minutes in a day)
VAR TaxaIndisponibilidade = DIVIDE( MinutosIndisponiveisNoContexto, TotalMinutosNoContexto )
```

### 3. Safe Division and Blanks
Across all metrics (like `% Execução` budget), the user employs the `DIVIDE` function with a safe alternate result (like `0` or `BLANK()`) and uses `IF(ISBLANK())` to ensure charts remain clean when data is missing, avoiding `NaN` or Infinity errors.---

## Section 32: Dynamic Titles, Textboxes (Markdowns), and Slicers (Governança BI Layout)
**Origin:** Extracted from the user's "Governança BI" dashboard (`Projeto para aprendizado`) layout.

### Dynamic DAX Titles in PBIR
To create a dynamic title that changes based on slicer selection, the user creates a DAX measure evaluating to text (e.g., `"Disponibilidade PJe do Ano " & SELECTEDVALUE('dCalendario'[Ano])`). 
In the `visual.json` file, instead of a static `Literal` string, the title property is bound to the measure using the `Measure` expression object:
```json
"visualContainerObjects": {
  "title": [
    {
      "properties": {
        "text": {
          "expr": {
            "Measure": {
              "Expression": {
                "SourceRef": { "Entity": "1 Disponibilidade de Sistemas" }
              },
              "Property": "Título Gráfico PJe"
            }
          }
        }
      }
    }
  ]
}
```

### Textboxes (Markdowns)
Standard Power BI textboxes have `visualType: "textbox"`. The text and its rich formatting are stored inside `objects.general`:
```json
"objects": {
  "general": [
    {
      "properties": {
        "paragraphs": [
          {
            "textRuns": [
              {
                "value": "Pergunta",
                "textStyle": {
                  "fontSize": "12pt",
                  "color": "#ffffff"
                }
              }
            ],
            "horizontalTextAlignment": "center"
          }
        ]
      }
    }
  ]
}
```

### Dropdown Slicer Configuration
Slicers (`visualType: "slicer"`) enforce their display mode (like Dropdown) via the `objects.data` property:
```json
"objects": {
  "data": [
    {
      "properties": {
        "mode": {
          "expr": { "Literal": { "Value": "'Dropdown'" } }
        }
      }
    }
  ]
}
```
Styling for slicer items (font size, color, background) is applied in `objects.items`, and the header in `objects.header`.

---

## 29. Modern Web Dashboard Design — Princípios e Implementação no PBIR

> [!IMPORTANT]
> Esta seção documenta os princípios de design de dashboards modernos (inspirados em shadcn/ui, Tremor, Vercel, Linear, Stripe) **e como implementar cada regra nos arquivos JSON do formato PBIP/PBIR**.
>
> Fontes: Nielsen Norman Group, Stephen Few (Information Dashboard Design), Cole Nussbaumer Knaflic (Storytelling with Data), Edward Tufte, Microsoft Learn, shadcn/ui, Tremor, Cloudscape Design System.

---

### 29.1 As 10 Regras Fundamentais de Design de Dashboard

#### Regra 1 — Hierarquia visual: posição importa
**Princípio**: O elemento mais importante deve estar no canto superior esquerdo. Usuários leem em Z (topo-esquerda → topo-direita → baixo-esquerda → baixo-direita).

**Implementação no PBIR**: Controlar a posição pelos campos `x`, `y` no `position` do `visual.json`.
```json
// KPI mais importante: canto superior esquerdo
"position": { "x": 24, "y": 96, "width": 292, "height": 100 }

// Gráficos de tendência: meio da página
"position": { "x": 24, "y": 212, "width": 860, "height": 340 }

// Tabela de detalhes: parte inferior
"position": { "x": 24, "y": 568, "width": 1232, "height": 128 }
```

**Ordem recomendada para licitações (1280×720):**
```
y:  0–80  → Cabeçalho / título / slicers
y: 80–200 → KPI cards (4–5 métricas principais)
y:200–560 → Gráficos principais (linha, barras, scatter)
y:560–720 → Tabela de detalhe
```

---

#### Regra 2 — Máximo de visuais por página
**Princípio**: Microsoft recomenda **máximo 8–10 visuais** por página. Mais que isso reduz o tamanho de cada visual, comprometendo a legibilidade.

**Verificação**: Contar `visual.json` na pasta `visuals/` de cada página:
```bash
ls pages/00_visao_geral/visuals/ | wc -l
```

**O que NÃO conta como "visual" para o limite:**
- Textboxes de título/subtítulo
- Shapes decorativas
- Slicers de filtro (são controles, não visualizações)

---

#### Regra 3 — Paleta semântica: máximo 5–6 cores com significado
**Princípio**: Cores sem significado são ruído. O cérebro humano distingue com clareza no máximo 7 categorias visuais distintas (Miller's Law). Cada cor deve ter um papel fixo e consistente.

**Paleta semântica recomendada para o projeto (shadcn/Tailwind):**

| Papel | Cor | Hex | Uso |
|-------|-----|-----|-----|
| Principal | Blue | `#3B82F6` | Barras primárias, linhas de tendência |
| Positivo | Emerald | `#10B981` | Crescimento YoY, metas atingidas |
| Negativo | Rose | `#F43F5E` | Queda YoY, alertas |
| Atenção | Amber | `#F59E0B` | Aviso, variação neutra |
| Secundário | Indigo | `#6366F1` | Segunda série, linha de comparação |
| Neutro | Zinc | `#71717A` | Labels secundários, eixos |

**Implementação no PBIR — colorir série de um gráfico:**
```json
// Em visual.json → objects → dataPoint
"dataPoint": [
  {
    "properties": {
      "fill": {
        "solid": {
          "color": { "expr": { "Literal": { "Value": "'#3B82F6'" } } }
        }
      }
    }
  }
]
```

**Colorir uma categoria específica (ex: linha negativa em vermelho):**
```json
"dataPoint": [
  {
    "properties": {
      "fill": {
        "solid": {
          "color": { "expr": { "Literal": { "Value": "'#F43F5E'" } } }
        }
      }
    },
    "selector": {
      "data": [{
        "scopeId": {
          "Comparison": {
            "ComparisonKind": 0,
            "Left": {
              "Column": {
                "Expression": { "SourceRef": { "Entity": "TABLE" } },
                "Property": "COLUMN"
              }
            },
            "Right": { "Literal": { "Value": "'ValorParaColorir'" } }
          }
        }
      }]
    }
  }
]
```

---

#### Regra 4 — Anatomia do KPI card moderno (padrão shadcn/Tremor)
**Princípio**: Todo KPI card deve responder: "O que estou vendo? É bom ou ruim? Está melhorando ou piorando?"

**5 elementos obrigatórios:**
1. **Label** — o que está sendo medido (12px, gray-500, uppercase ou regular)
2. **Valor principal** — o número em destaque (32–40px, bold)
3. **Delta vs período anterior** — `+12,3%` com seta ↑↓ e cor semântica (verde/vermelho)
4. **Período de referência** — "Jan–Dez 2024" (10px, muted)
5. **Contexto** — meta, benchmark, ou comparação

**Implementação via card nativo PBI** (limitações: sem delta inline, sem sparkline):
```json
// visual.json para card simples
{
  "visualType": "card",
  "query": {
    "queryState": {
      "Values": {
        "projections": [{
          "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Valor Total" } },
          "queryRef": "_Medidas.Valor Total"
        }]
      }
    }
  },
  "objects": {
    "labels": [{
      "properties": {
        "fontSize": { "expr": { "Literal": { "Value": "36D" } } },
        "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#09090B'" } } } } }
      }
    }],
    "categoryLabels": [{
      "properties": {
        "fontSize": { "expr": { "Literal": { "Value": "11D" } } },
        "color": { "solid": { "color": { "expr": { "Literal": { "Value": "'#71717A'" } } } } }
      }
    }]
  }
}
```

**Implementação via HTML Content visual** (completo — delta + ícone + sparkline):
```dax
measure KpiCardCompleto =
    VAR _valor = [Valor Total]
    VAR _anterior = [Valor Ano Anterior]
    VAR _delta = DIVIDE(_valor - _anterior, _anterior, 0)
    VAR _cor = IF(_delta >= 0, "#10B981", "#F43F5E")
    VAR _seta = IF(_delta >= 0, "↑", "↓")
    RETURN
    "<div style='font-family:Inter,Segoe UI,sans-serif; background:#FFFFFF; border:1px solid #E4E4E7; border-radius:12px; padding:min(20px,3vw); width:100%; height:100vh; box-sizing:border-box; display:flex; flex-direction:column; justify-content:space-between;'>" &
    "<span style='font-size:clamp(10px,2vw,12px); color:#71717A; text-transform:uppercase; letter-spacing:0.05em;'>Valor Total</span>" &
    "<div style='font-size:clamp(24px,5vw,36px); font-weight:700; color:#09090B; line-height:1;'>" & FORMAT(_valor, "R$ #,##0.0,,\" Bi\"") & "</div>" &
    "<div style='display:flex; align-items:center; gap:6px;'>" &
    "<span style='font-size:clamp(10px,2vw,13px); font-weight:600; color:" & _cor & ";'>" & _seta & " " & FORMAT(ABS(_delta), "0,0%") & "</span>" &
    "<span style='font-size:clamp(9px,1.5vw,11px); color:#71717A;'>vs ano anterior</span>" &
    "</div>" &
    "</div>"
```

---

#### Regra 5 — Typography hierarchy: 3 níveis distintos
**Princípio**: A diferença de tamanho entre níveis deve ser percebível (mínimo 4pt de diferença). Não usar mais de 2 pesos (regular + bold).

| Nível | Uso | Tamanho | Peso | Cor |
|-------|-----|---------|------|-----|
| Metric | Valor do KPI | 32–40pt | 700 | `#09090B` |
| Title | Título do visual | 13–14pt | 600 | `#09090B` |
| Label | Labels secundários, eixos | 10–11pt | 400 | `#71717A` |

**Implementação no PBIR — título do visual:**
```json
"visualContainerObjects": {
  "title": [{
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "text": { "expr": { "Literal": { "Value": "'Título do visual'" } } },
      "fontSize": { "expr": { "Literal": { "Value": "13D" } } },
      "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#09090B'" } } } } },
      "alignment": { "expr": { "Literal": { "Value": "'left'" } } }
    }
  }]
}
```

**Implementação no PBIR — label do eixo (categoryAxis):**
```json
"categoryAxis": [{
  "properties": {
    "fontSize": { "expr": { "Literal": { "Value": "10D" } } },
    "labelColor": {
      "solid": {
        "color": { "expr": { "Literal": { "Value": "'#71717A'" } } }
      }
    }
  }
}]
```

---

#### Regra 6 — Card container styling (borda, sombra, background)
**Princípio** (shadcn/Tailwind): Cards modernos usam borda sutil `1px solid` + `border-radius 8–12px` + background branco sobre fundo levemente cinza. Sombra só em hover, nunca permanente.

**Implementação no PBIR — container do visual:**
```json
"visualContainerObjects": {
  "background": [{
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "color": {
        "solid": {
          "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } }
        }
      },
      "transparency": { "expr": { "Literal": { "Value": "0D" } } }
    }
  }],
  "border": [{
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "color": {
        "solid": {
          "color": { "expr": { "Literal": { "Value": "'#E4E4E7'" } } }
        }
      },
      "radius": { "expr": { "Literal": { "Value": "12D" } } }
    }
  }],
  "title": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }]
}
```

**Página com fundo levemente cinza (padrão shadcn):**
```json
// Em page.json → objects → background
"background": [{
  "properties": {
    "color": {
      "solid": {
        "color": { "expr": { "Literal": { "Value": "'#FAFAFA'" } } }
      }
    }
  }
}]
```

---

#### Regra 7 — Data-ink ratio: remover elementos não-informativos
**Princípio** (Tufte): Maximize a proporção de pixels que comunicam dados. Remova grade desnecessária, bordas decorativas, títulos de eixo óbvios, legendas redundantes.

**O que remover e como no PBIR:**

```json
// Remover gridlines do eixo Y (values)
"valueAxis": [{
  "properties": {
    "gridlineShow": { "expr": { "Literal": { "Value": "false" } } }
  }
}]

// Remover título de eixo desnecessário
"categoryAxis": [{
  "properties": {
    "showAxisTitle": { "expr": { "Literal": { "Value": "false" } } }
  }
}]

// Remover legenda quando série única
"legend": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "false" } } }
  }
}]

// Ocultar ícones do header (hover buttons)
"visualHeader": [{
  "properties": {
    "show": { "expr": { "Literal": { "Value": "false" } } }
  }
}]
```

---

#### Regra 8 — Seleção de gráfico certa para cada pergunta
**Princípio** (Few / Knaflic): Cada tipo de pergunta tem um gráfico ideal.

| Pergunta analítica | Gráfico ideal | visualType no PBIR |
|---|---|---|
| Comparação entre categorias | Barras horizontais | `clusteredBarChart` |
| Evolução ao longo do tempo | Linha | `lineChart` |
| Proporção do total | Barras empilhadas 100% | `hundredPercentStackedColumnChart` |
| Distribuição (parte do todo) | Treemap | `treemap` |
| Correlação entre 2 variáveis | Scatter | `scatterChart` |
| Top N + concentração acumulada | Combo barras + linha | `lineClusteredColumnComboChart` |
| KPI único | Card | `card` ou `cardVisual` |
| Detalhe tabular | Tabela | `tableEx` |

> [!WARNING]
> **Evitar**: Pie charts com mais de 5 categorias, gráficos 3D, gauges decorativos (círculos com ponteiro). O PBI tem estes visuals mas eles violam princípios perceptuais básicos.

---

#### Regra 9 — Ordenação intencional dos dados
**Princípio**: Dados devem ser ordenados pelo valor (decrescente para rankings, crescente para tempo). Ordem alfabética só faz sentido em lookup tables.

**Impacto no PBIR**: A ordenação padrão não pode ser definida no JSON — precisa ser feita no Desktop. Porém, a estrutura da query influencia:

```json
// Para garantir que um eixo temporal use a ordem correta,
// mapear a coluna de data e não o texto formatado
// ❌ Errado — texto "Jan/2024" ordena alfabeticamente
"field": { "Column": { "Expression": { "SourceRef": { "Entity": "Calendario" } }, "Property": "MesAno" } }

// ✅ Certo — usar MesAnoNumero no eixo e MesAno como label
// (configurar sortByColumn no TMDL: MesAno → sortByColumn: MesAnoNumero)
```

---

#### Regra 10 — Slicers: controles, não decoração
**Princípio**: Slicers devem estar visivelmente separados dos dados (zona de controle no topo ou lateral). Usar estilo "Tile" para opções discretas (ano, trimestre). Usar "Dropdown" para listas longas.

**Tile slicer (botões) — objetos necessários:**
```json
"objects": {
  "data": [{
    "properties": {
      "mode": { "expr": { "Literal": { "Value": "'Tile'" } } }
    }
  }],
  "general": [{
    "properties": {
      "orientation": { "expr": { "Literal": { "Value": "1D" } } }
    }
  }],
  "items": [{
    "properties": {
      "fontSize": { "expr": { "Literal": { "Value": "12D" } } },
      "fontColor": {
        "solid": { "color": { "expr": { "Literal": { "Value": "'#09090B'" } } } }
      },
      "background": {
        "solid": { "color": { "expr": { "Literal": { "Value": "'#F4F4F5'" } } } }
      }
    }
  }]
}
```

**Sync entre páginas (sempre usar para filtros globais):**
```json
"syncGroup": {
  "groupName": "slicerAno",
  "fieldChanges": true,
  "filterChanges": true
}
```

---

### 29.2 Padrões de Layout Moderno — Grid 8px

**Princípio**: Design systems modernos (Tailwind, shadcn) usam grid de **8px** como unidade base. Todos os valores de position, padding e gap devem ser múltiplos de 8.

**Mapeamento para PBIR (página 1280×720):**

| Elemento | x | y | width | height | Notas |
|---|---|---|---|---|---|
| Margem lateral | 24 | — | — | — | 3 × 8px |
| Header / título | 24 | 16 | 960 | 56 | |
| Slicers (área) | 24 | 16 | 1232 | 56 | |
| KPI cards (5) | 24 + (i×248) | 88 | 240 | 96 | gap 8px |
| KPI cards (4) | 24 + (i×312) | 88 | 304 | 96 | gap 8px |
| Gráfico principal | 24 | 200 | 860 | 344 | |
| Gráfico lateral | 900 | 200 | 356 | 344 | |
| Tabela inferior | 24 | 560 | 1232 | 144 | |
| Gap entre cards | 8 | — | — | — | 1 × 8px |
| Gap entre seções | 16 | — | — | — | 2 × 8px |

---

### 29.3 Diagnóstico do Dashboard Atual — Violações e Correções

Análise baseada nas screenshots do Databrick Gov dashboard em comparação com as regras acima:

| # | Violação | Regra | Impacto | Correção no PBIR |
|---|---|---|---|---|
| 1 | Pareto com eixo X em ordem alfabética | Regra 9 (ordenação) | Alto | Filtro Top N + ordenar por Valor Total no Desktop |
| 2 | Linha do pareto constante (~96%) | Regra 4 (KPI correto) | Alto | Criar medida `% Pareto Acumulado` (DAX cumulativo) |
| 3 | Scatter com ponto único (sem Top N) | Regra 2 (visuals úteis) | Alto | Filtro Top N = 50 no Desktop |
| 4 | Tabela Top 20 sem dados (sem Top N) | Regra 2 (visuals úteis) | Alto | Filtro Top N = 20 no Desktop |
| 5 | Treemap com 25 cores distintas | Regra 3 (paleta max 7) | Médio | Agrupar categorias menores em "Outros" |
| 6 | Slicer de Ano em modo lista (legenda confusa) | Regra 10 (slicer Tile) | Médio | Mudar para modo Tile no Desktop ou via JSON |
| 7 | KPI cards sem delta vs período anterior | Regra 4 (anatomia KPI) | Médio | Adicionar medidas delta e usar HTML card |
| 8 | Cards sem borda/radius (visual antigo) | Regra 6 (card styling) | Baixo | Adicionar border + radius no visualContainerObjects |
| 9 | Títulos de eixo redundantes | Regra 7 (data-ink ratio) | Baixo | `showAxisTitle: false` nos objetos do gráfico |

---

### 29.4 Template: Visual Moderno Completo (KPI + Borda + Sem Título de Eixo)

Exemplo de `visual.json` seguindo todas as regras modernas para um card de KPI:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.6.0/schema.json",
  "name": "kpi_valor_total_moderno",
  "position": { "x": 24, "y": 88, "z": 4000, "height": 96, "width": 240, "tabOrder": 4000 },
  "visual": {
    "visualType": "card",
    "query": {
      "queryState": {
        "Values": {
          "projections": [{
            "field": {
              "Measure": {
                "Expression": { "SourceRef": { "Entity": "_Medidas" } },
                "Property": "Valor Total Formatado"
              }
            },
            "queryRef": "_Medidas.Valor Total Formatado",
            "nativeQueryRef": "Valor Total Formatado"
          }]
        }
      }
    },
    "objects": {
      "labels": [{
        "properties": {
          "fontSize": { "expr": { "Literal": { "Value": "28D" } } },
          "color": {
            "solid": { "color": { "expr": { "Literal": { "Value": "'#09090B'" } } } }
          }
        }
      }],
      "categoryLabels": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "fontSize": { "expr": { "Literal": { "Value": "11D" } } },
          "color": {
            "solid": { "color": { "expr": { "Literal": { "Value": "'#71717A'" } } } }
          }
        }
      }]
    },
    "visualContainerObjects": {
      "background": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": {
            "solid": { "color": { "expr": { "Literal": { "Value": "'#FFFFFF'" } } } }
          },
          "transparency": { "expr": { "Literal": { "Value": "0D" } } }
        }
      }],
      "border": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "color": {
            "solid": { "color": { "expr": { "Literal": { "Value": "'#E4E4E7'" } } } }
          },
          "radius": { "expr": { "Literal": { "Value": "12D" } } }
        }
      }],
      "title": [{
        "properties": {
          "show": { "expr": { "Literal": { "Value": "true" } } },
          "text": { "expr": { "Literal": { "Value": "'Valor Total'" } } },
          "fontSize": { "expr": { "Literal": { "Value": "11D" } } },
          "fontColor": {
            "solid": { "color": { "expr": { "Literal": { "Value": "'#71717A'" } } } }
          },
          "alignment": { "expr": { "Literal": { "Value": "'left'" } } }
        }
      }]
    },
    "drillFilterOtherVisuals": true
  }
}
```

---

### 29.5 Medida DAX — % Pareto Acumulado (correto)

A medida de concentração usada no `combo_pareto` deve ser **cumulativa por posição** no ranking, não um percentual fixo:

```dax
% Pareto Acumulado =
VAR ValorAtual = [Valor Total]
VAR TotalGeral = CALCULATE([Valor Total], ALL(licitacoes_2019_2024[nome]))
VAR FornecedoresComMaiorValor =
    FILTER(
        ALL(licitacoes_2019_2024[nome]),
        CALCULATE([Valor Total], ALL(licitacoes_2019_2024[nome])) >= ValorAtual
    )
VAR ValorAcumulado =
    CALCULATE([Valor Total], FornecedoresComMaiorValor)
RETURN
    DIVIDE(ValorAcumulado, TotalGeral)
```

Adicionar esta medida ao `_Medidas.tmdl` e trocar o binding do `Y2` no `combo_pareto/visual.json`:
```json
// Substituir em combo_pareto → Y2 projections
{
  "field": {
    "Measure": {
      "Expression": { "SourceRef": { "Entity": "_Medidas" } },
      "Property": "% Pareto Acumulado"
    }
  },
  "queryRef": "_Medidas.% Pareto Acumulado",
  "nativeQueryRef": "% Pareto Acumulado"
}
```

---

### 29.6 Checklist de Design Moderno — PBIR

Usar antes de finalizar qualquer página:

**Layout e hierarquia:**
- [ ] Elemento mais importante está no canto superior esquerdo (menor x, menor y)
- [ ] Máximo de 8 visuais informativos por página (não contar slicers e textboxes)
- [ ] Posições são múltiplos de 8px
- [ ] Seções visualmente separadas (grupo KPIs / grupo gráficos / grupo tabelas)

**Cores e tipografia:**
- [ ] Paleta usa no máximo 5–6 cores com papéis definidos
- [ ] Positivo = emerald `#10B981`, negativo = rose `#F43F5E`, principal = blue `#3B82F6`
- [ ] Título do visual: 13pt, `#09090B`, left-aligned
- [ ] Labels secundários: 10–11pt, `#71717A`
- [ ] Valor do KPI: mínimo 28pt, bold, `#09090B`

**Cards:**
- [ ] Background branco `#FFFFFF` com borda `#E4E4E7` e border-radius 12px
- [ ] Fundo da página em `#FAFAFA` (contraste sutil com os cards)
- [ ] KPI cards incluem label + valor + referência de período

**Gráficos:**
- [ ] Gridlines desnecessárias removidas (`gridlineShow: false`)
- [ ] Títulos de eixo removidos quando óbvios (`showAxisTitle: false`)
- [ ] Legendas removidas em séries únicas
- [ ] Ordenação por valor (não alfabética) — configurar no Desktop

**Dados:**
- [ ] Pareto ordena por valor decrescente (Top N aplicado)
- [ ] Linha do pareto usa medida cumulativa (não percentual fixo)
- [ ] Scatter usa Top N para evitar ponto único
- [ ] Tabelas têm Top N para focar no relevante

---

## 35. Bookmark JSON Schema (v2.1.0) — Documentação Completa

> [!IMPORTANT]
> Seção 30 descreve bookmarks conceitualmente. Esta seção documenta o **esquema real dos arquivos `.bookmark.json`** e `bookmarks.json`, extraídos do projeto Databricks Gov.

### bookmarks.json — Índice de Bookmarks

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
  "items": [
    { "name": "bm_abrir_gaveta" },
    { "name": "34ca1d6b40e18ee13081" }
  ]
}
```

- Localização: `Report/definition/bookmarks/bookmarks.json`
- `items` é uma array de objetos com apenas `"name"` — o nome do arquivo `.bookmark.json` (sem extensão)
- PBI Desktop usa hex IDs quando cria automaticamente; nomes legíveis como `bm_abrir_gaveta` também são aceitos e preservados

### .bookmark.json — UI Toggle (gaveta de filtros)

Bookmark **mínimo** para alternar visibilidade de elementos — sem capturar estado de slicers:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmark/2.1.0/schema.json",
  "displayName": "Abrir Gaveta de Filtros",
  "name": "bm_abrir_gaveta",
  "options": {
    "suppressData": true
  },
  "explorationState": {
    "version": "1.0",
    "activeSection": "00_visao_geral",
    "sections": {
      "00_visao_geral": {
        "visualContainers": {
          "sli_ano": {
            "singleVisual": {
              "visualType": "slicer",
              "objects": {}
            }
          },
          "sli_gaveta_label": {
            "singleVisual": {
              "visualType": "textbox",
              "objects": {}
            }
          }
        }
      }
    }
  }
}
```

### Regras do Bookmark de UI Toggle

| Propriedade | Valor | Obrigatório | Função |
|-------------|-------|-------------|--------|
| `options.suppressData` | `true` | **Sim** | Impede que o bookmark redefina os filtros ativos dos slicers |
| `activeSection` | nome da página | Sim | Página onde o bookmark atua |
| `visualContainers` | objeto vazio `{}` por visual | Sim | Lista os visuais presentes na página |
| `objects` | `{}` | Sim | Vazio = não sobrescreve estado de formatação do visual |

> [!CAUTION]
> **`suppressData: true` é obrigatório em bookmarks de UI.** Sem ele, clicar no bookmark reseta as seleções de slicer do usuário para o estado salvo no momento da criação do bookmark — comportamento indesejado em gavetas/sidebars.

> [!WARNING]
> O `visualContainers` precisa listar **todos** os visuais da página (incluindo shapes, textboxes, slicers) — mesmo que o objeto seja `{}`. Visuais omitidos podem ter comportamento imprevisível ao aplicar o bookmark.

### Workflow: Criação de Bookmark de UI via IDE

1. Criar o arquivo `.bookmark.json` na pasta `Report/definition/bookmarks/`
2. Adicionar o `name` ao array `items` em `bookmarks.json`
3. No visual que deve ser mostrado/ocultado, adicionar `visualLink` com `type: 'BookmarkNavigation'` e `bookmarkName` apontando para o bookmark

---

## 36. Propriedades de Visual Não Documentadas (Descobertas no Projeto)

### 36.1 `subTitle` em visualContainerObjects

Subtítulo abaixo do título principal do visual — ideal para disclaimers, unidade de medida, ou contexto da análise:

```json
"visualContainerObjects": {
  "title": [{
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "text": { "expr": { "Literal": { "Value": "'Título Principal'" } } },
      "fontSize": { "expr": { "Literal": { "Value": "13D" } } },
      "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#09090B'" } } } } },
      "alignment": { "expr": { "Literal": { "Value": "'left'" } } }
    }
  }],
  "subTitle": [{
    "properties": {
      "show": { "expr": { "Literal": { "Value": "true" } } },
      "text": { "expr": { "Literal": { "Value": "'Estimativa indicativa · variabilidade histórica ±53% · não usar para metas precisas'" } } },
      "fontSize": { "expr": { "Literal": { "Value": "9D" } } },
      "fontColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#71717A'" } } } } }
    }
  }]
}
```

> [!TIP]
> `subTitle` é perfeito para colocar disclaimers em gráficos de forecast, indicar a fonte dos dados, ou contextualizar a métrica sem poluir o título principal.

### 36.2 Schema v2.7.0 do visualContainer

O projeto Databricks Gov usa `visualContainer/2.7.0` (a versão documentada anteriormente era 2.6.0). A URL do schema é:

```
https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json
```

> [!NOTE]
> As propriedades são compatíveis com 2.6.0. A mudança de versão ocorre ao salvar com versões mais novas do Power BI Desktop. Sempre espelhe a versão existente no projeto — não assuma a mais nova.

### 36.3 `displayName` em Projeções (Alias de Coluna)

Para renomear uma coluna na visualização sem alterar o modelo, use `displayName` na projeção:

```json
"projections": [
  {
    "field": {
      "Column": {
        "Expression": { "SourceRef": { "Entity": "licitacoes_2019_2024" } },
        "Property": "nome"
      }
    },
    "queryRef": "licitacoes_2019_2024.nome",
    "nativeQueryRef": "nome",
    "displayName": "Fornecedor"
  }
]
```

- `displayName`: nome exibido ao usuário (cabeçalho da coluna na tabela)
- `nativeQueryRef`: nome original no modelo
- `queryRef`: referência interna usada pelo engine de query

### 36.4 `selector.data.scopeId.Measure` — Colorir Série por Medida

Diferente de colorir por valor de coluna (`scopeId.Comparison`), para colorir uma **linha específica num gráfico com múltiplas medidas** usa-se `scopeId.Measure`:

```json
// ✅ Colorir a série "Valor Total" de azul num lineChart com múltiplas medidas
"dataPoint": [
  {
    "properties": {
      "fill": {
        "solid": {
          "color": { "expr": { "Literal": { "Value": "'#3B82F6'" } } }
        }
      }
    },
    "selector": {
      "data": [{
        "scopeId": {
          "Measure": {
            "Expression": { "SourceRef": { "Entity": "_Medidas" } },
            "Property": "Valor Total"
          }
        }
      }]
    }
  },
  {
    "properties": {
      "fill": {
        "solid": {
          "color": { "expr": { "Literal": { "Value": "'#F59E0B'" } } }
        }
      }
    },
    "selector": {
      "data": [{
        "scopeId": {
          "Measure": {
            "Expression": { "SourceRef": { "Entity": "_Medidas" } },
            "Property": "Valor Previsto"
          }
        }
      }]
    }
  }
]
```

**Resumo dos tipos de `scopeId`:**

| Tipo | Quando usar |
|------|-------------|
| `scopeId.Measure` | Colorir série num gráfico com múltiplas medidas no mesmo eixo |
| `scopeId.Comparison` | Colorir barra/ponto de um valor específico de uma coluna |
| `selector.metadata` | Colorir por `queryRef` (nome da série como string) |
| Sem selector | Cor padrão da primeira série |

---

## 37. `displayFolder` em Medidas TMDL

Organiza medidas em pastas no painel de campos do Power BI Desktop:

```tmdl
table _Medidas
    lineageTag: b5f8d3e2-94a6-4cab-ae17-8e4d2a39c156

    measure 'Valor Total' = SUM('licitacoes'[valor])
        formatString: R$ #,##0.00
        displayFolder: 01 Valores Base
        lineageTag: a1000001-0000-0000-0000-000000000001

    measure 'Valor YoY %' = DIVIDE([Valor Delta YoY], [Valor Ano Anterior])
        formatString: 0.0%
        displayFolder: 03 Time Intelligence
        lineageTag: a1000001-0000-0000-0000-000000000013
```

### Convenção de nomes de displayFolder

Prefixar com número garante ordenação correta no painel (PBI ordena alfabeticamente):

| Folder | Conteúdo |
|--------|----------|
| `01 Valores Base` | SUM, COUNT, DISTINCTCOUNT simples |
| `02 Medias e Ticket` | DIVIDE, MEDIAN, AVERAGE |
| `03 Time Intelligence` | SAMEPERIODLASTYEAR, TOTALYTD, DATESINPERIOD |
| `04 Participacao` | % do total, % da categoria (ALL, ALLEXCEPT) |
| `05 Rankings` | RANKX, TOPN, SELECTEDVALUE |
| `06 Concentracao` | Top 5/10 fornecedores, HHI |
| `07 Forecast` | Medidas de previsão (IC Superior/Inferior) |

> [!TIP]
> Tabelas de medidas sem colunas (só medidas) não precisam de `partition`. O PBI as trata como "measure tables" — boas práticas é criar uma única tabela `_Medidas` para centralizar todas as métricas calculadas.

---

## 38. `tableEx` Visual — Schema Completo

`tableEx` é o `visualType` da tabela nativa do Power BI (não confundir com `matrix`).

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json",
  "name": "tbl_top10_forn",
  "position": { "x": 24, "y": 526, "z": 7000, "height": 186, "width": 1231, "tabOrder": 7000 },
  "visual": {
    "visualType": "tableEx",
    "query": {
      "queryState": {
        "Values": {
          "projections": [
            {
              "field": {
                "Column": {
                  "Expression": { "SourceRef": { "Entity": "licitacoes_2019_2024" } },
                  "Property": "nome"
                }
              },
              "queryRef": "licitacoes_2019_2024.nome",
              "nativeQueryRef": "nome",
              "displayName": "Fornecedor"
            },
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "_Medidas" } },
                  "Property": "Qtd Licitacoes"
                }
              },
              "queryRef": "_Medidas.Qtd Licitacoes",
              "nativeQueryRef": "Qtd Licitacoes"
            },
            {
              "field": {
                "Measure": {
                  "Expression": { "SourceRef": { "Entity": "_Medidas" } },
                  "Property": "Valor Total"
                }
              },
              "queryRef": "_Medidas.Valor Total",
              "nativeQueryRef": "Valor Total"
            }
          ]
        }
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

**Diferenças do tableEx vs outros visuais:**
- Role única: `Values` (todas as colunas e medidas vão na mesma projeção)
- `displayName` em cada projeção para renomear colunas
- Colunas e medidas podem ser misturadas livremente no mesmo array `Values`
- Sem `objects` é válido — usa formatação padrão do tema

---

## 39. DAX Time Intelligence — Biblioteca Completa (Projeto Databricks Gov)

Medidas validadas em produção no modelo de licitações 2019–2024:

```tmdl
// --- Comparação Período Anterior ---
measure 'Valor Ano Anterior' = CALCULATE([Valor Total], SAMEPERIODLASTYEAR(Calendario[Date]))
    formatString: R$ #,##0.00
    displayFolder: 03 Time Intelligence

measure 'Valor Delta YoY' = [Valor Total] - [Valor Ano Anterior]
    formatString: R$ #,##0.00
    displayFolder: 03 Time Intelligence

measure 'Valor YoY %' = DIVIDE([Valor Delta YoY], [Valor Ano Anterior])
    formatString: 0.0%
    displayFolder: 03 Time Intelligence

measure 'Valor Mes Anterior' = CALCULATE([Valor Total], DATEADD(Calendario[Date], -1, MONTH))
    formatString: R$ #,##0.00
    displayFolder: 03 Time Intelligence

// --- Acumulados ---
measure 'Valor YTD' = TOTALYTD([Valor Total], Calendario[Date])
    formatString: R$ #,##0.00
    displayFolder: 03 Time Intelligence

measure 'Valor YTD Ano Anterior' = CALCULATE([Valor YTD], SAMEPERIODLASTYEAR(Calendario[Date]))
    formatString: R$ #,##0.00
    displayFolder: 03 Time Intelligence

// --- Rolling Window ---
measure 'Valor 12M Moveis' = CALCULATE(
        [Valor Total],
        DATESINPERIOD(Calendario[Date], LASTDATE(Calendario[Date]), -12, MONTH)
    )
    formatString: R$ #,##0.00
    displayFolder: 03 Time Intelligence

// --- Rankings ---
measure 'Rank Categoria' = IF(
        HASONEVALUE('licitacoes'[categoria_ia]),
        RANKX(ALL('licitacoes'[categoria_ia]), [Valor Total],, DESC, DENSE)
    )
    displayFolder: 05 Rankings

measure 'Rank Fornecedor' = IF(
        HASONEVALUE('licitacoes'[nome]),
        RANKX(ALLSELECTED('licitacoes'[nome], 'licitacoes'[cpfCnpjVencedor]), [Valor Total],, DESC, DENSE)
    )
    displayFolder: 05 Rankings

// --- TOP N ---
measure 'Fornecedor #1 Nome' = CALCULATE(
        SELECTEDVALUE('licitacoes'[nome]),
        TOPN(1, VALUES('licitacoes'[nome]), [Valor Total], DESC)
    )
    displayFolder: 05 Rankings

// --- Concentração (HHI-like) ---
measure 'Valor Top 5 Fornecedores' =
        VAR Top5 = TOPN(5, VALUES('licitacoes'[cpfCnpjVencedor]), [Valor Total], DESC)
        RETURN CALCULATE([Valor Total], Top5)
    formatString: R$ #,##0.00
    displayFolder: 06 Concentracao

measure '% Concentracao Top 5 Fornecedores' = DIVIDE(
        [Valor Top 5 Fornecedores],
        CALCULATE([Valor Total], ALL('licitacoes'[cpfCnpjVencedor]))
    )
    formatString: 0.0%
    displayFolder: 06 Concentracao
```

---

## 40. Integração Forecast (Prophet) → Power BI

Padrão para integrar previsões externas (Prophet, ARIMA, etc.) como medidas DAX:

### Estrutura do Modelo

1. Exportar do Python: tabela com colunas `ds` (data), `yhat`, `yhat_lower`, `yhat_upper`
2. Carregar no modelo como tabela separada (ex: `forecast_mensal`)
3. Criar medidas DAX que retornam `BLANK()` para datas históricas e o valor de previsão para datas futuras

```tmdl
measure 'Forecast Valor' = ```
    VAR DataContexto = MAX(Calendario[Date])
    VAR UltimaDataReal = CALCULATE(MAX('licitacoes'[mes_ano]), ALL(Calendario))
    RETURN
        IF(
            DataContexto > UltimaDataReal,
            CALCULATE(
                SUM('forecast_mensal'[yhat]),
                'forecast_mensal'[ds] = DataContexto
            ),
            BLANK()
        )
    ```
    formatString: R$ #,##0.00
    displayFolder: 07 Forecast

measure 'Forecast IC Superior' = ```
    VAR DataContexto = MAX(Calendario[Date])
    VAR UltimaDataReal = CALCULATE(MAX('licitacoes'[mes_ano]), ALL(Calendario))
    RETURN
        IF(
            DataContexto > UltimaDataReal,
            CALCULATE(SUM('forecast_mensal'[yhat_upper]), 'forecast_mensal'[ds] = DataContexto),
            BLANK()
        )
    ```
    formatString: R$ #,##0.00
    displayFolder: 07 Forecast
```

### No visual.json (lineChart com 4 séries)

Adicionar todas as medidas (real + previsto + IC superior + IC inferior) no mesmo role `Y`:

```json
"Y": {
  "projections": [
    { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Valor Total" } }, "queryRef": "_Medidas.Valor Total", "nativeQueryRef": "Valor Total" },
    { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Forecast Valor" } }, "queryRef": "_Medidas.Forecast Valor", "nativeQueryRef": "Forecast Valor" },
    { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Forecast IC Superior" } }, "queryRef": "_Medidas.Forecast IC Superior", "nativeQueryRef": "Forecast IC Superior" },
    { "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "_Medidas" } }, "Property": "Forecast IC Inferior" } }, "queryRef": "_Medidas.Forecast IC Inferior", "nativeQueryRef": "Forecast IC Inferior" }
  ]
}
```

Usar `selector.data.scopeId.Measure` para colorir cada série individualmente (ver Seção 36.4).

*Seções 35–40 adicionadas em 2026-04-21 — extraídas do projeto Databricks Gov (licitações Exército Brasileiro 2019–2024)*

---

## Seção 41 — Constantes de Layout para LayoutValidator

> Extraídas empiricamente do dashboard Databrick Gov (finalizado, 3 páginas, 49 visuais).
> Base para o modelo matemático de predição de truncamento no DashForge AI.
> Data de coleta: 2026-04-23

### 41.1 Canvas (padrão observado)

```
Largura:  1280px
Altura:    720px
DisplayOption: FitToPage
Background: #FAFAFA
```

### 41.2 Escala de fontes canônica

| Papel no layout     | Tamanho | Unidade | Visual type   |
|---------------------|---------|---------|---------------|
| Título da página    | 20      | pt      | textbox       |
| Subtítulo da página | 11      | pt      | textbox       |
| Label gaveta filtro | 14      | pt      | textbox       |
| Título do visual    | 13      | D (pt)  | containerObj  |
| Subtítulo do visual | 9       | D (pt)  | containerObj  |
| Título do slicer    | 10      | D (pt)  | slicer        |
| Item do slicer      | 8       | D (pt)  | slicer        |
| Título do card (KPI)| 11      | D (pt)  | card          |
| Valor do card (KPI) | 28      | D (pt)  | card          |
| Header de tabela    | 10      | D (pt)  | tableEx       |
| Valores de tabela   | 10 ou 9 | D (pt)  | tableEx       |

### 41.3 Textbox — altura de linha

Fórmula validada com 3 casos reais:

```
line_height_px = n_lines × (font_pt × 2.2 + 4)
```

| Texto                        | font_pt | Altura real (px) | Fórmula → resultado |
|------------------------------|---------|-----------------|---------------------|
| Título página (1 linha, 20pt)| 20      | 47.88           | 1 × (20×2.2+4) = 48 |
| Subtítulo página (1 linha, 11pt)| 11   | 32.81 / 30.15   | 1 × (11×2.2+4) = 28.2 → ~30 |
| Label "FILTROS" (1 linha, 14pt)| 14    | 40.58           | 1 × (14×2.2+4) = 34.8 → ~38 |

> Precisão: ±3px. Suficiente para detectar overflow; não usar para pixel-perfect.

### 41.4 Card (KPI) — decomposição de altura

```
card_height = title_area + value_area + padding_vertical
  title_area      ≈ 28px  (para font 11pt)
  value_area      ≈ font_pt × 1.6px  (para 28pt → ~45px)
  padding_vertical ≈ 17–26px

Observado:
  90.46px = 28 + 45 + ~17   (página 0)
  99.31px = 28 + 45 + ~26   (página 2)
```

Larguras observadas: ~291–292px para 4 KPIs lado a lado em canvas 1280px.

Para predizer se o valor vai truncar no card:
```python
def card_value_fits(card_width, value_str, font_pt=28):
    avg_char_width_px = font_pt * 0.55  # Segoe UI, proporcional
    needed = len(value_str) * avg_char_width_px
    available = card_width - 24  # padding horizontal total estimado
    return needed <= available
```

### 41.5 TableEx — constantes de paginação

Validado com cross-check nos 3 casos reais (ver cálculo abaixo):

```
header_height    ≈ 43px         (linha de header, independente da fonte)
row_height_10pt  ≈ 24px         → 10 × 2.2 + 2 = 24
row_height_9pt   ≈ 22px         → 9 × 2.2 + 2 = 21.8 ≈ 22
row_height_fórmula: row_h = font_pt × 2.2 + 2
column_overhead  ≈ 30px         (bordas + área de scroll horizontal)
```

**Validação cruzada:**

| Tabela              | Altura total | Font | Header | Fórmula rows                    | Resultado |
|---------------------|-------------|------|--------|---------------------------------|-----------|
| tbl_top10_forn      | 186.21px    | 10pt | 43px   | (186.21-43)/24 = 5.97          | ~6 linhas |
| tbl_cat_detalhe     | 237.64px    | 10pt | 43px   | (237.64-43)/24 = 8.10          | ~8 linhas |
| tbl_top20_forn      | 483.25px    | 9pt  | 43px   | (483.25-43)/22 = **20.01**     | ~20 linhas ✓ perfeito |

Fórmula para predição de linhas visíveis:
```python
def table_rows_visible(height, font_pt=10):
    header = 43
    row_h = font_pt * 2.2 + 2
    return int((height - header) / row_h)

def table_cols_overflow(col_widths, visual_width):
    overhead = 30
    return sum(col_widths) > (visual_width - overhead)
```

### 41.6 Slicer dropdown — dimensões padrão

Consistente nas 6 instâncias (2 slicers × 3 páginas):

```
width:  247.55px
height:  90.76px
font título: 10pt
font items:   8pt
border radius: 8px
border color: #E4E4E7
```

### 41.7 Gaveta de filtros (VisualGroup outspacePane)

```
width:  ~285px  (284.55–284.88)
height: ~273px  (272.62–273.09)
posição X: ~976px  (canvas 1280px → fica quase no limite direito)
posição Y:  ~16–26px
border radius: 30px (shape interno)
default: isHidden = true
```

### 41.8 Botões de navegação (imagem com PageNavigation)

```
width:  40px
height: 40px
posição Y: ~26px (alinhado ao topo da página)
posição X arrow-right: ~1216px (quase na borda direita)
posição X arrow-left:  ~1100–1152px (à esquerda do arrow-right)
posição X filtro (funnel): entre arrow-left e arrow-right
```

### 41.9 Container visual padrão (background + border)

Padrão observado em todos os visuais de dados (cards, gráficos, tabelas):

```json
"background": { "show": true, "color": "#FFFFFF", "transparency": 0 },
"border":     { "show": true, "color": "#E4E4E7", "radius": 12 }
```

Gaveta de filtros usa `"radius": 30` no shape subjacente.

### 41.10 Margens de posicionamento dos visuais

Observado consistentemente entre os visuais principais e as bordas do canvas:

```
margin_left:   ~24px  (X inicial dos visuais de conteúdo)
margin_top:    ~96px  (Y inicial abaixo do header: títulos ~16-87px + cards)
gap_entre_visuais: ~0px (visuais tocam uns nos outros, sem gap visível)
```

*Seção 41 adicionada em 2026-04-23 — constantes extraídas do Databrick Gov, base para LayoutValidator do DashForge AI*

---

## Seção 42 — Constantes de Layout: CONTRATAÇÕES - DGT

> Segundo dashboard analisado. Canvas diferente, visual types novos, escala de fontes maior.
> Data de coleta: 2026-04-23

### 42.1 Canvas — segundo padrão observado

```
Página 1 e 3: 1920 × 1080px  (Full HD — alternativa comum ao 1280×720)
Página 2:     1920 × 1280px  (Full HD vertical expandido)
```

O LayoutValidator precisa parametrizar o canvas; não assumir 1280×720 como único padrão.

### 42.2 Fontes não escalam automaticamente com o canvas

O designer escolhe fontes maiores manualmente em canvases maiores. Comparativo:

| Papel                  | 1280×720 (Databrick Gov) | 1920×1080 (DGT) | Fator |
|------------------------|--------------------------|-----------------|-------|
| Valor do card KPI      | 28pt                     | 30–35pt         | ~1.2× |
| Título do card KPI     | 11pt                     | 22–25pt         | ~2.1× |
| Header de tabela       | 10pt                     | 15pt            | 1.5×  |
| Valores de tabela      | 9–10pt                   | 13pt            | 1.4×  |
| Título do slicer       | 10pt                     | 20pt            | 2.0×  |
| Item do slicer         | 8pt                      | 18pt            | 2.25× |
| Label em gráfico       | n/d                      | 12–22pt         | —     |
| Legenda                | n/d                      | 18–26pt         | —     |

**Implicação para o DashForge AI:** o RequirementsAgent precisa saber o canvas alvo antes de decidir as fontes. Não existe "fonte padrão universal" — depende do canvas.

Regra heurística observada: `font_pt_sugerido ≈ font_pt_base_1280 × (canvas_width / 1280) × 0.85`

### 42.3 Card KPI — dimensões no canvas 1920×1080

```
width:  370–421px   (vs 292px no canvas 1280)
height: 122–158px   (vs 90–99px no canvas 1280)
value font:  30–35pt (título + valor maior = card mais alto)
title font:  22–25pt
```

Validação da fórmula com card de 125.78px (title 25pt, value 35pt):
```
title_area  ≈ 25 × 2.2 + 4 = 59px
value_area  ≈ 35 × 1.6     = 56px
padding     ≈ 10px
total       = 125px ≈ 125.78 ✓
```
A fórmula da Seção 41.4 se mantém válida com fontes maiores.

### 42.4 TableEx — header height varia com a fonte

Tabela observada: 1906px × 348.31px, 14 colunas, header font 15pt, values font 13pt.

```
row_h (13pt) = 13 × 2.2 + 2 = 30.6px
header_h (15pt font) ≈ 15 × 2.8 + 2 = 44px
rows_visible = (348.31 - 44) / 30.6 = 9.94 ≈ 10 linhas ✓
```

Revisão da fórmula de header_height (era fixo em 43px):
```
header_h = max(43, font_pt_header × 2.8 + 2)
```
Para 10pt: max(43, 30) = 43px  → igual ao anterior ✓
Para 15pt: max(43, 44) = 44px  → levemente maior ✓

### 42.5 Novos visual types identificados

#### clusteredColumnChart (barras verticais)
```
Dimensões observadas:
  1538.38 × 512.79px  (página 1, 1920 canvas)
  1467.60 × 313.88px  (página 2, 1920 canvas)

Legenda: pode ser Left (consome largura, não altura)
Labels: show=true, fontSize 12–22pt
categoryAxis: fontSize 15–18pt
valueAxis: pode ser show=false (sem eixo Y visível)
```

Diferença crítica de orientação vs clusteredBarChart:
- `clusteredBarChart`: categorias no eixo Y (horizontal) → rótulos à esquerda consomem **largura**
- `clusteredColumnChart`: categorias no eixo X (vertical) → rótulos embaixo podem **rotar** quando há muitas categorias

#### stackedAreaChart
```
Dimensões observadas: 1472 × 361.95px
Legenda: Left
Labels: show=true, fontSize 22pt
categoryAxis: fontSize 16pt, axisType=Categorical
```

#### pageNavigator
```
Dimensões observadas: 808.74 × 59.38px
Button fontSize: 18pt (default), 15pt (selected)
Shape: rectangleRounded, roundEdge=5
```
Não contribui para truncamento de dados — decorativo.

### 42.6 Legenda na posição Left

Quando `legend.position = Left`, a legenda consome **largura** do gráfico, não altura.
Estimativa de largura reservada: `max_series_label_length × avg_char_width + ícone (~20px)`

Para detectar overflow de legenda lateral:
```python
def legend_left_width(series_labels, font_pt=18):
    avg_char_w = font_pt * 0.55
    longest = max(len(s) for s in series_labels)
    return longest * avg_char_w + 20  # 20px para o ícone de cor

def chart_area_width(visual_width, legend_labels, font_pt=18, position='Left'):
    if position in ('Left', 'Right'):
        return visual_width - legend_left_width(legend_labels, font_pt) - 16
    return visual_width  # Top/Bottom não consome largura
```

### 42.7 Shapes maiores que o canvas

O background shape tinha `width=2597.99, height=2876.35` — bem maior que o canvas 1920×1080. O Power BI clipa automaticamente. Não gera erro nem afeta outros visuais.

### 42.8 Slicer — dimensões no canvas 1920

```
Largura: 262–554px (mais variação que no canvas 1280)
Altura:   74–102px
Title fontSize: 20pt
Items fontSize: 18pt
```

*Seção 42 adicionada em 2026-04-23 — extraída do dashboard CONTRATAÇÕES - DGT (3 páginas, canvas 1920×1080/1280)*

---

## Seção 43 — Constantes de Layout: Relatório Pagamentos + ESTRATÉGICO - PROJETOS + Elos Minuta

> Três dashboards reais analisados em paralelo. Foco em: novos canvas sizes, novos visual types, distinção card vs cardVisual.
> Data de coleta: 2026-04-23

### 43.1 Catálogo completo de canvas sizes observados

| Dimensão          | Dashboard de origem               | Uso típico                     |
|-------------------|-----------------------------------|--------------------------------|
| 1280 × 720        | Databrick Gov, Rel. Pagamentos    | Web / apresentação padrão      |
| 1800 × 900        | Elos Minuta (páginas ativas)      | Monitor widescreen             |
| 1920 × 1080       | CONTRATAÇÕES - DGT                | Full HD                        |
| 1920 × 1280       | DGT página 2                      | Full HD vertical expandido     |
| 2200 × 1200       | ESTRATÉGICO - PROJETOS            | Ultra-wide corporativo         |
| 1400 × 1050       | ESTRATÉGICO página 2              | 4:3 expandido                  |
| 320 × 240         | Elos Minuta (tooltip)             | Página de tooltip              |

**Tooltip page**: `DisplayOption: Tooltip` + dimensões 320×240 + `HiddenInViewMode: true`. O Power BI renderiza essa página como popup ao passar o cursor sobre um visual. O LayoutValidator deve reconhecer e ignorar para cálculos de layout normais.

### 43.2 card (clássico) vs cardVisual (moderno) — distinção crítica

São dois visual types distintos com comportamentos e propriedades diferentes:

| Propriedade           | `card` (clássico)         | `cardVisual` (moderno)              |
|-----------------------|---------------------------|-------------------------------------|
| Visual type no JSON   | `"card"`                  | `"cardVisual"`                      |
| Suporte multi-métrica | Não (1 por visual)        | Sim (N colunas em 1 visual)         |
| Layout interno        | Simples: título + valor   | Tiles: cada métrica é um "tile"     |
| accentBar             | Não                       | Sim (barra colorida lateral)        |
| Dimensões típicas     | ~290×90px (1280 canvas)   | Muito variável — de 240×64 a 1704×168 |
| Propriedade de valor  | `labels.fontSize`         | `value.fontSize` / `calloutValue`   |

**cardVisual multi-coluna** (Elos Minuta — 5 métricas):
```
Dimensões: 1704.91 × 168.45px  (canvas 1800)
Colunas:   5 tiles lado a lado
value font: 22D  |  label font: 16D
Largura por tile: 1704.91 / 5 ≈ 341px
```

**cardVisual compacto** (Relatório Pagamentos — 1 métrica):
```
Dimensões: 240 × 64px  (canvas 1280)
value font: 28D
```

**cardVisual detalhe** (ESTRATÉGICO — modo painel):
```
Dimensões: 330 × 238px  |  329 × 252px
value font: 10D  |  label font: 14D
Suporte a accentBar lateral
```

### 43.3 Novos visual types — catálogo completo

| Visual type | Dashboard | Status para LayoutValidator |
|---|---|---|
| `donutChart` | Elos Minuta | Preditível — legenda + labels |
| `pivotTable` | Rel. Pagamentos, Elos Minuta | Parcialmente preditível |
| `actionButton` | Todos os 3 | Decorativo — não trunca dados |
| `azureMap` | Elos Minuta | Opaco — canvas fixo, sem texto |
| `FlowVisual_*` | Elos Minuta, Rel. Pagamentos | Decorativo — só botão |
| `powerBIGanttChart*` | ESTRATÉGICO | Opaco — visual de marketplace |
| `pageNavigator` | Rel. Pagamentos | Decorativo |

#### donutChart
```
Exemplo: 417.73 × 310.16px (canvas 1800)
Legenda: position=Top, fontSize=10D
Labels (callout): fontSize=11D
```
Quando legenda está Top/Bottom, desconta altura:
`plot_height = visual_height - legend_height`
`legend_height ≈ n_series × (font_pt × 2.0 + 4) + 8px`

#### pivotTable
```
Relatório Pagamentos: 1136.67 × 561.67px, columnAdjustment=growToFit
Elos Minuta:           593.13 × 647.71px, columnWidths explícitas (216D, 434D)
values fontSize:  10–12D
headers fontSize: 10–12D
```
Mesmas fórmulas de row_height e header_height do tableEx (Seção 41.5).
Diferença: `growToFit` distribui o espaço igualmente quando sem columnWidths fixas.

#### actionButton — dimensões por papel
```
Botão "fechar" / close (X):     ~58 × 55px, text 'X', font 20D
Botão "histórico" / toggle (H): ~48 × 49px, text 'H', shape oval, font 12D
Botão de navegação (voltar):    ~199 × 40px, font implícita (sem D explícito)
```
Não contribui para truncamento de dados — ignorar no LayoutValidator.

### 43.4 Escala de fontes por canvas (tabela consolidada 5 dashboards)

| Papel                | 1280×720 | 1800×900 | 1920×1080 | 2200×1200 |
|----------------------|----------|----------|-----------|-----------|
| Valor card (KPI)     | 28pt     | 22–25pt  | 30–35pt   | 24–36pt   |
| Título card          | 11pt     | 15pt     | 22–25pt   | 12–16pt   |
| Header tabela        | 10pt     | 12pt     | 15pt      | 10–12pt   |
| Valores tabela       | 9–10pt   | 12pt     | 13pt      | 10pt      |
| Título slicer        | 10pt     | 14pt     | 20pt      | 16pt      |
| Item slicer          | 8pt      | 14pt     | 18pt      | 16pt      |
| Label gráfico        | n/d      | 11–12pt  | 12–22pt   | 18pt      |

**Conclusão:** não há relação linear simples entre canvas size e font size — o designer escolhe. O RequirementsAgent deve perguntar o canvas target e sugerir fontes baseado em benchmark, não em fórmula rígida.

### 43.5 Padrão de menu toggle via visual groups

Observado no Relatório Pagamentos — alternativa ao bookmarks outspacePane do Databrick Gov:

```
VisualGroup "Menu Escondido"
  x=0, y=96, width=79.65, height=624.22
  GroupMode: ScaleMode
  isHidden: false  ← visível por padrão (menu recolhido)

VisualGroup "Menu Exibido"
  x=0, y=0, width=1280, height=721.04
  GroupMode: ScaleMode
  isHidden: true   ← oculto por padrão
```

Dois grupos se alternam via bookmark — mesma lógica do outspacePane mas implementada como grupos sobrepostos em vez de grupo que desliza para fora do canvas.

### 43.6 Conditional formatting em tabelas (tableEx/pivotTable)

Elos Minuta usou row-level conditional formatting via `selector.data.scopeId.Column`:
```
Status_Validacao = 'Divergência'       → background #D64550 (vermelho)
Status_Validacao = 'Dados Conciliados' → background #049464 (verde)
```
Formato idêntico ao da Seção 36.3 (cor por série em lineChart), mas aplicado em `background` de células de tabela. O LayoutValidator não precisa considerar isso — não afeta dimensões.

### 43.7 Tooltip page — identificação e tratamento

```json
// page.json de página tooltip
"displayOption": "Tooltip",
"visibility": "HiddenInViewMode",
// Dimensões padrão:
"width": 320,
"height": 240
```
O LayoutValidator deve detectar `displayOption = "Tooltip"` e pular a página — as fórmulas de layout não se aplicam ao contexto de tooltip.

*Seção 43 adicionada em 2026-04-23 — extraída de: Relatório Pagamentos (5 págs, 1280×720), ESTRATÉGICO - PROJETOS (4 págs, 2200×1200/1400×1050), Elos Minuta (8 págs, 1800×900 + tooltip)*

---

## Seção 44 — Catálogo de Padrões de Slicer (Segmentação de Dados)

> Extraído de 54+ slicers reais em 5 dashboards. Data: 2026-04-23

### 44.1 Distribuição por modo
- **Dropdown**: 96% dos casos — modo padrão absoluto
- **Between**: apenas para ranges de data (DataAlvará, etc.)
- **Tile / List / Relative Date**: não observados nesses dashboards

### 44.2 Configurações canônicas

```json
// Dropdown padrão mínimo
{
  "visualType": "slicer",
  "singleVisual": {
    "objects": {
      "data": [{ "properties": { "mode": { "expr": { "Literal": { "Value": "'Dropdown'" } } } } }],
      "header": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
      "items": [{ "properties": { "textSize": { "expr": { "Literal": { "Value": "12D" } } } } }]
    }
  }
}
```

```json
// Between (intervalo de datas)
{
  "data": [{ "properties": { "mode": { "expr": { "Literal": { "Value": "'Between'" } } } }],
  "slider": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }],
  "date": [{ "properties": { "textSize": { "expr": { "Literal": { "Value": "15D" } } } } }]
}
```

### 44.3 Recursos avançados observados

**Seleção invertida** (filtro "todos exceto"):
```json
"filterConfig": [{ "properties": {
  "isInvertedSelectionMode": { "expr": { "Literal": { "Value": "true" } } }
} }]
```
Usado em: ESTRATÉGICO (Projeto, Fornecedor), Databrick Gov (categoria_ia).

**Seleção única obrigatória**:
```json
"general": [{ "properties": {
  "strictSingleSelect": { "expr": { "Literal": { "Value": "true" } } }
} }]
```

**Sincronização entre páginas**:
```json
// Em syncSlicers.json da página ou diretamente no visual
"syncConfig": { "group": "NomeDoGrupo", "filterChanges": true, "fieldChanges": true }
```
SyncGroups observados: `"FiltroAno"` (Databrick Gov), `"Projeto"` e `"Fornecedores"` (ESTRATÉGICO).

### 44.4 Dimensões por canvas

| Canvas      | Largura típica | Altura típica | font items | font título |
|-------------|----------------|---------------|------------|-------------|
| 1280×720    | 247px          | 90px          | 8–10D      | 10D         |
| 1800×900    | 230px          | 107px         | 14D        | 14D         |
| 1920×1080   | 262–554px      | 75–102px      | 18D        | 20D         |
| 2200×1200   | 250px          | 93–96px       | 16D        | 16D         |

### 44.5 Padrão de título: header oculto + visualContainerObjects.title

Em 100% dos casos observados, o header interno do slicer fica oculto e o título vem do container:
```json
// Dentro do visual
"header": [{ "properties": { "show": { "expr": { "Literal": { "Value": "false" } } } } }]

// Em visualContainerObjects
"title": [{ "properties": {
  "show":      { "expr": { "Literal": { "Value": "true" } } },
  "text":      { "expr": { "Literal": { "Value": "'Mês'" } } },
  "fontSize":  { "expr": { "Literal": { "Value": "10D" } } },
  "bold":      { "expr": { "Literal": { "Value": "false" } } },
  "alignment": { "expr": { "Literal": { "Value": "'left'" } } }
} }]
```

---

## Seção 45 — Padrões de Interatividade (Bookmarks, Botões, Gavetas)

> Extraído de 30+ bookmarks e 50+ visualLinks em 5 dashboards. Data: 2026-04-23

### 45.1 Três padrões de gaveta observados

#### Padrão A — Toggle de VisualGroup (Databrick Gov)
O grupo de visuais sai/entra do canvas via `isHidden` em bookmark:
```
BookmarkA (gaveta aberta):  VisualGroup.isHidden = false
BookmarkB (gaveta fechada): VisualGroup.isHidden = true
Botão funil → BookmarkA
Botão X     → BookmarkB
Botão funil-x → ClearAllSlicers
```
Os slicers e labels ficam dentro do VisualGroup. Quando oculto, o grupo desliza para fora do canvas (`x > canvas_width`).

#### Padrão B — OutspacePane expand/collapse (Contratações DGT)
O painel lateral nativo do Power BI é expandido/contraído via bookmark:
```
BookmarkA (abrir):  outspacePane.expanded = true
BookmarkB (fechar): outspacePane.expanded = false
BookmarkC (limpar): suppressData=true, suppressDisplay=true → ClearAllSlicers sem mudar estado
```
3 botões dedicados: abrir, fechar, limpar (ícones distintos).

#### Padrão C — Visual Groups sobrepostos (Relatório Pagamentos)
Dois grupos ocupam a mesma área; bookmarks alternam qual está visível:
```
VisualGroup "Menu Escondido" → isHidden: false (padrão)
VisualGroup "Menu Exibido"   → isHidden: true  (padrão)
Bookmark alterna os dois estados simultaneamente
```

### 45.2 Estrutura de bookmark (campos obrigatórios)

```json
{
  "name": "id_unico",
  "displayName": "Nome Legível",
  "suppressData": true,
  "explorationState": {
    "version": "1.0",
    "activeSection": "page-id",
    "sections": {
      "page-id": {
        "visualContainers": {
          "visual-name": {
            "singleVisual": {
              "visualType": "slicer",
              "objects": {}
            }
          }
        }
      }
    }
  }
}
```

`suppressData: true` = bookmark só muda estado visual (show/hide), não dados.
`suppressActiveSection: true` = bookmark afeta todas as páginas, não só a ativa.
`suppressDisplay: true` = bookmark não muda visibilidade de visuais (só dados/filtros).

### 45.3 Tipos de visualLink (botões)

| Tipo              | Uso observado                    | Visual type que usa    |
|-------------------|----------------------------------|------------------------|
| `Bookmark`        | Abrir/fechar gaveta, navegação   | image, actionButton    |
| `ClearAllSlicers` | Resetar todos os filtros         | image                  |
| `PageNavigation`  | Navegar para outra página        | image, actionButton    |
| `URL`             | Não observado                    | —                      |

```json
// Imagem com visualLink para bookmark
"visualLink": {
  "show": { "expr": { "Literal": { "Value": "true" } } },
  "type": { "expr": { "Literal": { "Value": "'Bookmark'" } } },
  "bookmark": { "expr": { "Literal": { "Value": "'id_do_bookmark'" } } }
}

// ActionButton com texto
"visualType": "actionButton",
"singleVisual": {
  "objects": {
    "text": [{ "properties": {
      "text":      { "expr": { "Literal": { "Value": "'X'" } } },
      "fontSize":  { "expr": { "Literal": { "Value": "22D" } } }
    } }],
    "icon": [{ "properties": { "iconType": { "expr": { "Literal": { "Value": "'Blank'" } } } } }]
  },
  "vcObjects": {
    "visualLink": [{ "properties": {
      "type":     { "expr": { "Literal": { "Value": "'Bookmark'" } } },
      "bookmark": { "expr": { "Literal": { "Value": "'id_bookmark'" } } }
    } }]
  }
}
```

### 45.4 Configurações globais de report.json

Padrão observado em todos os dashboards:
```json
{
  "filterPaneHiddenInEditMode": true,
  "defaultDrillFilterOtherVisuals": true,
  "outspacePane": { "expanded": false }
}
```

### 45.5 Ícones de controle mais usados (StaticResources)

| Função        | Ícone comum             | Tipo de link     |
|---------------|-------------------------|------------------|
| Abrir filtros | funnel.svg, filter.png  | Bookmark (abrir) |
| Fechar painel | x.svg, Bot_o_fechar.png | Bookmark (fechar)|
| Limpar filtros| funnel-x.svg, clear-filter.png | ClearAllSlicers / Bookmark |
| Navegar →     | arrow-right.svg         | PageNavigation   |
| Navegar ←     | arrow-left.svg          | PageNavigation   |

---

## Seção 46 — Padrões de Medidas DAX

> Extraído dos 5 semantic models. Data: 2026-04-23

### 46.1 Organização canônica (Databrick Gov como referência)

Databrick Gov é o único com `displayFolder` definidos. Serve de template para o DashForge AI:

| Pasta | Padrão DAX principal |
|---|---|
| `01 Valores Base` | `SUM`, `DISTINCTCOUNT` |
| `02 Médias` | `DIVIDE([A], [B])` com proteção BLANK |
| `03 Time Intelligence` | `SAMEPERIODLASTYEAR`, `DATEADD`, `TOTALYTD`, `DATESINPERIOD` |
| `04 Participação` | `CALCULATE([M], ALLEXCEPT(T, T[col]))` |
| `05 Rankings` | `IF(HASONEVALUE(T[col]), RANKX(...))` |
| `06 Concentração` | `TOPN + VAR` complexas |
| `07 Qualidade` | `FILTER + COUNTROWS`, `ISBLANK` |
| `08 Auxiliares` | Formatação texto/cor |
| `09 Forecast` | Regressão, DATESINPERIOD |

### 46.2 Padrões críticos de protecão

```dax
// Proteção de divisão por zero
Ticket Medio = DIVIDE([Valor Total], [Qtd Licitacoes])

// Proteção de contexto múltiplo em ranking
Rank Fornecedor = IF(HASONEVALUE(T[nome]), RANKX(ALL(T[nome]), [Valor Total]))

// Garantir retorno numérico mesmo com CALCULATE vazio
Projetos Em Risco = CALCULATE([Total Ativos], T[Status] = "Em risco") + 0

// Tolerância em reconciliação
Status_Validacao = IF(ABS([Calculado] - [Real]) <= 0.01, "✅ Conciliado", "❌ Divergência")
```

### 46.3 Medidas de controle visual (macros para mostrar/ocultar)

Estas medidas são aplicadas como filtros de nível visual para mostrar/ocultar visuais dinamicamente:

```dax
// Mostrar painel de detalhe somente quando um item é filtrado
ExibirHistorico = IF(ISFILTERED(Projetos[Projeto]), 1, 0)
// Aplicar no visual como filtro: ExibirHistorico = 1

// Mostrar somente linhas com problema
Filtro Linhas com Problema =
    VAR TemAlvara = ISBLANK([AlvaraId]) || [AlvaraId] = ""
    VAR TemValorErrado = [Valor] <= 0
    RETURN IF(TemAlvara || TemValorErrado, 1, 0)
// Aplicar no visual como filtro: Filtro Linhas com Problema = 1
```

### 46.4 Medidas auxiliares de cor (formatação condicional)

```dax
// Retorna HEX diretamente para usar em conditional formatting
Cor YoY =
    SWITCH(
        TRUE(),
        [Valor YoY %] > 0,    "#16A34A",  // verde
        [Valor YoY %] < 0,    "#DC2626",  // vermelho
        "#71717A"                           // cinza (neutro)
    )
```

### 46.5 Medidas de texto dinâmico

Usadas em `cardVisual` ou `textbox` para títulos e legendas que refletem filtros ativos:

```dax
// Período selecionado
Periodo Selecionado =
    VAR MinD = MIN(T[PrimeiroDiaMes])
    VAR MaxD = MAX(T[UltimoDiaMes])
    RETURN IF(
        ISBLANK(MinD), "Período: (sem filtro)",
        "Período: " & FORMAT(MinD, "dd/mm/yyyy") & " a " & FORMAT(MaxD, "dd/mm/yyyy")
    )

// Timestamp com fuso (UTC-3)
Ultima Atualizacao =
    "Atualizado em " & FORMAT(NOW() - TIME(3,0,0), "dd/MM/yyyy") &
    " às " & FORMAT(NOW() - TIME(3,0,0), "HH:mm")

// Valor formatado para KPI (sem notação científica)
Valor Total Formatado =
    VAR v = [Valor Total]
    RETURN SWITCH(TRUE(),
        v >= 1e9, FORMAT(v/1e9, "0.0") & " bi",
        v >= 1e6, FORMAT(v/1e6, "0.0") & " mi",
        v >= 1e3, FORMAT(v/1e3, "0.0") & " mil",
        FORMAT(v, "#,##0"))

// Título dinâmico (mostra item selecionado)
Titulo Projeto = SELECTEDVALUE(Projetos[Projeto], "Todos os Projetos")
```

### 46.6 Colunas calculadas (padrões recorrentes)

```dax
// Status derivado com lógica temporal
StatusCalculado =
    VAR Hoje = TODAY()
    RETURN SWITCH(TRUE(),
        [Status] IN {"CANCELADO", "SUSPENSO"}, [Status],
        [Status] = "ENTREGUE", "ENTREGUE",
        Hoje > [DataEntrega], "ATRASADO",
        [Status])

// Normalização de percentual (aceita 0.87 ou 87)
PctConcluido =
    VAR Bruto = IF(ISBLANK([pct_campo]), [Progresso], [pct_campo])
    VAR Num = IFERROR(VALUE(Bruto), 0)
    RETURN TRUNC(IF(Num > 1, Num / 100, Num), 4)

// Classificação de domínio de texto
DominioEmail =
    VAR e = LOWER([Email])
    RETURN IF(ISBLANK(e), "Sem email",
        IF(RIGHT(e, 12) = "@tjba.jus.br", "Interno", "Externo"))
```

### 46.7 Tabela de lookup criada em DAX (DATATABLE)

```dax
// Tabela estática para filtro de status visual
FiltroStatus = DATATABLE("Status", STRING, {{"✅"}, {"❌"}})
```
Usada como tabela auxiliar para slicers ou para cruzamento com medida de status.

---

## Seção 47 — Requisitos de Capacidade do DashForge AI

> O que o sistema precisa gerar para atingir a qualidade dos 5 dashboards reais. Data: 2026-04-23

### 47.1 Camadas de geração requeridas

```
Camada 1 — Estrutura de dados (RequirementsAgent coleta)
  ├── Tabelas e campos disponíveis
  ├── Relações (many-to-one, filtro direction)
  └── Tipo de dado por campo (data, texto, número, %)

Camada 2 — Medidas DAX (DAXAgent gera)
  ├── Valores Base: SUM / DISTINCTCOUNT por campo numérico
  ├── Médias: DIVIDE com proteção
  ├── Time Intelligence: somente se houver tabela de calendário
  ├── Participação: % do total com ALLEXCEPT
  ├── Rankings: RANKX com guarda HASONEVALUE
  ├── Auxiliares: cor (Cor YoY) e texto formatado
  └── Controle visual: IF(ISFILTERED, 1, 0) para painel detalhe

Camada 3 — Visuais e layout (PBIRGenerator gera)
  ├── Cards KPI: card ou cardVisual multi-coluna
  ├── Gráficos: lineChart, clusteredBarChart, clusteredColumnChart, donutChart
  ├── Tabelas: tableEx com columnWidths e sort
  ├── Slicers: dropdown padrão + Between para data
  └── Navegação: image com PageNavigation entre páginas

Camada 4 — Interatividade (BookmarkAgent gera)
  ├── Gaveta de filtros: VisualGroup + 2 bookmarks + 3 botões
  ├── ClearAllSlicers: 1 imagem com funnel-x
  └── Controle de painel detalhe: ExibirHistorico via filtro visual
```

### 47.2 Funcionalidades mínimas por tier de complexidade

**Tier 1 — Dashboard básico (MVP do DashForge AI)**
- Cards KPI + 1 gráfico de linha temporal + 1 tabela
- Slicers dropdown sem sync
- Sem bookmarks / sem gaveta
- Medidas: Valores Base + Médias

**Tier 2 — Dashboard intermediário**
- Múltiplas páginas com navegação (arrow-right/left)
- Gaveta de filtros com bookmarks (Padrão A ou B)
- ClearAllSlicers
- Slicer sync entre páginas
- Medidas: + Time Intelligence + Participação + Rankings

**Tier 3 — Dashboard avançado**
- 4+ páginas + tooltip page
- cardVisual multi-coluna
- Painel de detalhe com ExibirHistorico (controle visual via DAX)
- Formatação condicional com medida de cor
- Medidas de texto dinâmico (títulos, timestamps)
- Medidas de qualidade de dados

### 47.3 O que NÃO é necessário gerar (complexidade não justificada)

- Visuais de marketplace (Gantt, FlowVisual) — opaco, não controlável
- azureMap — requer credenciais Azure, fora do escopo
- Colunas calculadas complexas (StatusCalculado, PctConcluido) — gerar só quando o usuário pedir
- DATATABLE de lookup — gerar só para casos de filtro de status dinâmico
- Bookmarks com `suppressActiveSection` — apenas Padrão A/B são suficientes

*Seções 44–47 adicionadas em 2026-04-23 — síntese de 54+ slicers, 30+ bookmarks, 5 semantic models*

---

## Seção 48 — Novos Visual Types: Governança BI e projeto.pbip

> Descobertas dos dois dashboards finais. Data: 2026-04-23

### 48.1 Canvas sizes adicionais

| Dimensão       | Dashboard          |
|----------------|--------------------|
| 1710 × 800     | Governança BI (1)  |
| 1678 × 799     | Governança BI pág 2|

### 48.2 lineClusteredColumnComboChart (combo coluna + linha)

```
Exemplo: 1252.31 × 508.33px (canvas 1710×800)
Y (coluna): métrica principal (ex: Disponibilidade %)
Y2 (linha): meta ou comparativo (ex: Meta de Disponibilidade)
Labels: fontSize=11pt, bold=true, position=OutsideEnd
enableDetailDataLabel: true
```
Ideal para mostrar realizado vs meta ao longo do tempo. Compartilha eixo X com dois eixos Y independentes.

### 48.3 Gauge customizado de marketplace

Visual type: `dg5AAA90EFEFE747CB9357C4FC19B85A58`
Campos obrigatórios: `pointerValue`, `min`, `max`, `redStart`, `redEnd`, `yellowStart`, `yellowEnd`
```dax
-- Constantes de meta para o gauge
Maximo      = 1
Minimo      = 0
targetstart = 0.9   -- início da zona verde
targetend   = 1
mediastart  = 0.7   -- início da zona amarela
mediaend    = 0.9
Meta        = 0.9
Meta_legenda = "Meta: 90%"
```
**Importante**: opaco para o LayoutValidator — não gerar via JSON diretamente, usar apenas se o custom visual estiver instalado.

### 48.4 Deneb / Vega-Lite (projeto.pbip)

Visual type: `deneb7E15AEF80B9E4D4F8E12924291ECE89A`

```json
// Configuração mínima no visual.json
{
  "visualType": "deneb7E15AEF80B9E4D4F8E12924291ECE89A",
  "singleVisual": {
    "objects": {
      "vega": [{
        "properties": {
          "jsonSpec": { "expr": { "Literal": { "Value": "'{ ... spec Vega-Lite ... }'" } } },
          "provider":  { "expr": { "Literal": { "Value": "'vegaLite'" } } },
          "themeMode": { "expr": { "Literal": { "Value": "'light'" } } }
        }
      }]
    }
  }
}
```
Permite criar qualquer tipo de chart via JSON declarativo. Não preditível pelo LayoutValidator (spec define o espaço internamente).

### 48.5 htmlContent (projeto.pbip)

Visual type: `htmlContent443BE3AD55E043BF878BED274D3A6855`

A medida DAX retorna uma string HTML/CSS completa que é renderizada dentro do visual:
```dax
HtmlKpiViews = "
<div style='font-family: Segoe UI; background: linear-gradient(135deg,#1e3a5f,#2d6a9f);
             border-radius: 12px; padding: 16px; color: white;'>
  <div style='font-size: 11px; opacity: 0.7; text-transform: uppercase;'>Views</div>
  <div style='font-size: 32px; font-weight: bold;'>" & FORMAT([TotalViews], "#,##0") & "</div>
</div>"
```

Padrões CSS usados:
- **Glass morphism**: `backdrop-filter: blur(10px); background: rgba(255,255,255,0.1)`
- **Animated gradient**: `@keyframes br { background-position: 0%→100%→0% }`
- **SVG gauge**: `stroke-dasharray: 283; stroke-dashoffset: calculado`
- **Responsive font**: `font-size: clamp(12px, 2.5vw, 14px)`
- **HTML table dinâmica**: via `CONCATENATEX` — gera linhas de tabela por linha de dado

### 48.6 Shape como hotspot invisível para ação

```json
// Shape 100% transparente com visualLink — o "botão invisível" sobre uma imagem
{
  "visualType": "shape",
  "singleVisual": {
    "objects": {
      "fill": [{ "properties": {
        "transparency": { "expr": { "Literal": { "Value": "100D" } } }
      } }]
    },
    "vcObjects": {
      "visualLink": [{ "properties": {
        "type":     { "expr": { "Literal": { "Value": "'PageNavigation'" } } },
        "navigationSection": { "expr": { "Literal": { "Value": "'page-id'" } } }
      } }]
    }
  }
}
```
Permite que qualquer área clicável do canvas ative uma ação sem precisar de imagem ou botão explícito.

---

## Seção 49 — Análise de Qualidade: 7 Dashboards

> Análise visual, funcional e de dados. Serve de benchmark para o DashForge AI. Data: 2026-04-23

### 49.1 Scorecard consolidado

| Dashboard                  | Canvas      | Págs | Visual ★ | Interativ. ★ | Dados ★ | Total |
|----------------------------|-------------|------|----------|--------------|---------|-------|
| **Databrick Gov**          | 1280×720    | 3    | ★★★★★   | ★★★★★       | ★★★★☆  | 14/15 |
| **projeto.pbip**           | 1280×720    | 8    | ★★★★★   | ★★★★★       | ★★★☆☆  | 13/15 |
| **Elos Minuta**            | 1800×900    | 8+tt | ★★★★☆   | ★★★☆☆       | ★★★★★  | 12/15 |
| **Relatório Pagamentos**   | 1280×720    | 5    | ★★★☆☆   | ★★★★☆       | ★★★★★  | 12/15 |
| **Governança BI**          | 1710×800    | 4    | ★★★☆☆   | ★★★★☆       | ★★★★☆  | 11/15 |
| **ESTRATÉGICO - PROJETOS** | 2200×1200   | 4    | ★★★☆☆   | ★★★★☆       | ★★★☆☆  | 10/15 |
| **CONTRATAÇÕES - DGT**     | 1920×1080   | 3    | ★★★☆☆   | ★★★☆☆       | ★★☆☆☆  | 8/15  |

---

### 49.2 Qualidade Visual — análise por dimensão

#### Consistência de design

**★★★★★ Databrick Gov** — único com tema totalmente customizado (shadcn-theme.json). Paleta de 10 cores coerente, border-radius 12px uniforme, tipografia em hierarquia clara (20pt título → 13pt visual → 11pt subtítulo → 9pt dados). Cada visual segue o mesmo padrão de container (background branco + borda #E4E4E7).

**★★★★★ projeto.pbip** — coerência por página temática (dark navy, light, sage-green). Cada página tem identidade própria mas linguagem visual unificada. Glass morphism aplicado consistentemente.

**★★★☆☆ CONTRATAÇÕES - DGT** — paleta #1F5673 aplicada, mas fontes inconsistentes entre páginas (títulos 25D em uma página, 22D em outra). Shape de fundo maior que o canvas (2597×2876px) — workaround de design.

**★★☆☆☆ Governança BI** — 25 imagens como elementos de layout (banners, ícones). Shapes como rótulos de indicadores em vez de visuais nativos. Sensação de "colagem" em vez de dashboard nativo.

#### Adequação do tipo de gráfico ao dado

**Acertos observados:**
- Databrick Gov: barras horizontais para ranking (melhor que treemap, decisão confirmada pelo usuário)
- Governança BI: combo chart (coluna + linha) para realizado vs meta — ideal para esse caso
- Elos Minuta: donut para composição de custo mensal — correto
- Elos Minuta: azureMap para distribuição geográfica de usuários — ideal
- ESTRATÉGICO: Gantt para cronograma de projetos — único chart adequado

**Problemas observados:**
- Governança BI: gauge customizado de marketplace — impacto visual alto mas limitações técnicas; medida `Meta` hardcoded como constante DAX
- CONTRATAÇÕES - DGT: stackedAreaChart para % executado/previsto — legenda Left consome muito espaço lateral

#### Densidade de informação por página

**Alta densidade (problema):**
- Relatório Pagamentos: 142 visuais em 5 páginas = 28 visuais/página em média. Página "deposito de visuais" (39 visuais) indica rascunho não removido — ruído no arquivo PBIR.
- CONTRATAÇÕES - DGT: tabela com 14 colunas — ultrapassa a largura confortável de leitura.

**Densidade ideal:**
- Databrick Gov: 16 visuais/página média, clara hierarquia de atenção (KPIs → gráfico → tabela).
- Governança BI: estrutura 1 gráfico grande + 1 gauge + KPI por página — foco.

---

### 49.3 Qualidade Funcional — análise por dimensão

#### Navegação e orientação do usuário

**★★★★★ Melhor prática — Governança BI**
Imagens de navegação com `tooltip` textual ("Clique para navegar para PJe 1° e 2° Grau"). O usuário sabe para onde vai antes de clicar. PageNavigation em vez de bookmarks — mais simples de manter.

**★★★★★ Melhor prática — projeto.pbip**
Barra de navegação persistente no topo (`exec_nav_bar`), shapes como hotspots invisíveis sobre ícones SVG, 3 destinos sempre visíveis. Padrão de SPA (single page application) no Power BI.

**★★☆☆☆ Problema — Elos Minuta**
8 páginas, 7 delas HiddenInViewMode. Sem bookmarks. Sem pageNavigator. Como o usuário navega? Depende do painel lateral nativo do Power BI — não há controle programático da navegação.

#### Controle de filtros

**★★★★★ Melhor prática — Databrick Gov**
- Gaveta Padrão A: VisualGroup com slicers dentro → oculta para fora do canvas
- 2 bookmarks (abrir/fechar) + 1 ClearAllSlicers independente
- SyncGroup entre páginas: mesmo filtro mantido ao navegar
- InvertedSelectionMode no slicer de categoria: "todos exceto X"

**★★★★★ Melhor prática — projeto.pbip**
- htmlContent como UI de gaveta: CSS puro em medida DAX, sem dependência de shape/image
- `SageDrawerBg` + `SageBtnOpen/Close` — gaveta com backdrop blur animado
- Estado de filtro capturado em bookmark com slicer states

**★★☆☆☆ Ausente — Elos Minuta**
Sem ClearAllSlicers, sem gaveta, sem sinal visual de filtro ativo. O usuário pode não saber que está filtrando.

#### Conteúdo dinâmico

**★★★★★ Melhor prática — Elos Minuta**
```dax
Ultima_Atualizacao = "Atualizado em " & FORMAT(NOW()-TIME(3,0,0), "dd/MM/yyyy HH:mm")
Titulo - Painel Executivo = "Controle de Fiscalização - " & [Periodo Selecionado]
```
Timestamp com correção de fuso horário (UTC-3). Título da página reflete filtro ativo. O usuário sempre sabe quando os dados foram atualizados e qual período está vendo.

**★★★★★ Melhor prática — ESTRATÉGICO**
```dax
ExibirHistorico = IF(ISFILTERED(Projetos[Projeto]), 1, 0)
```
Painel de histórico aparece apenas quando um projeto específico é selecionado. Sem isso o dashboard ficaria poluído com dados de todos os projetos simultaneamente.

**★★★★★ Melhor prática — projeto.pbip**
```dax
HtmlKpiViews → cor condicional por valor, animação de progresso, badge de status
```
Cards que mudam de aparência baseado nos dados — não apenas o valor, mas cor de fundo, ícone e animação.

---

### 49.4 Qualidade de Dados — análise por dimensão

#### Proteção contra contextos inválidos

**★★★★★ Melhor prática — Databrick Gov** (padrão mais rigoroso)
```dax
DIVIDE([A], [B])                         -- nunca divisão direta
IF(HASONEVALUE(T[col]), RANKX(...))      -- rank só com contexto único
CALCULATE(..., ALLEXCEPT(...))           -- participação com contexto controlado
```
Toda medida que pode receber contexto múltiplo tem proteção explícita.

**Problema — CONTRATAÇÕES - DGT**
```dax
Razão = SUM([Valor]) / CALCULATE(SUM([Dotação]), [Ano]="2025")
```
Divisão direta sem DIVIDE. Se o denominador for zero, retorna erro em vez de BLANK. Ano hardcoded como "2025" — quebrará em 2026.

#### Validação e qualidade de dados visível ao usuário

**★★★★★ Melhor prática — Relatório Pagamentos**
KPI dedicado para cada tipo de problema detectado:
```dax
Problemas Encontrados = [Qtd Alvará Faltante] + [Qtd Precatório Faltante] +
                        [Qtd Valor com Problema] + [Assinaturas Faltando]
```
Card muda de cor (#00567E azul → #DE6A73 vermelho) quando há problemas. O usuário vê imediatamente que há dados para corrigir, sem precisar ir à tabela.

**★★★★★ Melhor prática — Elos Minuta**
```dax
Status_Validacao = IF(ABS([ValorCalculado] - [ValorReal]) <= 0.01,
                      "✅ Dados Conciliados", "❌ Divergência encontrada")
```
Reconciliação linha por linha com tolerância de 1 centavo. Aplicada como formatação condicional na tabela — linhas problemáticas ficam vermelhas.

**Ausente — ESTRATÉGICO - PROJETOS e Governança BI**
Nenhum indicador de qualidade de dados. O usuário não tem como saber se os dados do SharePoint estão completos ou com problemas.

#### Frescor e rastreabilidade dos dados

**★★★★★ Elos Minuta** — timestamp visível com fuso horário correto
**★★★☆☆ Governança BI** — `Disponibilidade % (Até Hoje)` usa `KEEPFILTERS(Date <= TODAY())` — dados sempre atuais até hoje, mas sem indicador visual de quando foi o último refresh
**★★☆☆☆ demais** — sem qualquer indicador de atualização

---

### 49.5 Melhores práticas a replicar no DashForge AI (por categoria)

#### Visual
| Prática | Fonte | Implementação |
|---|---|---|
| Tema unificado com theme.json | Databrick Gov | Gerar shadcn-theme.json adaptado ao projeto |
| Hierarquia tipográfica clara: 20→13→11→9pt | Databrick Gov | Hardcoded por canvas size |
| 1 chart grande + KPIs + tabela por página | Databrick Gov + Governança BI | Template de página padrão |
| Barras horizontais para ranking | Databrick Gov | clusteredBarChart + sort DESC |
| Combo chart para meta vs realizado | Governança BI | lineClusteredColumnComboChart |

#### Funcional
| Prática | Fonte | Implementação |
|---|---|---|
| Gaveta com syncGroup cross-page | Databrick Gov | Padrão A + syncConfig |
| ClearAllSlicers dedicado (funnel-x) | Databrick Gov + DGT | Imagem fixa em toda página |
| Timestamp de atualização visível | Elos Minuta | Medida `Ultima_Atualizacao` |
| Título de página reflete filtro ativo | Elos Minuta + Governança BI | SELECTEDVALUE ou Periodo Selecionado |
| ExibirHistorico para painel detalhe | ESTRATÉGICO | ISFILTERED + filtro visual |
| Tooltip em botão de navegação | Governança BI | `tooltip.text` na visualLink |

#### Dados
| Prática | Fonte | Implementação |
|---|---|---|
| DIVIDE() em toda divisão | Databrick Gov | Regra de codegen de medidas |
| HASONEVALUE() antes de RANKX | Databrick Gov | Proteção padrão em medidas de rank |
| KPI de problemas detectados | Relatório Pagamentos | Medida = soma de N validadores |
| Cor condicional do card por alerta | Relatório Pagamentos | Formatação condicional com HEX |
| ABS(diff) <= tolerância | Elos Minuta | Para reconciliação de valores monetários |
| Pasta de medidas (displayFolder) | Databrick Gov | 9 pastas padrão geradas sempre |

---

### 49.6 Anti-padrões identificados (nunca replicar)

| Anti-padrão | Observado em | Problema |
|---|---|---|
| Imagens como elementos de layout (25 imagens/pág) | Governança BI | Manutenção impossível, não responsivo |
| Shapes como rótulos textuais | Governança BI | Não lê via acessibilidade, não escala |
| Shape maior que o canvas (2597×2876px) | CONTRATAÇÕES - DGT | Causa confusão no editor |
| Divisão direta sem DIVIDE | CONTRATAÇÕES - DGT | Erro em runtime quando denominador = 0 |
| Ano hardcoded em medida DAX ("2025") | CONTRATAÇÕES - DGT | Quebra ao virar o ano |
| Página "deposito de visuais" em produção | Relatório Pagamentos | Vaza rascunhos para o arquivo PBIR |
| 8 páginas ocultas sem navegação programática | Elos Minuta | Usuário desorientado |
| Gauge de marketplace como KPI principal | Governança BI | Opaco, não escala, dependência de marketplace |
| Sem indicador de frescor de dados | 4 de 7 dashboards | Usuário não sabe se dados são atuais |

*Seções 48–49 adicionadas em 2026-04-23 — análise qualitativa de 7 dashboards reais*

*Última atualização: 2026-04-18 — baseado em análise das screenshots do Databrick Gov + pesquisa Nielsen Norman Group, Tremor, shadcn/ui, Microsoft Learn*

---

## Seção 50 — Gap Analysis: O que falta documentar antes de codar o DashForge AI

> Adicionado em 2026-04-23. Objetivo: identificar lacunas de conhecimento que impediriam o agente de gerar um `.pbip` válido do zero.

### 50.1 Status geral (o que JÁ temos)

| Área | Seções | Status |
|---|---|---|
| Estrutura de pastas do .pbip | 1, 19 | ✅ Completo |
| Formato de cor | 2 | ✅ Completo |
| TMDL: medidas, colunas, tabelas calculadas, M/SharePoint | 3, 18, 31 | ✅ Completo |
| Relationships TMDL | 3.1 | ✅ Completo |
| model.tmdl (raiz) | 3.2, 18 | ✅ Completo |
| visual.json: card, cardVisual, slicer, textbox, shape, image, visualGroup | 4, 4.1-4.8 | ✅ Completo |
| visual.json: tableEx | 38 | ✅ Completo (schema completo) |
| visual.json: query roles de charts (lineChart, bar, column) | 4.8 | ✅ Referência |
| visual.json: deneb | 21, 22, 48.4 | ✅ Completo |
| visual.json: htmlContent | 7, 11, 48.5 | ✅ Completo |
| page.json | 5 | ✅ Completo |
| pages.json (metadata) | 6 | ✅ Completo |
| Bookmarks JSON (gaveta UI toggle) | 35, 45.1-45.3 | ✅ Completo |
| report.json (fragmentos: custom visuals + settings) | 12, 45.4 | ⚠️ Parcial |
| DAX: medidas críticas + proteções + time intelligence | 10, 33, 39, 46 | ✅ Completo |
| displayFolder TMDL | 37 | ✅ Completo |
| Slicer sync, inverted selection | 44 | ✅ Completo |
| Conditional formatting selector | 36.4, 4.7 | ✅ Completo |
| Layout constants + LayoutValidator formulas | 41-43 | ✅ Completo |
| Auto-normalization (o que PBI adiciona no save) | 8, 13 | ✅ Documentado |
| Regras críticas de geração (indentação TMDL, GUID format, schema version) | 31 | ✅ Completo |
| DashForge AI tiers de capacidade | 47 | ✅ Completo |

---

### 50.2 GAPS Críticos — impedem geração de .pbip do zero

#### ~~GAP-C1~~ RESOLVIDO: Conteúdo do arquivo raiz `.pbip`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
  "version": "1.0",
  "artifacts": [
    {
      "report": {
        "path": "Relatório Pagamentos.Report"
      }
    }
  ],
  "settings": {
    "enableAutoRecovery": true
  }
}
```

**Regras:**
- `artifacts[0].report.path` = nome da pasta `.Report` (convenção: `<NomeProjeto>.Report`)
- `version` é sempre `"1.0"` (do schema pbipProperties)
- `enableAutoRecovery: true` é boilerplate fixo
- O agente substitui apenas o `path` ao gerar um novo projeto

#### ~~GAP-C2~~ RESOLVIDO: Conteúdo do arquivo `definition.pbir`

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
  "version": "4.0",
  "datasetReference": {
    "byPath": {
      "path": "../Relatório Pagamentos.SemanticModel"
    }
  }
}
```

**Regras:**
- `version: "4.0"` é a versão do PBIR — manter fixo
- `byPath.path` = caminho relativo da pasta `.Report` até a pasta `.SemanticModel`, sempre `"../<NomeProjeto>.SemanticModel"`
- Convenção de nomes: `<NomeProjeto>.Report` e `<NomeProjeto>.SemanticModel` ficam lado a lado na mesma pasta raiz
- Para Mode B (SemanticModel existente fornecido pelo usuário): só trocar o path para apontar para o SemanticModel recebido

#### GAP-C3: M query para CSV e Excel — CRÍTICO (Mode C)

A Seção 3 tem apenas o padrão SharePoint. Para o **Mode C** (receber CSV/Excel e criar SemanticModel), precisamos dos padrões M:

```m
// CSV — TODO: verificar e documentar
Fonte = Csv.Document(File.Contents("C:\dados.csv"), [Delimiter=";", Encoding=1252, QuoteStyle=QuoteStyle.None])

// Excel — TODO: verificar e documentar
Fonte = Excel.Workbook(File.Contents("C:\dados.xlsx"), null, true),
Tabela = Fonte{[Item="Sheet1", Kind="Sheet"]}[Data]
```

Também falta: como o agente recebe o arquivo (upload → salva em disco → path no M query)? Qual path usar para que o .pbip seja portável?

---

### 50.3 GAPS Altos — degradam qualidade mas não bloqueiam MVP

#### GAP-A1: Templates completos de chart visual.json — ALTO

Temos os query roles (Seção 4.8) e objetos, mas não temos um **visual.json mínimo copy-paste-ready** para cada tipo de gráfico padrão. O agente precisa de templates canônicos para:

- `lineChart` (temos exemplo em Seção 40 para forecast — pode ser adaptado)
- `clusteredBarChart`
- `clusteredColumnChart`
- `stackedAreaChart`
- `donutChart`
- `lineClusteredColumnComboChart` (esboço em Seção 48.2)

**Estratégia:** Criar um chart mínimo de cada tipo no PBI Desktop, salvar como .pbip, copiar o visual.json resultante.

#### GAP-A2: Visual-level filter JSON (padrão ExibirHistorico) — ALTO

A Seção 46.3 documenta a medida DAX `ExibirHistorico = IF(ISFILTERED(T[col]), 1, 0)` e diz "aplicar como filtro de nível visual: ExibirHistorico = 1". Mas **não temos o JSON** que representa esse filtro dentro do visual.json.

É diferente do slicer filter (Seção 30). A Seção 30 diz "nunca escreva filtros de dados à mão" para bookmarks, mas o visual-level filter estático é mais simples. Precisamos do JSON exato que PBI Desktop gera quando você adiciona um filtro visual.

**Como resolver:** Adicionar um filtro de nível visual em qualquer chart, salvar, copiar o JSON resultante.

#### GAP-A3: report.json template mínimo completo — ALTO

Temos fragmentos (custom visuals em Seção 12, settings em Seção 45.4) mas não um template mínimo funcional do report.json inteiro para um relatório sem custom visuals. O que é obrigatório? O que é opcional?

**Hipótese do conteúdo mínimo:**
```json
{
  "$schema": "...",
  "themeCollection": { ... },
  "filterPaneHiddenInEditMode": true,
  "defaultDrillFilterOtherVisuals": true,
  "outspacePane": { "expanded": false }
}
```

---

### 50.4 GAPS Médios — importantes para Mode B e boas práticas

#### GAP-M1: version.json — MÉDIO

Mencionado na Seção 1 como "PBIR version (2.0.0)" mas sem conteúdo documentado. Provavelmente só 2-3 linhas JSON.

#### GAP-M2: cultures/pt-BR.tmdl — MÉDIO

Mencionado na estrutura (Seção 1) mas sem conteúdo. Necessário para criar um SemanticModel completo. Pode ser boilerplate fixo.

#### GAP-M3: Convenção de nomenclatura de IDs gerados — MÉDIO

A Seção 6 diz "IDs podem ser human-readable, PBI preserva". Mas o agente precisa de uma convenção determinista:
- Nome da pasta do visual == campo `name` no visual.json?
- Nome da pasta da página == campo `name` no page.json?
- IDs de bookmark: formato?
- Quando usar slugs (snake_case) vs. GUID aleatório?

**Convenção recomendada para implementar:**
```
page folder:    slug do displayName  →  "visao_geral"
visual folder:  tipo + número        →  "card_01", "lineChart_01"
bookmark ID:    b_ + slug            →  "b_abrir_gaveta"
lineageTag:     UUID v4 gerado       →  python: str(uuid.uuid4())
```

#### GAP-M4: Mode B — leitura de SemanticModel existente — MÉDIO

Para o Mode B (receber .pbip com SemanticModel, adicionar páginas), o agente precisa:
1. Ler os arquivos `tables/*.tmdl` para descobrir tabelas e colunas disponíveis
2. Extrair: nomes de tabelas, nomes de colunas, nomes de medidas, tipos de dados
3. Usar esses nomes nos campos `Entity` e `Property` do visual.json

Não temos documentado o algoritmo de parse de TMDL para extração de schema. O parsing é simples (TMDL é texto estruturado por indentação) mas precisa ser planejado.

**Regra de binding Entity/Property (parcialmente implícita nas seções existentes):**
```json
// Na query do visual.json:
"Entity": "NomeDaTabela",   // exatamente como aparece no .tmdl, sem aspas simples
"Property": "NomeDaColuna"  // exatamente como aparece no .tmdl (com espaços se houver)
```

#### GAP-M5: syncSlicers.json nível de página — MÉDIO

A Seção 44.3 mostra `syncConfig` dentro do visual.json. Mas existe também um `syncSlicers.json` por página? Ou o sync fica 100% no visual? Não está claro. Verificar nos arquivos reais dos dashboards que usam syncGroup.

---

### 50.5 GAPS Baixos — podem esperar

#### GAP-B1: Tooltip page formato completo
Seção 43.7 identifica tooltip pages (`displayOption: "Tooltip"` + `HiddenInViewMode`). Falta: como um visual referencia uma tooltip page? Qual campo no visual.json aponta para a página de tooltip?

#### GAP-B2: Conditional formatting em tableEx (cor de fundo/texto)
Seção 43.6 menciona que tableEx suporta conditional formatting. A Seção 36.4 cobre `selector.data.scopeId.Measure` para colorir série de chart. Mas a aplicação específica a colunas de tabela (background/font color por valor) não foi explicitamente templated.

---

### 50.6 Plano de ação — como preencher os gaps antes de codar

| Gap | Ação | Complexidade |
|---|---|---|
| GAP-C1 (`.pbip` raiz) | Abrir qualquer .pbip como texto → copiar aqui | 5 min |
| GAP-C2 (`definition.pbir`) | Abrir `definition.pbir` de qualquer projeto → copiar aqui | 5 min |
| GAP-C3 (M query CSV/Excel) | Criar tabela no PBI Desktop via "Obter Dados > Texto/CSV" → salvar .pbip → copiar partition M | 15 min |
| GAP-A1 (chart templates) | Criar 1 de cada tipo no PBI Desktop, salvar, copiar visual.json | 60 min |
| GAP-A2 (visual-level filter) | Adicionar filtro visual no Desktop, salvar, copiar JSON | 10 min |
| GAP-A3 (report.json mínimo) | Criar .pbip vazio no Desktop, copiar report.json gerado | 5 min |
| GAP-M1 (version.json) | Copiar de qualquer projeto existente | 2 min |
| GAP-M2 (cultures TMDL) | Copiar de qualquer projeto existente | 2 min |
| GAP-M3 (convenção IDs) | Decisão de design — documentar convenção acima | 0 min (já decidido acima) |
| GAP-M4 (Mode B leitura) | Planejar algoritmo de parse TMDL na fase 2 | planejar depois |
| GAP-M5 (syncSlicers.json) | Grep nos dashboards reais existentes | 10 min |

**Prioridade:** GAP-C1, C2, C3 bloqueiam o start do Fase 1. GAP-A1, A2, A3 bloqueiam qualidade do output. Gaps M e B podem ser feitos durante desenvolvimento.

*Seção 50 adicionada em 2026-04-23*

---

## Seção 51 — Templates Canônicos de Chart visual.json + Gaps Resolvidos

> Adicionado em 2026-04-24. Fecha GAP-A1, GAP-A2, GAP-A3, GAP-M1, GAP-M2, GAP-M5 da Seção 50.

---

### 51.1 Estrutura mínima de qualquer chart (esqueleto comum)

Todo chart compartilha esta estrutura — apenas `visualType` e os `projections` mudam.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.7.0/schema.json",
  "name": "bar_01",
  "position": { "x": 0, "y": 0, "z": 1000, "height": 300, "width": 500, "tabOrder": 1000 },
  "visual": {
    "visualType": "<tipo>",
    "query": {
      "queryState": {
        "Category": { "projections": [
          {
            "field": { "Column": { "Expression": { "SourceRef": { "Entity": "Tabela" } }, "Property": "Coluna" } },
            "queryRef": "Tabela.Coluna",
            "nativeQueryRef": "Coluna",
            "active": true
          }
        ]},
        "Y": { "projections": [
          {
            "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "Medidas" } }, "Property": "Valor" } },
            "queryRef": "Medidas.Valor",
            "nativeQueryRef": "Valor"
          }
        ]}
      },
      "sortDefinition": {
        "sort": [{ "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "Medidas" } }, "Property": "Valor" } }, "direction": "Descending" }],
        "isDefaultSort": true
      }
    },
    "drillFilterOtherVisuals": true
  }
}
```

**Regras críticas:**
- `queryRef` = `"Entidade.Propriedade"` (concatenação com ponto)
- `nativeQueryRef` = nome exibido no visual (pode ser diferente da propriedade)
- `active: true` na Category = dimensão principal ativa no eixo
- `objects` e `visualContainerObjects` são OPCIONAIS — se omitidos, usa defaults do tema
- Sem `objects` o visual é válido e abre no PBI Desktop

---

### 51.2 clusteredBarChart (barras horizontais — ranking)

**Quando usar:** ranking de categorias, comparação entre itens de uma lista.

**Roles:** `Category` (dimensão/coluna), `Y` (medida).

```json
"visualType": "clusteredBarChart"
```

**Observações do template real:**
- `valueAxis.show: false` + `valueAxis.showAxisTitle: false` = eixo Y oculto (padrão moderno)
- `categoryAxis.showAxisTitle: false` = sem título de eixo  
- `labels.bold: true` = rótulos em negrito

---

### 51.3 clusteredColumnChart (colunas verticais)

**Quando usar:** comparação temporal por período curto, distribuição por categoria.

**Roles:** `Category` (dimensão), `Y` (medida), `Tooltips` (medidas extras no tooltip — opcional).

```json
"visualType": "clusteredColumnChart"
```

**Role adicional Tooltips:**
```json
"Tooltips": { "projections": [{
  "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "Tab" } }, "Property": "MedidaExtra" } },
  "queryRef": "Tab.MedidaExtra",
  "nativeQueryRef": "Label do Tooltip",
  "displayName": "Label do Tooltip"
}]}
```

---

### 51.4 lineChart (linha temporal)

**Quando usar:** tendência ao longo do tempo, evolução de KPI.

**Roles:** `Category` (hierarquia de data OU coluna), `Y` (medida).

**Eixo de data com hierarquia automática do PBI (mais comum):**
```json
"Category": { "projections": [
  {
    "field": { "HierarchyLevel": {
      "Expression": { "Hierarchy": { "Expression": { "PropertyVariationSource": {
        "Expression": { "SourceRef": { "Entity": "Calendario" } },
        "Name": "Variation",
        "Property": "Date"
      }}, "Hierarchy": "Hierarquia de datas" }},
      "Level": "Ano"
    }},
    "queryRef": "Calendario.Date.Variation.Hierarquia de datas.Ano",
    "nativeQueryRef": "Date Ano",
    "active": true
  },
  {
    "field": { "HierarchyLevel": {
      "Expression": { "Hierarchy": { "Expression": { "PropertyVariationSource": {
        "Expression": { "SourceRef": { "Entity": "Calendario" } },
        "Name": "Variation",
        "Property": "Date"
      }}, "Hierarchy": "Hierarquia de datas" }},
      "Level": "Mês"
    }},
    "queryRef": "Calendario.Date.Variation.Hierarquia de datas.Mês",
    "nativeQueryRef": "Date Mês",
    "active": true
  }
]}
```

**Observações:**
- Múltiplos níveis (Ano + Mês) = permite drill-down
- `active: false` em níveis inferiores (Dia) = visível no drill mas não exibido por default
- Para eixo de data simples (sem hierarquia): usar `Column` normal

---

### 51.5 donutChart (rosca)

**Quando usar:** composição de partes do todo (máx 5-6 fatias — anti-padrão com muitas fatias).

**Roles:** `Category` (dimensão), `Y` (medida).

```json
"visualType": "donutChart"
```

**objects relevantes:**
```json
"labels": [{ "properties": {
  "labelStyle": { "expr": { "Literal": { "Value": "'Category, data value, percent of total'" } } },
  "labelDisplayUnits": { "expr": { "Literal": { "Value": "1D" } } }
}}],
"legend": [{ "properties": { "show": { "expr": { "Literal": { "Value": "true" } } } } }]
```

---

### 51.6 stackedAreaChart (área empilhada)

**Quando usar:** composição ao longo do tempo (ex: execução vs. previsto por período).

**Roles:** `Category` (HierarchyLevel de data OU coluna), `Y` (medida).

```json
"visualType": "stackedAreaChart"
```

**Novidades descobertas neste tipo:**
- `visualContainerObjects.title.heading: "'Heading3'"` — define hierarquia tipográfica do título
- `visualContainerObjects.title.titleWrap: true` — permite quebra de linha no título
- `visualContainerObjects.divider` — linha separadora entre título e visual
- `visualContainerObjects.visualHeader.show` — controla visibilidade do header completo
- `selector.metadata: "Sum(Tabela.Coluna)"` — colore serie específica pelo nome da agregação

---

### 51.7 lineClusteredColumnComboChart (combo coluna + linha)

**Quando usar:** realizado (coluna) vs. meta (linha) no mesmo gráfico.

**Roles:** `Category` (eixo X compartilhado), `Y` (colunas — eixo primário), `Y2` (linha — eixo secundário).

```json
"visualType": "lineClusteredColumnComboChart"
// também existe: "lineStackedColumnComboChart" (coluna empilhada + linha)
```

**Estrutura com Y2 (eixo secundário para a linha):**
```json
"queryState": {
  "Category": { "projections": [/* coluna de data ou categoria */] },
  "Y":  { "projections": [/* medida para as colunas */] },
  "Y2": { "projections": [
    {
      "field": { "Measure": { "Expression": { "SourceRef": { "Entity": "TabMeta" } }, "Property": "Meta" } },
      "queryRef": "TabMeta.Meta",
      "nativeQueryRef": "Meta"
    }
  ]}
}
```

**objects exclusivos do combo:**
```json
"valueAxis": [{ "properties": {
  "show": { "expr": { "Literal": { "Value": "false" } } },
  "secShow": { "expr": { "Literal": { "Value": "false" } } },
  "secLabelColor": { "solid": { "color": { "expr": { "Literal": { "Value": "'#FF0000'" } } } } }
}}],
"lineStyles": [{ "properties": {
  "strokeLineJoin": { "expr": { "Literal": { "Value": "'miter'" } } },
  "lineStyle": { "expr": { "Literal": { "Value": "'solid'" } } },
  "showMarker": { "expr": { "Literal": { "Value": "false" } } }
}}],
"seriesLabels": [{ "properties": {
  "show": { "expr": { "Literal": { "Value": "false" } } },
  "seriesPosition": { "expr": { "Literal": { "Value": "'Left'" } } }
}}]
```

**Colorir serie específica por medida (selector.metadata):**
```json
"dataPoint": [
  { "properties": { "fill": { "solid": { "color": { "expr": { "Literal": { "Value": "'#0097B2'" } } } } } },
    "selector": { "metadata": "TabMeta.Meta" } }
]
```

---

### 51.8 ~~GAP-A2~~ RESOLVIDO: filterConfig de visual-level filter (ExibirHistorico)

O `filterConfig` é o filtro aplicado ao visual via painel de filtros do PBI Desktop. O padrão para ocultar/mostrar visuals com medida de controle é **"medida is NOT null"**:

```json
"filterConfig": {
  "filters": [
    {
      "name": "4933e43dd14fec8ce815",
      "field": {
        "Measure": {
          "Expression": { "SourceRef": { "Entity": "Medidas" } },
          "Property": "ExibirHistorico"
        }
      },
      "type": "Advanced",
      "filter": {
        "Version": 2,
        "From": [{ "Name": "m", "Entity": "Medidas", "Type": 0 }],
        "Where": [{
          "Condition": {
            "Not": {
              "Expression": {
                "Comparison": {
                  "ComparisonKind": 0,
                  "Left": { "Measure": { "Expression": { "SourceRef": { "Source": "m" } }, "Property": "ExibirHistorico" } },
                  "Right": { "Literal": { "Value": "null" } }
                }
              }
            }
          }
        }]
      },
      "howCreated": "User"
    }
  ]
}
```

**Por que "NOT null" e não "= 1":** A medida `ExibirHistorico = IF(ISFILTERED(T[col]), 1, BLANK())`. O PBI trata BLANK() como null. O filtro "NOT null" passa qualquer valor não-blank — ou seja, mostra o visual quando a medida retornar 1.

**`name` do filtro:** hex de 20 chars gerado aleatoriamente. Usar `uuid.uuid4().hex[:20]` em Python.

---

### 51.9 ~~GAP-A3~~ RESOLVIDO: report.json mínimo completo

Versão sem custom visuals, sem imagens, tema base padrão do PBI:

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.2.0/schema.json",
  "themeCollection": {
    "baseTheme": {
      "name": "CY25SU10",
      "reportVersionAtImport": {
        "visual": "2.1.0",
        "report": "3.0.0",
        "page": "2.3.0"
      },
      "type": "SharedResources"
    }
  },
  "settings": {
    "useStylableVisualContainerHeader": true,
    "exportDataMode": "AllowSummarized",
    "defaultDrillFilterOtherVisuals": true,
    "allowChangeFilterTypes": true,
    "useEnhancedTooltips": true,
    "useDefaultAggregateDisplayName": true
  }
}
```

**Para adicionar gaveta de filtros (outspacePane oculto por padrão):**
```json
"objects": {
  "outspacePane": [{ "properties": { "expanded": { "expr": { "Literal": { "Value": "false" } } } } }],
  "section": [{ "properties": { "verticalAlignment": { "expr": { "Literal": { "Value": "'Top'" } } } } }]
}
```

---

### 51.10 ~~GAP-M1~~ RESOLVIDO: version.json

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
  "version": "2.0.0"
}
```

Arquivo fixo — nunca mudar.

---

### 51.11 ~~GAP-M2~~ RESOLVIDO: cultures/pt-BR.tmdl

**Não gerar.** O arquivo é auto-gerado pelo PBI Desktop com metadata linguística de cada medida e coluna. Tem 46k+ tokens por projeto de tamanho médio. Omitir completamente — o PBI cria na primeira abertura.

---

### 51.12 ~~GAP-M5~~ RESOLVIDO: syncSlicers.json

**Não existe.** Confirmado por busca em todos os projetos. O sync de slicer fica 100% dentro do `visual.json` do slicer:

```json
"syncConfig": {
  "group": "FiltroAno",
  "filterChanges": true,
  "fieldChanges": true
}
```

Fica dentro de `visual.objects.general[0].properties` ou diretamente em `visual.syncConfig` (depender da versão — verificar no visual.json real do slicer existente).

---

### 51.13 Status final dos Gaps (pós Seção 51)

| Gap | Status |
|---|---|
| GAP-C1 (.pbip raiz) | ✅ RESOLVIDO (Seção 50) |
| GAP-C2 (definition.pbir) | ✅ RESOLVIDO (Seção 50) |
| GAP-C3 (M query CSV/Excel) | ⚠️ PENDENTE — única ação que requer PBI Desktop |
| GAP-A1 (chart templates) | ✅ RESOLVIDO (Seção 51.2–51.7) |
| GAP-A2 (visual-level filter) | ✅ RESOLVIDO (Seção 51.8) |
| GAP-A3 (report.json mínimo) | ✅ RESOLVIDO (Seção 51.9) |
| GAP-M1 (version.json) | ✅ RESOLVIDO (Seção 51.10) |
| GAP-M2 (cultures TMDL) | ✅ RESOLVIDO (Seção 51.11) |
| GAP-M3 (convenção IDs) | ✅ RESOLVIDO (Seção 50.4) |
| GAP-M4 (Mode B leitura) | Planejado para Fase 2 |
| GAP-M5 (syncSlicers.json) | ✅ RESOLVIDO (Seção 51.12) |
| GAP-B1 (tooltip page ref) | Baixa prioridade — Fase 2+ |
| GAP-B2 (conditional format tableEx) | Baixa prioridade — Fase 2+ |

**Única pendência bloqueante para Fase 1:** GAP-C3 (M query CSV/Excel para Mode C). Mode A e Mode B podem começar sem isso.

*Seção 51 adicionada em 2026-04-24*

---

## Seção 52 — Arquivos Completos do SemanticModel para Mode C (CSV/Excel)

> Adicionado em 2026-04-24. Fecha GAP-C3. Fonte: projeto `vendas.pbip` gerado pelo PBI Desktop a partir de um CSV real.

---

### 52.1 ~~GAP-C3~~ RESOLVIDO: M Query para CSV

Formato gerado automaticamente pelo PBI Desktop ao carregar um CSV:

```tmdl
partition vendas = m
    mode: import
    source =
            let
                Fonte = Csv.Document(File.Contents("C:\caminho\completo\arquivo.csv"),[Delimiter=",", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None]),
                #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
                #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"Data", type date}, {"Produto", type text}, {"Regiao", type text}, {"Vendedor", type text}, {"Status", type text}, {"Valor", Int64.Type}, {"Quantidade", Int64.Type}})
            in
                #"Tipo Alterado"
```

**Parâmetros obrigatórios:**
- `Delimiter=","` — vírgula para CSV padrão (usar `";"` para CSV europeu/brasileiro)
- `Columns=N` — número de colunas do CSV (otimização de parser)
- `Encoding=65001` — UTF-8. Alternativas: `1252` (Windows-1252/ANSI), `1200` (UTF-16)
- `QuoteStyle=QuoteStyle.None` — padrão quando não há aspas duplas nos dados

**Mapeamento de tipos M → TMDL:**

| M type | TMDL dataType | TMDL formatString |
|---|---|---|
| `type date` | `dateTime` | `Long Date` |
| `type text` | `string` | *(omitir)* |
| `Int64.Type` | `int64` | `0` |
| `type number` / `Currency.Type` | `decimal` | `0.00` ou `"R$ #,##0.00"` |
| `type logical` | `boolean` | *(omitir)* |

**Coluna de data gera automaticamente o bloco `variation`:**
```tmdl
column Data
    dataType: dateTime
    formatString: Long Date
    lineageTag: <uuid>
    summarizeBy: none
    sourceColumn: Data

    variation Variation
        isDefault
        relationship: <uuid-do-relacionamento>
        defaultHierarchy: LocalDateTable_<uuid>.'Hierarquia de datas'

    annotation SummarizationSetBy = Automatic
    annotation UnderlyingDateTimeDataType = Date
```

O bloco `variation` conecta a coluna de data ao LocalDateTable auto-gerado. O UUID do relacionamento e do LocalDateTable são interdependentes — **gerados pelo PBI Desktop na primeira abertura.**

---

### 52.2 Estratégia de geração para Mode C (decisão arquitetural)

**Problema:** `variation`, `LocalDateTable_<UUID>` e o relacionamento em `relationships.tmdl` referenciam UUIDs gerados dinamicamente pelo PBI Desktop — não podem ser hardcoded.

**Solução:** O agente gera apenas o mínimo; o PBI Desktop completa o resto na primeira abertura.

| Arquivo | O agente gera? | Observação |
|---|---|---|
| `model.tmdl` | ✅ Sim | Com `__PBI_TimeIntelligenceEnabled = 1` |
| `database.tmdl` | ✅ Sim | Fixo: `compatibilityLevel: 1600` |
| `tables/<nome>.tmdl` | ✅ Sim | Sem o bloco `variation` — PBI adiciona |
| `relationships.tmdl` | ❌ Não | PBI cria ao reconhecer a coluna de data |
| `cultures/pt-BR.tmdl` | ❌ Não | PBI gera na primeira abertura |
| `DateTableTemplate_<UUID>.tmdl` | ❌ Não | PBI gera automaticamente |
| `LocalDateTable_<UUID>.tmdl` | ❌ Não | PBI gera automaticamente |
| `.platform` (Report e SemanticModel) | ✅ Sim | Com UUID gerado pelo agente |
| `definition.pbism` | ✅ Sim | Fixo (ver 52.4) |
| `definition.pbir` | ✅ Sim | Já documentado na Seção 50 |
| `.pbip` (raiz) | ✅ Sim | Já documentado na Seção 50 |

---

### 52.3 definition.pbism (novo — entry point do SemanticModel)

Análogo ao `definition.pbir` do Report. Conecta o SemanticModel ao schema do Fabric.

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
  "version": "4.2",
  "settings": {}
}
```

Arquivo fixo — não mudar.

---

### 52.4 .platform (Report e SemanticModel)

Arquivo de integração com Fabric/Git. Necessário em ambas as pastas.

**vendas.Report/.platform:**
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "Report",
    "displayName": "<NomeProjeto>"
  },
  "config": {
    "version": "2.0",
    "logicalId": "<uuid-v4>"
  }
}
```

**vendas.SemanticModel/.platform:**
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
  "metadata": {
    "type": "SemanticModel",
    "displayName": "<NomeProjeto>"
  },
  "config": {
    "version": "2.0",
    "logicalId": "<uuid-v4>"
  }
}
```

`logicalId` = UUID v4 único por artefato. Em Python: `str(uuid.uuid4())`.

---

### 52.5 database.tmdl (fixo)

```tmdl
database
    compatibilityLevel: 1600
```

Sempre idêntico. Nunca mudar.

---

### 52.6 model.tmdl mínimo para Mode C (tabela única)

```tmdl
model Model
    culture: pt-BR
    defaultPowerBIDataSourceVersion: powerBI_V3
    sourceQueryCulture: pt-BR
    dataAccessOptions
        legacyRedirects
        returnErrorValuesAsNull

annotation __PBI_TimeIntelligenceEnabled = 1
annotation PBI_QueryOrder = ["<NomeTabela>"]
annotation PBI_ProTooling = ["DevMode"]

ref table <NomeTabela>
ref cultureInfo pt-BR
```

**Notas:**
- `__PBI_TimeIntelligenceEnabled = 1` → PBI auto-cria LocalDateTable + DateTableTemplate + relacionamento para cada coluna de data
- `PBI_QueryOrder` → ordem das tabelas no painel de campos (lista JSON de strings)
- `ref cultureInfo pt-BR` → requerido para localização

---

### 52.7 Template completo de tabela TMDL para CSV (Mode C)

```tmdl
table <NomeTabela>
    lineageTag: <uuid-v4>

    column <ColunaCategorica>
        dataType: string
        lineageTag: <uuid-v4>
        summarizeBy: none
        sourceColumn: <ColunaCategorica>

        annotation SummarizationSetBy = Automatic

    column <ColunaData>
        dataType: dateTime
        formatString: Long Date
        lineageTag: <uuid-v4>
        summarizeBy: none
        sourceColumn: <ColunaData>

        annotation SummarizationSetBy = Automatic
        annotation UnderlyingDateTimeDataType = Date

    column <ColunaInteira>
        dataType: int64
        formatString: 0
        lineageTag: <uuid-v4>
        summarizeBy: sum
        sourceColumn: <ColunaInteira>

        annotation SummarizationSetBy = Automatic

    column <ColunaDecimal>
        dataType: decimal
        lineageTag: <uuid-v4>
        summarizeBy: sum
        sourceColumn: <ColunaDecimal>

        annotation SummarizationSetBy = Automatic

    partition <NomeTabela> = m
        mode: import
        source =
                let
                    Fonte = Csv.Document(File.Contents("<caminho-absoluto>.csv"),[Delimiter=",", Columns=<N>, Encoding=65001, QuoteStyle=QuoteStyle.None]),
                    #"Cabeçalhos Promovidos" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),
                    #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"<ColunaData>", type date}, {"<ColunaCategorica>", type text}, {"<ColunaInteira>", Int64.Type}, {"<ColunaDecimal>", type number}})
                in
                    #"Tipo Alterado"

    annotation PBI_ResultType = Table
```

**Atenção ao bloco `variation`:** Não gerar o bloco `variation` nas colunas de data — o PBI Desktop o adiciona automaticamente quando detecta `UnderlyingDateTimeDataType = Date` + `__PBI_TimeIntelligenceEnabled = 1`.

---

### 52.8 Estrutura completa de pastas para um .pbip gerado do zero (Mode C)

```
<Projeto>.pbip                                    ← fixo (ver Seção 50)
├── <Projeto>.Report/
│   ├── .platform                                 ← fixo com logicalId UUID
│   ├── definition.pbir                           ← fixo (ver Seção 50)
│   └── definition/
│       ├── version.json                          ← fixo (ver Seção 51.10)
│       ├── report.json                           ← mínimo (ver Seção 51.9)
│       └── pages/
│           ├── pages.json                        ← lista de páginas
│           └── <pageId>/
│               ├── page.json
│               └── visuals/
│                   └── <visualId>/
│                       └── visual.json
└── <Projeto>.SemanticModel/
    ├── .platform                                 ← fixo com logicalId UUID
    ├── definition.pbism                          ← fixo (ver Seção 52.3)
    └── definition/
        ├── model.tmdl                            ← mínimo (ver Seção 52.6)
        ├── database.tmdl                         ← fixo (ver Seção 52.5)
        └── tables/
            └── <NomeTabela>.tmdl                 ← gerado (ver Seção 52.7)
```

**Arquivos que o agente NÃO cria (PBI Desktop gera na 1ª abertura):**
- `relationships.tmdl`
- `cultures/pt-BR.tmdl`
- `tables/DateTableTemplate_<UUID>.tmdl`
- `tables/LocalDateTable_<UUID>.tmdl`
- `.pbi/` (pasta de cache local)

---

### 52.8b M Query para Excel (.xlsx)

```tmdl
partition <NomeTabela> = m
    mode: import
    source =
            let
                Fonte = Excel.Workbook(File.Contents("C:\caminho\completo\arquivo.xlsx"), null, true),
                <NomePlanilha>_Sheet = Fonte{[Item="<NomePlanilha>",Kind="Sheet"]}[Data],
                #"Cabeçalhos Promovidos" = Table.PromoteHeaders(<NomePlanilha>_Sheet, [PromoteAllScalars=true]),
                #"Tipo Alterado" = Table.TransformColumnTypes(#"Cabeçalhos Promovidos",{{"Data", type date}, {"Produto", type text}, {"Valor", Int64.Type}})
            in
                #"Tipo Alterado"
```

**Diferenças em relação ao CSV:**

| | CSV | Excel |
|---|---|---|
| Função | `Csv.Document(File.Contents(...), [...])` | `Excel.Workbook(File.Contents(...), null, true)` |
| Parâmetros extras | `Delimiter`, `Columns`, `Encoding` | Nenhum |
| Passo adicional | — | Selecionar planilha: `Fonte{[Item="<aba>", Kind="Sheet"]}[Data]` |
| Nome da tabela TMDL | Nome do arquivo (sem extensão) | **Nome da aba do Excel** |

**Parâmetros do `Excel.Workbook`:**
- `null` = deixar PBI inferir headers (padrão)
- `true` = `InferSheetDimensions` — detecta o range usado automaticamente (sempre `true`)

**Implicação para Mode C:** se o usuário enviar um `.xlsx`, o agente precisa saber o nome da aba para construir o M query. O nome da aba vira o nome da tabela no SemanticModel.

---

### 52.9 Status final — TODOS os gaps bloqueantes resolvidos

| Gap | Status |
|---|---|
| GAP-C1 (.pbip raiz) | ✅ Seção 50 |
| GAP-C2 (definition.pbir) | ✅ Seção 50 |
| GAP-C3 (M query CSV + arquivos SemanticModel) | ✅ **Seção 52** |
| GAP-A1 (chart templates) | ✅ Seção 51 |
| GAP-A2 (visual-level filter) | ✅ Seção 51 |
| GAP-A3 (report.json mínimo) | ✅ Seção 51 |
| GAP-M1 (version.json) | ✅ Seção 51 |
| GAP-M2 (cultures TMDL) | ✅ Seção 51 |
| GAP-M3 (convenção IDs) | ✅ Seção 50 |
| GAP-M5 (syncSlicers.json) | ✅ Seção 51 |

**Documentação completa. O desenvolvimento pode começar.**

*Seção 52 adicionada em 2026-04-24*
