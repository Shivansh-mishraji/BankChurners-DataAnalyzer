"""
api/data.py
===========
FastAPI backend for Bank Churner Analytics Web Dashboard.
Serves the dataset, analytics, and CRUD operations as JSON endpoints.
"""

import io
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Shared dataset (singleton loaded once per worker) ─────────────────────────
_df: Optional[pd.DataFrame] = None
_ROOT = Path(__file__).parent.parent
CSV_PATH = _ROOT / "dataset.csv" if (_ROOT / "dataset.csv").exists() else _ROOT / "data" / "dataset.csv"


def _get_df() -> pd.DataFrame:
    global _df
    if _df is None:
        if not CSV_PATH.exists():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Dataset not found at {CSV_PATH}. Please place dataset.csv in the project root.",
            )
        _df = pd.read_csv(CSV_PATH)
        logger.info("Loaded %d records from %s", len(_df), CSV_PATH)
    return _df


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert DataFrame to JSON-safe records."""
    return json.loads(df.to_json(orient="records"))


# ── Pydantic models ───────────────────────────────────────────────────────────

class NewRecord(BaseModel):
    clientID: str
    Type: str
    age: int
    gender: str
    Dependent_count: int
    Educational_Level: str
    Marital_Status: str
    Income_Category: str
    Card_Category: str
    Months_on_book: int
    Total_Relationship_count: int
    Month_Inactive_12_month: int
    Contacts_count_12_mon: int
    Credit_Limit: float
    Total_Revolving_Bal: float
    Avg_Open_To_Buy: float
    Total_Amt_chng_Q4_Q1: float
    Total_Trans_Amt: float
    Total_Trans_Ct: int
    Total_Ct_Chng_Q4_Q1: float
    Average_Utilization_Ratio: float
    geography: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/overview")
async def get_overview():
    """High-level dataset statistics for the KPI cards."""
    df = _get_df()
    total = len(df)
    # Derive "high churn risk" as utilization > 0.7 (proxy since dataset has no attrition flag)
    high_risk_mask = df["Average_Utilization_Ratio"] > 0.7 if "Average_Utilization_Ratio" in df.columns else pd.Series([False]*total)
    churned = int(high_risk_mask.sum())
    churn_rate = round(churned / total * 100, 1) if total else 0
    avg_credit = round(float(df["Credit_Limit"].mean()), 2) if "Credit_Limit" in df.columns else 0
    avg_util = round(float(df["Average_Utilization_Ratio"].mean()) * 100, 1) if "Average_Utilization_Ratio" in df.columns else 0
    avg_age = round(float(df["age"].mean()), 1) if "age" in df.columns else 0
    avg_trans = round(float(df["Total_Trans_Amt"].mean()), 2) if "Total_Trans_Amt" in df.columns else 0

    return {
        "total_customers": total,
        "high_risk_customers": churned,
        "churned_customers": churned,
        "churn_rate_pct": churn_rate,
        "avg_credit_limit": avg_credit,
        "avg_utilization_pct": avg_util,
        "avg_age": avg_age,
        "avg_transaction_amt": avg_trans,
        "columns": list(df.columns),
    }


@router.get("/records")
async def get_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    gender: Optional[str] = None,
    card_category: Optional[str] = None,
    income_category: Optional[str] = None,
    geography: Optional[str] = None,
    customer_type: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
):
    """Paginated, filterable record list."""
    df = _get_df().copy()

    # Filters
    if search:
        mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        df = df[mask]
    if gender:
        df = df[df["gender"] == gender]
    if card_category:
        df = df[df["Card_Category"] == card_category]
    if income_category:
        df = df[df["Income_Category"] == income_category]
    if geography:
        df = df[df["geography"] == geography]
    if customer_type:
        df = df[df["Type"] == customer_type]

    # Sort
    if sort_by and sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=(sort_dir == "asc"))

    total = len(df)
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "records": _df_to_records(page_df),
    }


@router.get("/analytics/distribution")
async def get_distribution(column: str = Query(...)):
    """Value counts for any categorical column."""
    df = _get_df()
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found.")
    counts = df[column].value_counts().reset_index()
    counts.columns = ["label", "count"]
    total = counts["count"].sum()
    counts["pct"] = (counts["count"] / total * 100).round(1)
    return counts.to_dict(orient="records")


@router.get("/analytics/numeric-stats")
async def get_numeric_stats(column: str = Query(...)):
    """Descriptive statistics for a numeric column."""
    df = _get_df()
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found.")
    s = df[column]
    if not pd.api.types.is_numeric_dtype(s):
        raise HTTPException(status_code=400, detail=f"Column '{column}' is not numeric.")
    desc = s.describe()
    hist_counts, hist_edges = np.histogram(s.dropna(), bins=20)
    return {
        "column": column,
        "count": int(desc["count"]),
        "mean": round(float(desc["mean"]), 3),
        "std": round(float(desc["std"]), 3),
        "min": round(float(desc["min"]), 3),
        "q25": round(float(desc["25%"]), 3),
        "median": round(float(desc["50%"]), 3),
        "q75": round(float(desc["75%"]), 3),
        "max": round(float(desc["max"]), 3),
        "histogram": {
            "counts": hist_counts.tolist(),
            "edges": [round(float(e), 2) for e in hist_edges.tolist()],
        },
    }


@router.get("/analytics/churn-by")
async def churn_by(column: str = Query(...)):
    """High-risk rate breakdown by categorical column (util > 0.7 as proxy for churn risk)."""
    df = _get_df()
    if column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column}' not found.")
    if "Average_Utilization_Ratio" not in df.columns:
        raise HTTPException(status_code=400, detail="Utilization column not found.")
    df = df.copy()
    df["_high_risk"] = df["Average_Utilization_Ratio"] > 0.7
    grp = df.groupby(column)["_high_risk"].agg(["sum", "count"]).reset_index()
    grp.columns = [column, "churned", "total"]
    grp["churn_rate"] = (grp["churned"] / grp["total"] * 100).round(1)
    result = [
        {"label": str(row[column]), "total": int(row["total"]),
         "churned": int(row["churned"]), "churn_rate": float(row["churn_rate"])}
        for _, row in grp.iterrows()
    ]
    return sorted(result, key=lambda x: x["churn_rate"], reverse=True)


@router.get("/analytics/correlation")
async def get_correlation():
    """Correlation matrix for numeric columns (top pairs)."""
    df = _get_df()
    num_df = df.select_dtypes(include=[np.number])
    corr = num_df.corr()
    # Return top 20 correlated pairs (excluding self-correlation)
    pairs = []
    cols = corr.columns.tolist()
    for i, c1 in enumerate(cols):
        for j, c2 in enumerate(cols):
            if j <= i:
                continue
            pairs.append({"col1": c1, "col2": c2, "corr": round(float(corr.loc[c1, c2]), 3)})
    pairs.sort(key=lambda x: abs(x["corr"]), reverse=True)
    return pairs[:25]


@router.get("/analytics/scatter")
async def get_scatter(
    x: str = Query(...),
    y: str = Query(...),
    color_by: Optional[str] = None,
    sample: int = Query(500, ge=50, le=2000),
):
    """Scatter plot data (sampled)."""
    df = _get_df()
    for col in [x, y]:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' not found.")
    sub = df[[x, y] + ([color_by] if color_by and color_by in df.columns else [])].dropna()
    if len(sub) > sample:
        sub = sub.sample(sample, random_state=42)
    return _df_to_records(sub)


@router.post("/records", status_code=201)
async def add_record(record: NewRecord):
    """Add a new customer record."""
    global _df
    df = _get_df()
    new_row = pd.DataFrame([record.model_dump()])
    _df = pd.concat([df, new_row], ignore_index=True)
    logger.info("Added record: %s", record.clientID)
    return {"message": "Record added", "total": len(_df)}


@router.delete("/records/{index}")
async def delete_record(index: int):
    """Delete a record by integer index."""
    global _df
    df = _get_df()
    if index < 0 or index >= len(df):
        raise HTTPException(status_code=404, detail=f"Record at index {index} not found.")
    _df = df.drop(df.index[index]).reset_index(drop=True)
    logger.info("Deleted record at index %d", index)
    return {"message": "Record deleted", "total": len(_df)}


@router.get("/export/csv")
async def export_csv():
    """Export full dataset as CSV download."""
    df = _get_df()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bank_churners_export.csv"},
    )


@router.get("/export/json")
async def export_json():
    """Export full dataset as JSON download."""
    df = _get_df()
    buf = io.StringIO()
    df.to_json(buf, orient="records", indent=2)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=bank_churners_export.json"},
    )


@router.get("/filters/options")
async def get_filter_options():
    """Unique values for all filter dropdowns."""
    df = _get_df()
    return {
        "gender": sorted(df["gender"].dropna().unique().tolist()) if "gender" in df.columns else [],
        "card_category": sorted(df["Card_Category"].dropna().unique().tolist()) if "Card_Category" in df.columns else [],
        "income_category": sorted(df["Income_Category"].dropna().unique().tolist()) if "Income_Category" in df.columns else [],
        "geography": sorted(df["geography"].dropna().unique().tolist()) if "geography" in df.columns else [],
        "customer_type": sorted(df["Type"].dropna().unique().tolist()) if "Type" in df.columns else [],
        "education": sorted(df["Educational_Level"].dropna().unique().tolist()) if "Educational_Level" in df.columns else [],
        "marital_status": sorted(df["Marital_Status"].dropna().unique().tolist()) if "Marital_Status" in df.columns else [],
    }
