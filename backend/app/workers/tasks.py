import logging
from celery import Celery
from datetime import datetime
from typing import Optional
import json

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "compliance_audit",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
)


@celery_app.task(bind=True, name="audit.analyze_sop")
def analyze_sop_task(
    self,
    clause: str,
    regulator: str = "all",
    top_k: int = 5,
    clause_id: Optional[str] = None,
    context: Optional[str] = None
) -> dict:
    from app.services.audit_service import AuditService
    
    logger.info(f"Starting async audit task: {self.request.id}")
    self.update_state(
        state="PROCESSING",
        meta={"clause_id": clause_id, "started_at": datetime.utcnow().isoformat()}
    )
    
    try:
        service = AuditService()
        import asyncio
        result = asyncio.run(service.analyze_sop(
            clause=clause,
            regulator=regulator,
            top_k=top_k,
            clause_id=clause_id,
            context=context,
            enable_tracking=True
        ))
        
        result["task_id"] = self.request.id
        result["completed_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Audit task completed: {self.request.id}")
        return result
        
    except Exception as e:
        logger.error(f"Audit task failed: {self.request.id}, error: {e}")
        self.update_state(
            state="FAILED",
            meta={"error": str(e), "clause_id": clause_id}
        )
        raise


@celery_app.task(bind=True, name="audit.batch_analyze")
def batch_analyze_task(
    self,
    clauses: list[dict],
    regulator: str = "all"
) -> dict:
    from app.services.audit_service import AuditService
    
    logger.info(f"Starting batch audit task: {self.request.id}, clauses: {len(clauses)}")
    
    results = []
    total = len(clauses)
    
    for i, clause_data in enumerate(clauses):
        self.update_state(
            state="PROCESSING",
            meta={
                "progress": i / total,
                "current": i + 1,
                "total": total,
                "clause_id": clause_data.get("clause_id")
            }
        )
        
        try:
            service = AuditService()
            import asyncio
            result = asyncio.run(service.analyze_sop(
                clause=clause_data.get("clause", ""),
                regulator=regulator,
                clause_id=clause_data.get("clause_id"),
                context=clause_data.get("context"),
                enable_tracking=False
            ))
            results.append(result)
        except Exception as e:
            results.append({
                "clause_id": clause_data.get("clause_id"),
                "error": str(e),
                "status": "FAILED"
            })
    
    compliant_count = sum(1 for r in results if r.get("final_status") == "COMPLIANT")
    
    logger.info(f"Batch audit completed: {self.request.id}")
    return {
        "task_id": self.request.id,
        "total": total,
        "compliant_count": compliant_count,
        "non_compliant_count": total - compliant_count,
        "completed_at": datetime.utcnow().isoformat(),
        "results": results
    }


@celery_app.task(bind=True, name="ingestion.process_pdf")
def process_pdf_task(
    self,
    file_path: str,
    regulator: str = "BI"
) -> dict:
    from app.pipeline.extractor import PDFExtractor
    from app.pipeline.parser import RegulationParser
    from app.pipeline.chunker import IngestionPipeline
    
    logger.info(f"Starting PDF processing task: {self.request.id}")
    self.update_state(
        state="EXTRACTING",
        meta={"file_path": file_path, "regulator": regulator}
    )
    
    try:
        import asyncio
        
        extractor = PDFExtractor()
        document = asyncio.run(extractor.extract_from_path(file_path, regulator))
        
        self.update_state(
            state="PARSING",
            meta={"file_name": document.file_name, "file_size": document.file_size}
        )
        
        parser = RegulationParser()
        parsed_doc = parser.parse(document)
        
        self.update_state(
            state="CHUNKING",
            meta={"sections": len(parsed_doc.sections)}
        )
        
        pipeline = IngestionPipeline()
        chunked_doc = pipeline.process(parsed_doc)
        
        logger.info(f"PDF processing completed: {self.request.id}")
        return {
            "task_id": self.request.id,
            "file_name": document.file_name,
            "regulator": regulator,
            "total_chunks": chunked_doc.total_chunks,
            "total_tokens": chunked_doc.total_tokens,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"PDF processing failed: {self.request.id}, error: {e}")
        self.update_state(
            state="FAILED",
            meta={"error": str(e), "file_path": file_path}
        )
        raise


@celery_app.task(bind=True, name="ingestion.watch_directory")
def watch_directory_task(self, watch_dir: str, regulator: str = "BI") -> dict:
    from app.pipeline.extractor import PDFWatcher
    
    logger.info(f"Starting directory watch task: {self.request.id}")
    
    try:
        import asyncio
        
        watcher = PDFWatcher(watch_dir, callback=None)
        watcher.load_state()
        
        documents = asyncio.run(watcher.scan(regulator))
        
        if documents:
            for doc in documents:
                process_pdf_task.delay(doc.file_path, regulator)
        
        logger.info(f"Directory watch completed: {self.request.id}, found {len(documents)} new files")
        return {
            "task_id": self.request.id,
            "watch_dir": watch_dir,
            "new_files": len(documents),
            "files": [d.file_name for d in documents]
        }
        
    except Exception as e:
        logger.error(f"Directory watch failed: {self.request.id}, error: {e}")
        raise


@celery_app.task(name="mlflow.sync_experiments")
def sync_experiments_task() -> dict:
    from app.ml.tracking import MLflowTracker
    
    logger.info("Starting MLflow sync task")
    
    try:
        tracker = MLflowTracker()
        experiments = tracker.list_experiments()
        
        experiment_data = []
        for exp in experiments:
            runs = tracker.list_runs(experiment_id=exp.experiment_id)
            experiment_data.append({
                "experiment_id": exp.experiment_id,
                "name": exp.name,
                "run_count": len(runs)
            })
        
        logger.info(f"MLflow sync completed: {len(experiments)} experiments")
        return {
            "synced_at": datetime.utcnow().isoformat(),
            "experiments": experiment_data
        }
        
    except Exception as e:
        logger.error(f"MLflow sync failed: {e}")
        raise