import logging
from typing import Optional
from pathlib import Path

from app.config import settings
from app.core.exceptions import ComplianceAuditError

logger = logging.getLogger(__name__)


class RegulationService:
    def __init__(self):
        self.persist_dir = Path(settings.CHROMADB_PERSIST_DIR)
        self.collection_bi = settings.CHROMADB_COLLECTION_BI
        self.collection_ojk = settings.CHROMADB_COLLECTION_OJK
        
    def _get_collection(self, regulator: str):
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            
            collection_name = (
                self.collection_bi if regulator == "BI" 
                else self.collection_ojk if regulator == "OJK" 
                else None
            )
            
            if collection_name:
                return client.get_collection(name=collection_name)
            return None
        except Exception as e:
            logger.error(f"Failed to get collection: {e}")
            raise ComplianceAuditError(
                code="COLLECTION_ERROR",
                detail=f"Failed to access collection: {str(e)}",
                status_code=500
            )
    
    async def search(
        self,
        query: str,
        regulator: str = "all",
        top_k: int = 5
    ) -> list[dict]:
        try:
            import chromadb
            from openai import OpenAI
            
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            embedding_response = client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=query
            )
            query_embedding = embedding_response.data[0].embedding
            
            results = []
            regulators_to_search = (
                ["BI", "OJK"] if regulator == "all" 
                else [regulator]
            )
            
            for reg in regulators_to_search:
                collection = self._get_collection(reg)
                if collection is None:
                    continue
                
                search_results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"]
                )
                
                for i, doc in enumerate(search_results["documents"][0]):
                    results.append({
                        "content": doc,
                        "metadata": search_results["metadatas"][0][i],
                        "distance": search_results["distances"][0][i],
                        "regulator": reg
                    })
            
            results.sort(key=lambda x: x["distance"])
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise ComplianceAuditError(
                code="SEARCH_ERROR",
                detail=f"Search failed: {str(e)}",
                status_code=500
            )
    
    async def get_regulation_list(self) -> dict:
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            
            collections = {}
            for name, collection_name in [
                ("BI", self.collection_bi),
                ("OJK", self.collection_ojk)
            ]:
                try:
                    collection = client.get_collection(name=collection_name)
                    collections[name] = {
                        "name": collection_name,
                        "count": collection.count(),
                        "metadata": collection.metadata
                    }
                except Exception:
                    collections[name] = {
                        "name": collection_name,
                        "count": 0,
                        "metadata": {}
                    }
            
            return collections
        except Exception as e:
            logger.error(f"Failed to list regulations: {e}")
            raise ComplianceAuditError(
                code="LIST_ERROR",
                detail=f"Failed to list regulations: {str(e)}",
                status_code=500
            )
    
    async def get_articles(
        self,
        regulator: str,
        pasal: Optional[str] = None
    ) -> list[dict]:
        try:
            collection = self._get_collection(regulator)
            if collection is None:
                return []
            
            if pasal:
                results = collection.get(
                    where={"pasal": pasal},
                    include=["documents", "metadatas"]
                )
            else:
                results = collection.get(
                    include=["documents", "metadatas"]
                )
            
            articles = []
            for i, doc in enumerate(results["documents"]):
                articles.append({
                    "content": doc,
                    "metadata": results["metadatas"][i]
                })
            
            return articles
        except Exception as e:
            logger.error(f"Failed to get articles: {e}")
            raise ComplianceAuditError(
                code="ARTICLE_ERROR",
                detail=f"Failed to get articles: {str(e)}",
                status_code=500
            )