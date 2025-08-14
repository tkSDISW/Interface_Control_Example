"""
interface_parser.py
-------------------
Reusable module to parse Markdown headings from a CSV 'description' field
into dynamic Python objects.

Usage:
    from interface_parser import InterfaceIssueParser

    parser = InterfaceIssueParser("your.csv", description_col="description")
    parser.load()
    parser.build_objects()

    # Get all objects having a specific heading
    process_objs = parser.get_by_section_presence("Process Interface Information")

    # Convert to a DataFrame with only specific sections
    df = parser.to_dataframe(process_objs, include_sections=["Process Interface Information"])
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd
import re

def slugify(heading: str) -> str:
    s = heading.strip()
    s = re.sub(r'^[#\s]+', '', s)
    s = re.sub(r'\s+', ' ', s)
    s = s.strip().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = s.strip('_')
    if not s:
        s = "section"
    if not re.match(r'^[a-z_]', s):
        s = "_" + s
    return s

@dataclass
class DescriptionObject:
    source_index: int
    raw_description: str
    sections: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        for k, v in self.sections.items():
            setattr(self, k, v)

class InterfaceIssueParser:
    def __init__(self, csv_path: str, description_col: str = "description"):
        self.csv_path = csv_path
        self.description_col = description_col
        self.df: Optional[pd.DataFrame] = None
        self.objects: List[DescriptionObject] = []

    @staticmethod
    def parse_markdown_sections(md: str) -> Dict[str, str]:
        if not isinstance(md, str) or not md.strip():
            return {}
        text = md.replace('\\r\\n', '\\n').replace('\\r', '\\n')
        heading_regex = re.compile(r'^(#{1,6})\\s*(.+?)\\s*$', re.MULTILINE)
        sections = {}
        matches = list(heading_regex.finditer(text))
        if not matches:
            return {}
        for i, m in enumerate(matches):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            heading_text = m.group(2).strip()
            key = slugify(heading_text)
            content = text[start:end].strip()
            base_key = key
            counter = 2
            while key in sections:
                key = f"{base_key}_{counter}"
                counter += 1
            sections[key] = content
        return sections

    def load(self):
        self.df = pd.read_csv(self.csv_path, encoding="utf-8", engine="python")
        if self.description_col not in self.df.columns:
            lower_map = {c.lower(): c for c in self.df.columns}
            if self.description_col.lower() in lower_map:
                self.description_col = lower_map[self.description_col.lower()]
            else:
                raise KeyError(
                    f"Column '{self.description_col}' not found. Available: {list(self.df.columns)}"
                )

    def build_objects(self):
        if self.df is None:
            self.load()
        self.objects = []
        for idx, row in self.df.iterrows():
            desc = row.get(self.description_col, "")
            sections = self.parse_markdown_sections(desc)
            obj = DescriptionObject(source_index=idx, raw_description=desc, sections=sections)
            self.objects.append(obj)

    def get_by_section_presence(self, section_heading: str) -> List[DescriptionObject]:
        key = slugify(section_heading)
        return [o for o in self.objects if hasattr(o, key) and getattr(o, key).strip()]

    def to_dataframe(self, objects: List[DescriptionObject], include_sections: Optional[List[str]] = None) -> pd.DataFrame:
        records = []
        for o in objects:
            row = {"source_index": o.source_index}
            if include_sections:
                for h in include_sections:
                    k = slugify(h)
                    row[k] = getattr(o, k, "")
            else:
                for k, v in o.sections.items():
                    row[k] = v
            records.append(row)
        return pd.DataFrame(records)
