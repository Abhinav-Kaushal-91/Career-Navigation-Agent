"""Minimal OOXML loader for the project-owned golden dataset workbook."""

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .schemas import GoldenCase

_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def _column_index(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference)
    if letters is None:
        raise ValueError(f"invalid cell reference: {reference}")
    value = 0
    for letter in letters.group(0):
        value = value * 26 + ord(letter) - 64
    return value - 1


def _cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find(f"{{{_MAIN}}}v")
    if value is None or value.text is None:
        inline = cell.find(f"{{{_MAIN}}}is/{{{_MAIN}}}t")
        return inline.text or "" if inline is not None else ""
    if cell_type == "s":
        return shared_strings[int(value.text)]
    return value.text


def load_golden_cases(path: Path, sheet_name: str = "Golden Dataset") -> list[GoldenCase]:
    """Load the named sheet without adding a spreadsheet runtime dependency."""

    with zipfile.ZipFile(path) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(
            (
                item
                for item in workbook.findall(f".//{{{_MAIN}}}sheet")
                if item.attrib.get("name") == sheet_name
            ),
            None,
        )
        if sheet is None:
            raise ValueError(f"worksheet not found: {sheet_name}")
        relationship_id = sheet.attrib[f"{{{_REL}}}id"]
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship = next(
            item
            for item in relationships.findall(f"{{{_PKG_REL}}}Relationship")
            if item.attrib["Id"] == relationship_id
        )
        target = relationship.attrib["Target"].lstrip("/")
        worksheet_path = target if target.startswith("xl/") else f"xl/{target}"
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(node.text or "" for node in item.findall(f".//{{{_MAIN}}}t"))
                for item in root.findall(f"{{{_MAIN}}}si")
            ]
        worksheet = ElementTree.fromstring(archive.read(worksheet_path))

    rows: list[list[str]] = []
    for row in worksheet.findall(f".//{{{_MAIN}}}row"):
        values = [""] * 8
        for cell in row.findall(f"{{{_MAIN}}}c"):
            index = _column_index(cell.attrib["r"])
            if index < len(values):
                values[index] = _cell_text(cell, shared_strings)
        if values[0].startswith("GOLD-"):
            rows.append(values)
    cases = [
        GoldenCase(
            case_id=row[0],
            category=row[1],
            question=row[2],
            expected_answer=row[3],
            evaluation_mode=row[4],
            required_behavior=row[5],
            automatic_failure_conditions=row[6],
            priority=row[7],
        )
        for row in rows
    ]
    if len(cases) != 100 or len({case.case_id for case in cases}) != len(cases):
        raise ValueError("golden dataset must contain exactly 100 unique cases")
    return cases
