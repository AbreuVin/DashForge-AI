from src.models.project_spec import (
    ClientInfo,
    DataSource,
    MeasureSpec,
    PageSpec,
    ProjectSpec,
    ProjectStatus,
    TableProfile,
    VisualSpec,
    VisualType,
)


def make_minimal_spec() -> ProjectSpec:
    return ProjectSpec(
        id="test-001",
        client=ClientInfo(name="João", domain="vendas"),
        data_sources=[
            DataSource(
                filename="vendas.xlsx",
                tables=[TableProfile(name="Vendas", row_count=1000)],
            )
        ],
        pages=[
            PageSpec(
                id="page-1",
                name="Visão Geral",
                purpose="KPIs executivos",
                visuals=[
                    VisualSpec(
                        id="v1",
                        type=VisualType.card,
                        title="Receita Total",
                        measure_refs=["Receita Total"],
                    )
                ],
                confirmed=True,
            )
        ],
        measures=[MeasureSpec(name="Receita Total", dax="SUM(Vendas[Valor])")],
        status=ProjectStatus.confirmed,
    )


def test_spec_is_ready_to_build():
    spec = make_minimal_spec()
    assert spec.is_ready_to_build()


def test_spec_not_ready_when_open_questions():
    spec = make_minimal_spec()
    spec.add_open_question("Qual o período padrão?")
    assert not spec.is_ready_to_build()


def test_spec_not_ready_without_pages():
    spec = make_minimal_spec()
    spec.pages = []
    assert not spec.is_ready_to_build()


def test_spec_not_ready_without_data_source():
    spec = make_minimal_spec()
    spec.data_sources = []
    assert not spec.is_ready_to_build()


def test_spec_not_ready_when_status_is_collecting():
    spec = make_minimal_spec()
    spec.status = ProjectStatus.collecting
    assert not spec.is_ready_to_build()


def test_add_and_resolve_open_question():
    spec = make_minimal_spec()
    spec.add_open_question("Precisa de filtro por região?")
    assert "Precisa de filtro por região?" in spec.open_questions

    spec.resolve_question("Precisa de filtro por região?")
    assert spec.open_questions == []


def test_add_duplicate_question_is_ignored():
    spec = make_minimal_spec()
    spec.add_open_question("Pergunta X")
    spec.add_open_question("Pergunta X")
    assert spec.open_questions.count("Pergunta X") == 1


def test_spec_version_defaults_to_1():
    spec = ProjectSpec(id="x")
    assert spec.version == 1


def test_spec_serialization_roundtrip():
    spec = make_minimal_spec()
    data = spec.model_dump()
    restored = ProjectSpec.model_validate(data)
    assert restored.id == spec.id
    assert restored.pages[0].name == "Visão Geral"
    assert restored.measures[0].dax == "SUM(Vendas[Valor])"
