from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    collecting = "collecting"   # agente ainda coletando requisitos
    validating = "validating"   # agente validando consistência
    confirmed = "confirmed"     # usuário aprovou o que será feito
    building = "building"       # geração do .pbip em andamento
    ready = "ready"             # .pbip gerado, pronto para download
    iterating = "iterating"     # usuário pediu ajuste no projeto pronto


class VisualType(str, Enum):
    card = "card"
    bar_chart = "barChart"
    line_chart = "lineChart"
    pie_chart = "pieChart"
    table = "tableEx"
    matrix = "pivotTable"
    slicer = "slicer"
    area_chart = "areaChart"
    scatter = "scatterChart"
    map = "map"


class VisualSpec(BaseModel):
    id: str
    type: VisualType
    title: str
    description: str = ""
    measure_refs: list[str] = Field(default_factory=list)
    dimension_refs: list[str] = Field(default_factory=list)
    position: dict[str, float] = Field(default_factory=dict)


class PageSpec(BaseModel):
    id: str
    name: str
    purpose: str
    visuals: list[VisualSpec] = Field(default_factory=list)
    confirmed: bool = False


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    sample_values: list[Any] = Field(default_factory=list)
    null_pct: float = 0.0
    unique_count: int = 0


class TableProfile(BaseModel):
    name: str
    row_count: int
    columns: list[ColumnProfile] = Field(default_factory=list)


class DataSource(BaseModel):
    filename: str
    upload_path: str = ""
    tables: list[TableProfile] = Field(default_factory=list)


class MeasureSpec(BaseModel):
    name: str
    dax: str = ""
    description: str = ""
    confirmed: bool = False


class ClientInfo(BaseModel):
    name: str = ""
    domain: str = ""


class Iteration(BaseModel):
    version: int
    change_description: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectSpec(BaseModel):
    id: str
    version: int = 1
    status: ProjectStatus = ProjectStatus.collecting
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    client: ClientInfo = Field(default_factory=ClientInfo)
    data_sources: list[DataSource] = Field(default_factory=list)

    pages: list[PageSpec] = Field(default_factory=list)
    measures: list[MeasureSpec] = Field(default_factory=list)
    theme: str = "default"

    open_questions: list[str] = Field(default_factory=list)
    iterations: list[Iteration] = Field(default_factory=list)

    def is_ready_to_build(self) -> bool:
        """Spec tem informação mínima para iniciar o build."""
        return (
            bool(self.data_sources)
            and bool(self.pages)
            and not self.open_questions
            and self.status == ProjectStatus.confirmed
        )

    def add_open_question(self, question: str) -> None:
        if question not in self.open_questions:
            self.open_questions.append(question)

    def resolve_question(self, question: str) -> None:
        self.open_questions = [q for q in self.open_questions if q != question]
