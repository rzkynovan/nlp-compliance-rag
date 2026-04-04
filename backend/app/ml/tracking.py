import mlflow
from mlflow.tracking import MlflowClient
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
import json


class ExperimentTracker:
    def __init__(self, tracking_uri: str = "http://localhost:5000"):
        self.tracking_uri = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient(tracking_uri)
        self.current_run_id = None
    
    def start_run(
        self,
        experiment_name: str = "compliance-audit-rag",
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        mlflow.set_experiment(experiment_name)
        
        run = mlflow.start_run(tags=tags or {})
        self.current_run_id = run.info.run_id
        
        if params:
            mlflow.log_params(params)
        
        return self.current_run_id
    
    def log_metrics(self, run_id: str, metrics: Dict[str, float]):
        mlflow.log_metrics(metrics, run_id=run_id)
    
    def log_artifact(self, run_id: str, artifact_path: str):
        mlflow.log_artifact(artifact_path, run_id=run_id)
    
    def log_dict(self, run_id: str, dictionary: Dict[str, Any], artifact_file: str):
        mlflow.log_dict(dictionary, artifact_file, run_id=run_id)
    
    def end_run(self, run_id: Optional[str] = None):
        mlflow.end_run()
        if run_id == self.current_run_id or run_id is None:
            self.current_run_id = None
    
    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        try:
            run = self.client.get_run(run_id)
            return {
                "run_id": run.info.run_id,
                "experiment_id": run.info.experiment_id,
                "status": run.info.status,
                "start_time": datetime.fromtimestamp(run.info.start_time / 1000),
                "end_time": datetime.fromtimestamp(run.info.end_time / 1000) if run.info.end_time else None,
                "params": run.data.params,
                "metrics": run.data.metrics,
                "tags": run.data.tags
            }
        except Exception:
            return None
    
    def list_experiments(self, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        experiments = self.client.search_experiments()
        runs = []
        
        for exp in experiments:
            exp_runs = self.client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=limit
            )
            for run in exp_runs[skip:skip + limit]:
                runs.append({
                    "run_id": run.info.run_id,
                    "experiment_id": exp.experiment_id,
                    "experiment_name": exp.name,
                    "status": run.info.status,
                    "start_time": datetime.fromtimestamp(run.info.start_time / 1000),
                    "end_time": datetime.fromtimestamp(run.info.end_time / 1000) if run.info.end_time else None,
                    "params": run.data.params,
                    "metrics": run.data.metrics
                })
        
        return runs
    
    def compare_runs(self, run_ids: List[str]) -> Dict[str, Any]:
        runs_data = []
        metrics_keys = set()
        params_keys = set()
        
        for run_id in run_ids:
            run_data = self.get_run(run_id)
            if run_data:
                runs_data.append(run_data)
                metrics_keys.update(run_data["metrics"].keys())
                params_keys.update(run_data["params"].keys())
        
        comparison_table = []
        for run in runs_data:
            row = {"run_id": run["run_id"]}
            row.update({k: run["metrics"].get(k, None) for k in metrics_keys})
            row.update({k: run["params"].get(k, None) for k in params_keys})
            comparison_table.append(row)
        
        best_run = None
        best_metric = "recall"
        best_value = -1
        
        for run in runs_data:
            if best_metric in run["metrics"]:
                if run["metrics"][best_metric] > best_value:
                    best_value = run["metrics"][best_metric]
                    best_run = run["run_id"]
        
        return {
            "experiment_ids": run_ids,
            "comparison_table": comparison_table,
            "best_run_id": best_run or run_ids[0],
            "best_metric": best_metric,
            "metric_value": best_value
        }
    
    def get_artifacts(self, run_id: str) -> List[str]:
        artifacts = self.client.list_artifacts(run_id)
        return [artifact.path for artifact in artifacts]
    
    def get_run_start_time(self, run_id: str) -> datetime:
        run = self.get_run(run_id)
        return run["start_time"] if run else datetime.now()
    
    def log_audit_result(
        self,
        run_id: str,
        clause: str,
        verdict: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ):
        result_dict = {
            "clause": clause,
            "verdict": verdict,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat()
        }
        
        self.log_dict(run_id, result_dict, f"audit_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")