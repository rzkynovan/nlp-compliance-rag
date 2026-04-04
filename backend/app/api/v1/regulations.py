from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models.regulation import (
    RegulationMetadata, RegulationListResponse,
    ChunkSearchRequest, ChunkSearchResponse, ChunkMetadata, Regulator
)
from app.config import settings
import chromadb

router = APIRouter()


def get_chroma_client():
    return chromadb.PersistentClient(path=settings.CHROMADB_PERSIST_DIR)


@router.get("/list", response_model=RegulationListResponse)
async def list_regulations():
    client = get_chroma_client()
    
    regulations = []
    
    try:
        bi_collection = client.get_collection(settings.CHROMADB_COLLECTION_BI)
        bi_metadata = bi_collection.get(limit=1)
        
        regulations.append(RegulationMetadata(
            document_id="PBI_22_23_2020",
            document_name="Peraturan Bank Indonesia No. 22/23/PBI/2020",
            regulator=Regulator.BI,
            year=2020,
            total_pages=96,
            total_chunks=bi_collection.count(),
            status="active"
        ))
    except Exception:
        pass
    
    try:
        ojk_collection = client.get_collection(settings.CHROMADB_COLLECTION_OJK)
        
        regulations.append(RegulationMetadata(
            document_id="POJK_22_2023",
            document_name="Peraturan OJK No. 22 Tahun 2023",
            regulator=Regulator.OJK,
            year=2023,
            total_pages=131,
            total_chunks=ojk_collection.count(),
            status="active"
        ))
    except Exception:
        pass
    
    return RegulationListResponse(
        regulations=regulations,
        total=len(regulations)
    )


@router.post("/search", response_model=ChunkSearchResponse)
async def search_chunks(request: ChunkSearchRequest):
    import time
    start_time = time.time()
    
    client = get_chroma_client()
    
    from llama_index.embeddings.openai import OpenAIEmbedding
    embed_model = OpenAIEmbedding(model=settings.EMBEDDING_MODEL)
    query_embedding = embed_model.get_text_embedding(request.query)
    
    chunks = []
    
    collections_to_search = []
    if request.regulator:
        if request.regulator == Regulator.BI:
            collections_to_search.append(settings.CHROMADB_COLLECTION_BI)
        else:
            collections_to_search.append(settings.CHROMADB_COLLECTION_OJK)
    else:
        collections_to_search = [
            settings.CHROMADB_COLLECTION_BI,
            settings.CHROMADB_COLLECTION_OJK
        ]
    
    for collection_name in collections_to_search:
        try:
            collection = client.get_collection(collection_name)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=request.top_k
            )
            
            for i in range(len(results["ids"][0])):
                chunk = ChunkMetadata(
                    chunk_id=results["ids"][0][i],
                    document_id=results["metadatas"][0][i].get("document_id", ""),
                    regulator=Regulator.BI if "BI" in collection_name else Regulator.OJK,
                    chapter=results["metadatas"][0][i].get("BAB", ""),
                    article=results["metadatas"][0][i].get("Pasal", ""),
                    verse=results["metadatas"][0][i].get("Ayat", ""),
                    content=results["documents"][0][i],
                    embedding_model=settings.EMBEDDING_MODEL
                )
                chunks.append(chunk)
        except Exception:
            continue
    
    latency_ms = (time.time() - start_time) * 1000
    
    return ChunkSearchResponse(
        query=request.query,
        chunks=chunks[:request.top_k],
        total=len(chunks),
        latency_ms=latency_ms
    )


@router.get("/{document_id}/stats")
async def get_regulation_stats(document_id: str):
    client = get_chroma_client()
    
    collection_name = None
    if "PBI" in document_id or "BI" in document_id:
        collection_name = settings.CHROMADB_COLLECTION_BI
    elif "POJK" in document_id or "OJK" in document_id:
        collection_name = settings.CHROMADB_COLLECTION_OJK
    
    if not collection_name:
        raise HTTPException(status_code=404, detail="Regulation not found")
    
    try:
        collection = client.get_collection(collection_name)
        return {
            "document_id": document_id,
            "total_chunks": collection.count(),
            "collection_name": collection_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))