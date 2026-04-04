import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime

import aiofiles
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedDocument:
    file_path: str
    file_name: str
    file_hash: str
    file_size: int
    extracted_at: datetime
    regulator: str
    raw_content: Optional[bytes] = None


class PDFExtractor:
    def __init__(self):
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        
    def _compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]
    
    def _validate_file(self, file_path: Path) -> tuple[bool, str]:
        if not file_path.exists():
            return False, f"File not found: {file_path}"
        
        if file_path.suffix.lower() not in self.allowed_extensions:
            return False, f"Invalid extension: {file_path.suffix}"
        
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size:
            return False, f"File too large: {file_size} bytes (max: {self.max_file_size})"
        
        return True, "Valid"
    
    async def extract_from_path(
        self, 
        file_path: str, 
        regulator: str = "BI"
    ) -> ExtractedDocument:
        path = Path(file_path)
        is_valid, message = self._validate_file(path)
        
        if not is_valid:
            raise ValueError(message)
        
        async with aiofiles.open(path, "rb") as f:
            content = await f.read()
        
        file_hash = self._compute_hash(content)
        file_size = path.stat().st_size
        
        return ExtractedDocument(
            file_path=str(path.absolute()),
            file_name=path.name,
            file_hash=file_hash,
            file_size=file_size,
            extracted_at=datetime.utcnow(),
            regulator=regulator.upper(),
            raw_content=content
        )
    
    async def extract_from_upload(
        self,
        file: BinaryIO,
        filename: str,
        regulator: str = "BI"
    ) -> ExtractedDocument:
        content = await file.read()
        file_hash = self._compute_hash(content)
        file_size = len(content)
        
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes")
        
        return ExtractedDocument(
            file_path=f"upload://{filename}",
            file_name=filename,
            file_hash=file_hash,
            file_size=file_size,
            extracted_at=datetime.utcnow(),
            regulator=regulator.upper(),
            raw_content=content
        )


class PDFWatcher:
    def __init__(self, watch_dir: str, callback):
        self.watch_dir = Path(watch_dir)
        self.callback = callback
        self._processed_files: set[str] = set()
        
    def load_state(self, state_file: str = ".watcher_state"):
        state_path = self.watch_dir / state_file
        if state_path.exists():
            with open(state_path, "r") as f:
                self._processed_files = set(line.strip() for line in f)
    
    def save_state(self, state_file: str = ".watcher_state"):
        state_path = self.watch_dir / state_file
        with open(state_path, "w") as f:
            for file_hash in self._processed_files:
                f.write(f"{file_hash}\n")
    
    async def scan(self, regulator: str = "BI") -> list[ExtractedDocument]:
        extractor = PDFExtractor()
        documents = []
        
        for ext in self.allowed_extensions:
            for file_path in self.watch_dir.glob(f"*{ext}"):
                try:
                    doc = await extractor.extract_from_path(
                        str(file_path), 
                        regulator=regulator
                    )
                    if doc.file_hash not in self._processed_files:
                        documents.append(doc)
                        self._processed_files.add(doc.file_hash)
                except Exception as e:
                    logger.error(f"Error extracting {file_path}: {e}")
        
        self.save_state()
        return documents