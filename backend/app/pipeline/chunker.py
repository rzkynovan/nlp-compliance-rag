import re
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from app.pipeline.parser import ParsedDocument, ParsedSection

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    section_id: str
    content: str
    chunk_index: int
    token_count: int
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list[float]] = None


@dataclass
class ChunkedDocument:
    document_id: str
    source_file: str
    regulator: str
    chunks: list[Chunk]
    chunked_at: datetime
    total_chunks: int
    total_tokens: int


class SemanticChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def _estimate_tokens(self, text: str) -> int:
        return len(text.split())
    
    def _generate_chunk_id(self, document_id: str, content: str, index: int) -> str:
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{document_id}-chunk-{index}-{content_hash}"
    
    def _split_by_sentence(self, text: str) -> list[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_overlapping_chunks(
        self,
        sentences: list[str],
        section_id: str,
        document_id: str,
        start_index: int
    ) -> list[Chunk]:
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = start_index
        
        for sentence in sentences:
            sentence_tokens = self._estimate_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size and current_chunk:
                chunk_content = " ".join(current_chunk)
                
                if len(chunk_content) >= self.min_chunk_size:
                    chunk = Chunk(
                        chunk_id=self._generate_chunk_id(document_id, chunk_content, chunk_index),
                        document_id=document_id,
                        section_id=section_id,
                        content=chunk_content,
                        chunk_index=chunk_index,
                        token_count=current_tokens,
                        metadata={
                            "created_at": datetime.utcnow().isoformat()
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                if self.chunk_overlap > 0 and len(current_chunk) > 1:
                    overlap_sentences = []
                    overlap_tokens = 0
                    for s in reversed(current_chunk[:-1]):
                        s_tokens = self._estimate_tokens(s)
                        if overlap_tokens + s_tokens <= self.chunk_overlap:
                            overlap_sentences.insert(0, s)
                            overlap_tokens += s_tokens
                        else:
                            break
                    current_chunk = overlap_sentences + [sentence]
                    current_tokens = sum(self._estimate_tokens(s) for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            if len(chunk_content) >= self.min_chunk_size:
                chunk = Chunk(
                    chunk_id=self._generate_chunk_id(document_id, chunk_content, chunk_index),
                    document_id=document_id,
                    section_id=section_id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    token_count=current_tokens,
                    metadata={
                        "created_at": datetime.utcnow().isoformat()
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def chunk(self, document: ParsedDocument) -> ChunkedDocument:
        all_chunks = []
        current_chunk_index = 0
        
        for section in document.sections:
            sentences = self._split_by_sentence(section.content)
            section_chunks = self._create_overlapping_chunks(
                sentences,
                section.section_id,
                document.document_id,
                current_chunk_index
            )
            
            for chunk in section_chunks:
                chunk.metadata.update({
                    "section_title": section.title,
                    "regulator": document.regulator,
                    "source_file": document.source_file,
                })
            
            all_chunks.extend(section_chunks)
            current_chunk_index = len(all_chunks)
        
        total_tokens = sum(c.token_count for c in all_chunks)
        
        return ChunkedDocument(
            document_id=document.document_id,
            source_file=document.source_file,
            regulator=document.regulator,
            chunks=all_chunks,
            chunked_at=datetime.utcnow(),
            total_chunks=len(all_chunks),
            total_tokens=total_tokens
        )


class IngestionPipeline:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        self.chunker = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def process(self, document: ParsedDocument) -> ChunkedDocument:
        return self.chunker.chunk(document)
    
    def process_batch(
        self, 
        documents: list[ParsedDocument]
    ) -> list[ChunkedDocument]:
        return [self.process(doc) for doc in documents]