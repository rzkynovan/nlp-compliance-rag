export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

export const MLFLOW_URL =
  process.env.NEXT_PUBLIC_MLFLOW_URL || "http://localhost:5001";
