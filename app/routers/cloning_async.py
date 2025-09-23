"""Async FastAPI router for cloning detection using global BigQuery client"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.modules.cloning_report.application.async_services import get_async_cloning_service, cleanup_async_service
from app.modules.cloning_report.domain.entities import CloningReport

router = APIRouter(prefix="/cloning", tags=["cloning-async"])


class CloningReportRequest(BaseModel):
    """Request model for cloning report generation"""
    plate: str
    date_start: datetime
    date_end: datetime
    output_dir: Optional[str] = "reports"


class CloningReportResponse(BaseModel):
    """Response model for cloning report"""
    plate: str
    start_date: datetime
    end_date: datetime
    report_path: str
    total_detections: int
    suspicious_pairs_count: int
    analysis_summary: dict


@router.post("/report/async", response_model=CloningReportResponse)
async def generate_async_cloning_report(request: CloningReportRequest):
    """
    Generate cloning detection report asynchronously using global BigQuery client
    
    This endpoint uses the async BigQuery repository that reuses the global
    BigQuery client instance from the main application, providing better
    performance and resource management.
    """
    service = get_async_cloning_service()
    
    try:
        report = await service.execute(
            plate=request.plate,
            date_start=request.date_start,
            date_end=request.date_end,
            output_dir=request.output_dir
        )
        
        return CloningReportResponse(
            plate=report.plate,
            start_date=report.start_date,
            end_date=report.end_date,
            report_path=report.report_path,
            total_detections=report.total_detections,
            suspicious_pairs_count=len(report.suspicious_pairs),
            analysis_summary=report.analysis_summary
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate cloning report: {str(e)}")
    
    finally:
        await service.close()


