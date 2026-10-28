"""Explicit Summary aliases and isolated sprint/CR blocks for EVA ingestion.

Inspired by msp_qa's description_parser/block_splitter. Unknown labels and
conflicts are evidence to review, never fuzzy guesses or last-value wins.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser


def normalize(value: str) -> str:
    """Compare labels without accents, punctuation or repeated spaces."""
    text = unicodedata.normalize("NFKD", value).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


FIELD_ALIASES = {
    "project_id": (
        "project id",
        "id proyecto",
        "id del proyecto",
        "codigo de proyecto",
        "código",
        "id",
    ),
    "delivery_manager": (
        "delivery manager",
        "delivery manager name",
        "dm",
        "gerente de entrega",
        "responsable delivery",
    ),
    "service": (
        "service",
        "service type",
        "tipo de servicio",
        "servicio",
        "tipo de servico",
    ),
    "project_name": (
        "project name",
        "nombre del proyecto",
        "nombre proyecto",
        "nome do projeto",
        "proyecto",
    ),
    "client": (
        "client",
        "cliente",
        "empresa",
        "company",
        "customer",
        "account",
        "cuenta",
    ),
    "start": (
        "start",
        "start date",
        "estimated start date",
        "fecha inicio",
        "fecha de inicio",
        "fecha de inicio de proyecto",
        "fecha de inicio del proyecto",
        "fecha de inicio estimada",
        "data de inicio",
    ),
    "finish": (
        "finish",
        "finish date",
        "end date",
        "estimated end date",
        "fecha fin",
        "fecha de fin",
        "fecha estimada de fin",
        "fecha estimada de fin de proyecto",
        "fecha estimada de fin del proyecto",
        "fecha estimada de finalizacion",
        "estimated time of delivery",
        "fecha de termino",
        "data de fim",
    ),
    "budget": (
        "budget",
        "budget hrs",
        "budget hours",
        "presupuesto",
        "presupuesto horas",
        "horas presupuestadas",
        "horas estimadas",
        "estimated hours",
        "horas",
        "horas totales",
        "horas totais",
        "hours",
        "total hours",
    ),
    "status": (
        "status",
        "state",
        "estado",
        "estatus",
        "project status",
        "estado del proyecto",
    ),
}
ALIASES = {
    normalize(alias): key
    for key, aliases in FIELD_ALIASES.items()
    for alias in aliases
}
KNOWN_METADATA = frozenset(
    normalize(label)
    for label in (
        "pm",
        "project manager",
        "bp",
        "cmmi",
        "gerente de cuenta",
        "analista de procesos",
        "analyst",
        "qc",
        "quality control reviewer",
        "lider de tecnico",
        "lider de celula dev",
        "lider de celula sec",
        "research team leader",
        "sm",
        "ba",
        "arq",
        "code review",
        "arquitectos",
        "process owner",
        "quality control",
        "pm shadow",
        "analyst dev",
        "desarrollador rpa",
        "arquitecto rpa",
        "desarrollador 1",
        "desarrollador 2",
        "desarrollador 3",
        "scrum master",
        "business analyst",
        "analista de negocio",
        "arquitecto",
        "arquiteto",
        "architect",
        "solution architect",
        "technical lead",
        "tech lead",
        "lider tecnico",
        "desarrollador",
        "desarrolladores",
        "developer",
        "developers",
        "desenvolvedor",
        "desenvolvedores",
        "dev",
        "devs",
        "dev rpa",
        "dev power bi",
        "ml engineer",
        "machine learning engineer",
        "data engineer",
        "data enginer",
        "date enginer",
        "tester",
        "testers",
        "qa",
        "code reviewer",
        "code reviewers",
        "revisor qc",
        "duracion",
        "duracion estimada",
        "duration",
        "estimated duration",
        "duracao",
        "numero de sprint",
        "numero de sprints",
        "number of sprints",
        "sprints",
    )
)
SHARED_FIELDS = frozenset(
    {"delivery_manager", "service", "client", "project_name"}
)
HEADER = re.compile(
    r"^(?:(?:sprint|sprint number|iteracion|iteration|s)\s*#?\s*0*(\d+)"
    r"|(?:change[\s_-]*requests?|solicitud de cambio|cr|cambio de alcance)"
    r"\s*#?\s*0*(\d*))\s*[:.\-]?$",
    re.IGNORECASE,
)
SCOPED_LABEL = re.compile(r"^(.+?)\s+(s\d+|cr\d*)$", re.IGNORECASE)
COMPOSITE = re.compile(
    r"^(?:change requests?|solicitud de cambio|cr)\s*(\d*)"
    r"\s+(?:sprint|sprnt|s)\s*(\d+)$",
    re.IGNORECASE,
)


class _Text(HTMLParser):
    """HTML descriptions converted to lines, including table cell pairs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        if not self.hidden and tag in {
            "br",
            "p",
            "div",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
        }:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        elif not self.hidden and tag in {"td", "th"}:
            self.parts.append("\t")
        elif not self.hidden and tag in {
            "p",
            "div",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
        }:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


@dataclass
class SummaryBlock:
    """One explicit business scope; empty code denotes an unsuffixed scope."""

    code: str
    fields: dict[str, str] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    unknown_labels: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    conflicted: set[str] = field(default_factory=set)


def _code(value: str) -> str:
    text = value.upper()
    # Keep CR and CR1 distinct: no evidence that both are the same scope.
    match = re.fullmatch(r"(S|CR)(\d*)", text)
    return f"{match[1]}{int(match[2]) if match[2] else ''}" if match else text


def parse_summary(description: str) -> list[SummaryBlock]:
    """Parse text/HTML, preserving independent budgets/dates/IDs per block.

    Shared people/service/name metadata can be inherited from the preamble;
    its budget, dates and status never propagate to sprint/CR children.
    """
    parser = _Text()
    parser.feed(description)
    blocks: dict[str, SummaryBlock] = {"": SummaryBlock("")}
    current = blocks[""]
    seen_headers: set[str] = set()
    for raw in "".join(parser.parts).splitlines():
        line = raw.strip().strip("* ")
        if not line:
            continue
        normalized = normalize(line)
        header = HEADER.fullmatch(normalized.replace("number ", ""))
        composite = COMPOSITE.fullmatch(normalized)
        if header or composite:
            code = (
                f"CR{int(composite[1]) if composite[1] else ''}"
                f"_S{int(composite[2])}"
                if composite
                else f"S{int(header[1])}"
                if header[1]
                else (f"CR{int(header[2])}" if header[2] else "CR")
            )
            current = blocks.setdefault(code, SummaryBlock(code))
            if code in seen_headers:
                current.issues.append("duplicate_block")
            seen_headers.add(code)
            continue
        pair = re.split(r"\s*[:：]\s*|\t+", line, maxsplit=1)
        if len(pair) != 2:
            current.issues.append(f"unparsed_line:{line[:80]}")
            continue
        label, value = normalize(pair[0]), pair[1].strip()
        target = current
        scoped = SCOPED_LABEL.fullmatch(label)
        if scoped and scoped[1] in ALIASES:
            label, code = scoped[1], _code(scoped[2])
            if not (
                code == current.code
                or (code == "CR" and current.code.startswith("CR"))
                or current.code.endswith(f"_{code}")
            ):
                target = blocks.setdefault(code, SummaryBlock(code))
        key = ALIASES.get(label)
        if not key:
            if label in KNOWN_METADATA:
                target.metadata[label] = value
            else:
                target.unknown_labels.append(pair[0].strip())
            continue
        if not value:
            continue
        if key in target.conflicted:
            continue
        if key in target.fields and target.fields[key] != value:
            target.issues.append(f"conflicting_field:{key}")
            target.conflicted.add(key)
            target.fields.pop(key)
        else:
            target.fields[key] = value
    preamble = blocks[""]
    children = [block for code, block in blocks.items() if code]
    for child in children:
        for key in SHARED_FIELDS:
            if key not in child.conflicted and key in preamble.fields:
                child.fields.setdefault(key, preamble.fields[key])
    if not children or any(
        key in preamble.fields
        for key in {"budget", "start", "finish", "project_id"}
    ):
        return list(blocks.values())
    if preamble.issues or preamble.unknown_labels:
        return list(blocks.values())
    return children
