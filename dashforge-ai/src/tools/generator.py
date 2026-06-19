import os
import json
import uuid
import pandas as pd


def criar_pbip(nome_projeto: str, pasta_saida: str, caminho_csv: str) -> str:

    pasta_raiz = os.path.join(pasta_saida, nome_projeto)
    nome_tabela = os.path.splitext(os.path.basename(caminho_csv))[0]
    df = pd.read_csv(caminho_csv)
    colunas = df.columns.tolist()
    num_colunas = len(colunas)

    #Dicionários

    dicionario_plataform_report = {
      "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
      "metadata": {
        "type": "Report",
        "displayName": f"{nome_projeto}"
      },
      "config": {
        "version": "2.0",
        "logicalId": f"{str(uuid.uuid4())}"
      }
    }

    dicionario_definition_pbir = {
      "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
      "version": "4.0",
      "datasetReference": {
        "byPath": {
          "path": f"../{nome_projeto}.SemanticModel"
        }
      }
    }

    dicionario_version_json = {
      "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
      "version": "2.0.0"
    }

    dicionario_report_json = {
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
        "useStylableVisualContainerHeader": True,
        "exportDataMode": "AllowSummarized",
        "defaultDrillFilterOtherVisuals": True,
        "allowChangeFilterTypes": True,
        "useEnhancedTooltips": True,
        "useDefaultAggregateDisplayName": True
      }
    }


    dicionario_pages_json = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": ["pagina_01"],
    "activePageName": "pagina_01"
    }

    dicionario_page_json = {
          "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
          "name": "pagina_01",
          "displayName": "Dashboard",
          "displayOption": "FitToPage",
          "height": 720,
          "width": 1280,
          "objects": {}
        }

    dicionario_plataform_semanticmodel = {
      "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
      "metadata": {
        "type": "SemanticModel",
        "displayName": f"{nome_projeto}"
      },
      "config": {
        "version": "2.0",
        "logicalId": f"{str(uuid.uuid4())}"
      }
    }

    dicionario_definition_pbism = {
      "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
      "version": "4.2",
      "settings": {}
    }


    dicionario_projeto_pbip =  {
      "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
      "version": "1.0",
      "artifacts": [{"report": {"path": f"{nome_projeto}.Report"}}],
      "settings": {"enableAutoRecovery": True}
    }


    # Arquivos .tmdl

    texto_model_tmdl = (
        f"model Model\n"
        f"\tculture: pt-BR\n"
        f"\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        f"\tsourceQueryCulture: pt-BR\n"
        f"\tdataAccessOptions\n"
        f"\t\tlegacyRedirects\n"
        f"\t\treturnErrorValuesAsNull\n\n"
        f"annotation PBI_ProTooling = [\"DevMode\"]\n"
    )

    texto_database_tmdl = "database\n\tcompatibilityLevel: 1600\n"

    # Gera um bloco "column X" por coluna, detectando o tipo automaticamente
    blocos_coluna = ""
    itens_tipo_m = []
    for col in colunas:
        dtype = df[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            data_type, summarize_by, tipo_m = "int64", "sum", "Int64.Type"
        elif pd.api.types.is_float_dtype(dtype):
            data_type, summarize_by, tipo_m = "double", "sum", "type number"
        else:
            data_type, summarize_by, tipo_m = "string", "none", "type text"

        blocos_coluna += (
            f"\tcolumn {col}\n"
            f"\t\tdataType: {data_type}\n"
            f"\t\tlineageTag: {str(uuid.uuid4())}\n"
            f"\t\tsummarizeBy: {summarize_by}\n"
            f"\t\tsourceColumn: {col}\n\n"
        )
        itens_tipo_m.append(f'{{"{col}", {tipo_m}}}')

    tipos_m = ", ".join(itens_tipo_m)

    texto_tmdl = (
        f"table {nome_tabela}\n"
        f"\tlineageTag: {str(uuid.uuid4())}\n\n"
        f"{blocos_coluna}"
        f"\tpartition {nome_tabela} = m\n"
        f"\t\tmode: import\n"
        f"\t\tsource =\n"
        f"\t\t\t\tlet\n"
        f"\t\t\t\t    Fonte = Csv.Document(File.Contents(\"{caminho_csv}\"),[Delimiter=\",\", Columns={num_colunas}, Encoding=65001, QuoteStyle=QuoteStyle.None]),\n"
        f"\t\t\t\t    #\"Cabeçalhos Promovidos\" = Table.PromoteHeaders(Fonte, [PromoteAllScalars=true]),\n"
        f"\t\t\t\t    #\"Tipo Alterado\" = Table.TransformColumnTypes(#\"Cabeçalhos Promovidos\",{{{tipos_m}}})\n"
        f"\t\t\t\tin\n"
        f"\t\t\t\t    #\"Tipo Alterado\"\n\n"
        f"annotation PBI_ResultType = Table\n"
    )

    #Caminhos dos arquivos e pastas

        #Pastas


    pasta_report = os.path.join(pasta_raiz, f"{nome_projeto}.Report")
    pasta_definition_report = os.path.join(pasta_report,'definition')
    pasta_pages = os.path.join(pasta_definition_report,'pages')
    pasta_pagina = os.path.join(pasta_pages, "pagina_01")
    pasta_visuals = os.path.join(pasta_pagina, "visuals")
    pasta_semanticmodel = os.path.join(pasta_raiz,f'{nome_projeto}.SemanticModel')
    pasta_definition_semanticmodel = os.path.join(pasta_semanticmodel,'definition')
    pasta_tables = os.path.join(pasta_definition_semanticmodel,'tables')


        #Arquivos

    arquivo_plataform_report = os.path.join(pasta_report, '.platform')
    arquivo_definition_pbir = os.path.join(pasta_report, 'definition.pbir')
    arquivo_version_json = os.path.join(pasta_definition_report, 'version.json')
    arquivo_report_json = os.path.join(pasta_definition_report, 'report.json')
    arquivo_pages_json = os.path.join(pasta_pages, 'pages.json')
    arquivo_page_json = os.path.join(pasta_pagina, 'page.json')
    arquivo_plataform_semanticmodel = os.path.join(pasta_semanticmodel, '.platform')
    arquivo_definition_pbism = os.path.join(pasta_semanticmodel, 'definition.pbism')
    arquivo_model_tmdl = os.path.join(pasta_definition_semanticmodel, 'model.tmdl')
    arquivo_database_tmdl = os.path.join(pasta_definition_semanticmodel, 'database.tmdl')
    arquivo_pbip = os.path.join(pasta_raiz, f"{nome_projeto}.pbip")
    arquivo_tmdl = os.path.join(pasta_tables, f"{nome_tabela}.tmdl")


    #Fazedor de pastas

    os.makedirs(pasta_raiz, exist_ok=True)
    os.makedirs(pasta_report, exist_ok=True)
    os.makedirs(pasta_definition_report, exist_ok=True)
    os.makedirs(pasta_pages, exist_ok=True)
    os.makedirs(pasta_semanticmodel, exist_ok=True)
    os.makedirs(pasta_definition_semanticmodel, exist_ok=True)
    os.makedirs(pasta_pagina, exist_ok=True)
    os.makedirs(pasta_visuals, exist_ok=True)
    os.makedirs(pasta_tables, exist_ok=True)

    #Fazedor de arquivos

    with open(arquivo_plataform_report, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_plataform_report, arquivo, indent=2)

    with open(arquivo_definition_pbir, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_definition_pbir, arquivo, indent=2)

    with open(arquivo_version_json, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_version_json, arquivo, indent=2)

    with open(arquivo_report_json, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_report_json, arquivo, indent=2)

    with open(arquivo_pages_json, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_pages_json, arquivo, indent=2)

    with open(arquivo_plataform_semanticmodel, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_plataform_semanticmodel, arquivo, indent=2)

    with open(arquivo_definition_pbism, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_definition_pbism, arquivo, indent=2)

    with open(arquivo_model_tmdl, 'w', encoding="utf-8") as arquivo:
        arquivo.write(texto_model_tmdl)

    with open(arquivo_database_tmdl, 'w', encoding="utf-8") as arquivo:
        arquivo.write(texto_database_tmdl)

    with open(arquivo_tmdl, 'w', encoding="utf-8") as arquivo:
        arquivo.write(texto_tmdl)

    with open(arquivo_page_json, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_page_json, arquivo, indent=2)

    with open(arquivo_pbip, 'w', encoding="utf-8") as arquivo:
        json.dump(dicionario_projeto_pbip, arquivo, indent=2)

    print(f"Projeto '{nome_projeto}' criado com sucesso em: {pasta_raiz}")
    return pasta_raiz

criar_pbip("ProjetoTeste", os.getcwd(),"C:\\Users\\Vinícius Abreu\\OneDrive\\Documentos\\Power BI\\Estudos\\vendas.csv")
