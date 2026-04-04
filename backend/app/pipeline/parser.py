import re
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from app.pipeline.extractor import ExtractedDocument

logger = logging.getLogger(__name__)


@dataclass
class ParsedSection:
    section_id: str
    title: str
    content: str
    level: int
    parent_id: Optional[str]
    children: list["ParsedSection"]
    metadata: dict


@dataclass
class ParsedDocument:
    document_id: str
    source_file: str
    regulator: str
    title: str
    parsed_at: datetime
    sections: list[ParsedSection]
    metadata: dict
    raw_text: str


class RegulationParser:
    SECTION_PATTERNS = {
        "pasal": re.compile(r"^Pasal\s+(\d+)", re.MULTILINE),
        "ayat": re.compile(r"^(\d+)\.\s+", re.MULTILINE),
        "huruf": re.compile(r"^([a-z])\.\s+", re.MULTILINE),
        "bab": re.compile(r"^BAB\s+([IVX]+)", re.MULTILINE),
        "bagian": re.compile(r"^Bagian\s+Ke(\d+)", re.MULTILINE),
    }
    
    def __init__(self):
        self.min_section_length = 50
        
    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        text = re.sub(r'[^\S\n]+\n', '\n', text)
        return text.strip()
    
    def _extract_sections(self, text: str) -> list[dict]:
        sections = []
        
        pasal_matches = list(self.SECTION_PATTERNS["pasal"].finditer(text))
        
        for i, match in enumerate(pasal_matches):
            start = match.start()
            end = pasal_matches[i + 1].start() if i + 1 < len(pasal_matches) else len(text)
            section_text = text[start:end].strip()
            
            section_id = f"pasal-{match.group(1)}"
            
            bab_match = self.SECTION_PATTERNS["bab"].search(text[:start])
            parent_id = f"bab-{bab_match.group(1)}" if bab_match else None
            
            sections.append({
                "section_id": section_id,
                "title": f"Pasal {match.group(1)}",
                "content": section_text,
                "level": 1,
                "parent_id": parent_id,
            })
        
        return sections
    
    def parse(self, document: ExtractedDocument) -> ParsedDocument:
        if document.raw_content is None:
            raise ValueError("Document has no raw content")
        
        text = document.raw_content.decode("utf-8", errors="ignore")
        cleaned_text = self._clean_text(text)
        
        sections_data = self._extract_sections(cleaned_text)
        
        sections = [
            ParsedSection(
                section_id=s["section_id"],
                title=s["title"],
                content=s["content"],
                level=s["level"],
                parent_id=s.get("parent_id"),
                children=[],
                metadata={"regulator": document.regulator}
            )
            for s in sections_data
            if len(s["content"]) >= self.min_section_length
        ]
        
        metadata = {
            "file_hash": document.file_hash,
            "file_size": document.file_size,
            "regulator": document.regulator,
        }
        
        return ParsedDocument(
            document_id=document.file_hash,
            source_file=document.file_name,
            regulator=document.regulator,
            title=document.file_name.replace(".pdf", "").replace(".md", ""),
            parsed_at=datetime.utcnow(),
            sections=sections,
            metadata=metadata,
            raw_text=cleaned_text
        )