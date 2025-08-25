# -*- coding: utf-8 -*-
"""
BigQuery service for handling Google Cloud BigQuery operations.

This service encapsulates all BigQuery interactions for traffic analysis,
radar data, and vehicle tracking queries.
"""
from typing import List, Optional, Tuple

import pendulum
from google.cloud import bigquery
from loguru import logger

from app import config
from app.pydantic_models import (
    CarPassageOut,
    GetCarsByRadarIn,
    NPlatesBeforeAfterOut,
    Path,
)
from app.utils import (
    build_hint_query,
    build_n_plates_query,
    build_positions_query,
    build_get_car_by_radar_query,
    get_bigquery_client,
)


class BigQueryService:
    """Service for BigQuery operations and traffic analysis."""

    @staticmethod
    async def get_vehicle_hints(
        plate: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        latitude_min: Optional[float] = None,
        latitude_max: Optional[float] = None,
        longitude_min: Optional[float] = None,
        longitude_max: Optional[float] = None,
    ) -> List[str]:
        """
        Get vehicle plate hints based on location and time filters.
        
        Args:
            plate: Vehicle license plate
            start_time: Start time for search
            end_time: End time for search
            latitude_min: Minimum latitude
            latitude_max: Maximum latitude
            longitude_min: Minimum longitude
            longitude_max: Maximum longitude
            
        Returns:
            List of plate suggestions
        """
        logger.debug(f"Getting vehicle hints for plate {plate}")
        
        query = build_hint_query(
            placa=plate,
            min_datetime=start_time,
            max_datetime=end_time,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
        )
        
        client = get_bigquery_client()
        query_job = client.query(query)
        results = query_job.result()
        
        return [row.placa for row in results]

    @staticmethod
    async def get_vehicle_path(
        plate: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        max_time_interval: int = 3600,
        polyline: bool = False,
    ) -> List[Path]:
        """
        Get vehicle movement path over time.
        
        Args:
            plate: Vehicle license plate
            start_time: Start time for path
            end_time: End time for path
            max_time_interval: Maximum time interval in seconds
            polyline: Whether to include polyline data
            
        Returns:
            List of path points
        """
        logger.debug(f"Getting vehicle path for plate {plate}")
        
        query = build_positions_query(
            placa=plate,
            min_datetime=start_time,
            max_datetime=end_time,
        )
        
        client = get_bigquery_client()
        query_job = client.query(query)
        results = query_job.result()
        
        path_data = []
        for row in results:
            path_data.append(Path(
                datahora_equipamento=row.datahora_equipamento,
                latitude=row.latitude,
                longitude=row.longitude,
                location=row.location,
                radars=row.radars,
                # Add other fields as needed
            ))
        
        return path_data

    @staticmethod
    async def get_plates_before_after(
        plate: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        n_minutes: int,
        n_plates: int = 10,
    ) -> List[NPlatesBeforeAfterOut]:
        """
        Get plates detected before and after a specific plate.
        
        Args:
            plate: Reference vehicle license plate
            start_time: Start time for search
            end_time: End time for search
            n_minutes: Time window in minutes
            n_plates: Number of plates to return
            
        Returns:
            List of plates detected in the time window
        """
        logger.debug(f"Getting plates before/after {plate}")
        
        query, params = build_n_plates_query(
            placa=plate,
            min_datetime=start_time,
            max_datetime=end_time,
            n_minutes=n_minutes,
            n_plates=n_plates,
        )
        
        client = get_bigquery_client()
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        plates_data = []
        for row in results:
            plates_data.append(NPlatesBeforeAfterOut(
                id_detection=row.id_detection,
                detection_time=row.detection_time,
                id_camera_groups=row.id_camera_groups,
                radars=row.radars,
                location=row.location,
                latitude=row.latitude,
                longitude=row.longitude,
                plates_before=row.plates_before,
                plates_after=row.plates_after,
            ))
        
        return plates_data

    @staticmethod
    async def get_cars_by_radar(data: GetCarsByRadarIn) -> List[CarPassageOut]:
        """
        Get cars detected by specific radar.
        
        Args:
            data: Radar query parameters
            
        Returns:
            List of car passages
        """
        logger.debug(f"Getting cars by radar: {data.radar_id}")
        
        query = build_get_car_by_radar_query(
            radar_id=data.radar_id,
            start_time=data.start_time,
            end_time=data.end_time,
            plate_filter=data.plate_filter,
        )
        
        client = get_bigquery_client()
        query_job = client.query(query)
        results = query_job.result()
        
        car_passages = []
        for row in results:
            car_passages.append(CarPassageOut(
                placa=row.placa,
                datahora_equipamento=row.datahora_equipamento,
                latitude=row.latitude,
                longitude=row.longitude,
                radar_id=row.radar_id,
                location=row.location,
                # Add other fields as needed
            ))
        
        return car_passages

    @staticmethod
    def _build_time_filter(
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        time_column: str = "datahora_equipamento"
    ) -> str:
        """Build time filter for BigQuery queries."""
        return f"""
            {time_column} BETWEEN 
            TIMESTAMP('{start_time.to_iso8601_string()}') 
            AND TIMESTAMP('{end_time.to_iso8601_string()}')
        """

    @staticmethod
    async def get_vehicle_hints_raw(
        plate: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        latitude_min: Optional[float] = None,
        latitude_max: Optional[float] = None,
        longitude_min: Optional[float] = None,
        longitude_max: Optional[float] = None,
    ) -> List[str]:
        """
        Get vehicle plate hints using raw utils function (for backward compatibility).
        
        This method maintains the exact same interface as the utils.get_hints function
        but organizes it within the service layer pattern.
        """
        from app.utils import get_hints
        
        return await get_hints(
            placa=plate,
            min_datetime=start_time,
            max_datetime=end_time,
            latitude_min=latitude_min,
            latitude_max=latitude_max,
            longitude_min=longitude_min,
            longitude_max=longitude_max,
        )

    @staticmethod
    async def get_vehicle_path_raw(
        plate: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        max_time_interval: int = 3600,
        polyline: bool = False,
    ) -> List[dict]:
        """
        Get vehicle path using raw utils function (for backward compatibility).
        """
        from app.utils import get_path
        
        return await get_path(
            placa=plate,
            min_datetime=start_time,
            max_datetime=end_time,
            max_time_interval=max_time_interval,
            polyline=polyline,
        )

    @staticmethod
    def get_plates_before_after_raw(
        plate: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        n_minutes: int,
        n_plates: int = 10,
    ) -> List[NPlatesBeforeAfterOut]:
        """
        Get plates before/after using raw utils function (for backward compatibility).
        """
        from app.utils import get_n_plates_before_and_after
        
        return get_n_plates_before_and_after(
            placa=plate,
            min_datetime=start_time,
            max_datetime=end_time,
            n_minutes=n_minutes,
            n_plates=n_plates,
        )

    @staticmethod
    async def get_cars_by_radar_raw(
        radar_id: str,
        start_time: pendulum.DateTime,
        end_time: pendulum.DateTime,
        plate_hint: Optional[str] = None,
    ) -> List[CarPassageOut]:
        """
        Get cars by radar using raw utils function (for backward compatibility).
        """
        from app.utils import get_car_by_radar
        
        return await get_car_by_radar(
            codcet=radar_id,
            min_datetime=start_time,
            max_datetime=end_time,
            plate_hint=plate_hint,
        )

    @staticmethod
    def _build_location_filter(
        latitude_min: Optional[float],
        latitude_max: Optional[float], 
        longitude_min: Optional[float],
        longitude_max: Optional[float],
    ) -> str:
        """Build location filter for BigQuery queries."""
        filters = []
        
        if latitude_min is not None:
            filters.append(f"latitude >= {latitude_min}")
        if latitude_max is not None:
            filters.append(f"latitude <= {latitude_max}")
        if longitude_min is not None:
            filters.append(f"longitude >= {longitude_min}")
        if longitude_max is not None:
            filters.append(f"longitude <= {longitude_max}")
        
        return " AND ".join(filters) if filters else "TRUE"
