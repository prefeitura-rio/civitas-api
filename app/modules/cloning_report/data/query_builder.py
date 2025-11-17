"""BigQuery SQL query builder for vehicle detection data"""

from datetime import datetime
from typing import Any
from dataclasses import dataclass


@dataclass
class QueryParameters:
    """Parameters for BigQuery vehicle detection query"""

    plate: str
    start_date: datetime
    end_date: datetime
    timezone: str = "America/Sao_Paulo"


class BigQueryQueryBuilder:
    """Builds optimized BigQuery queries for vehicle detection data"""

    PARAM_QUERY = """
    WITH ordered_positions AS (
      SELECT DISTINCT
        datahora,
        placa,
        a.codcet,
        camera_latitude,
        camera_longitude,
        velocidade
      FROM `rj-civitas.cerco_digital.vw_readings` a
      WHERE
        placa = @plate
        AND (camera_latitude != 0 AND camera_longitude != 0)
        AND datahora >= TIMESTAMP(@start_date)
        AND datahora <= TIMESTAMP(@end_date)
        AND NOT EXISTS (
          SELECT 1
          FROM `rj-civitas.cerco_digital.radares_quarentena` AS r
          WHERE r.codcet = a.codcet
        )
      ORDER BY datahora ASC, placa ASC
    ),
    loc AS (
      SELECT
        t1.codcet,
        t1.bairro,
        t1.logradouro,
        t1.locequip AS localidade,
        t1.latitude,
        t1.longitude
      FROM `rj-cetrio.ocr_radar.equipamento` t1
    )
    SELECT DISTINCT
      p.datahora,
      p.codcet,
      p.placa,
      COALESCE(l.latitude,  p.camera_latitude)  AS latitude,
      COALESCE(l.longitude, p.camera_longitude) AS longitude,
      COALESCE(l.bairro,     '') AS bairro,
      COALESCE(l.localidade, '') AS localidade,
      COALESCE(l.logradouro, '') AS logradouro,
      p.velocidade,
      CONCAT(COALESCE(l.localidade, ''), ' (', p.codcet, ')') AS localidade_codcet
    FROM ordered_positions p
    LEFT JOIN loc l ON p.codcet = l.codcet
    ORDER BY p.datahora ASC;
    """

    @classmethod
    def build_vehicle_query(
        cls, params: QueryParameters
    ) -> tuple[str, list[tuple[str, str, str]]]:
        """Build the complete BigQuery SQL for vehicle detection with parameters"""
        query_parameters = [
            ("plate", "STRING", params.plate),
            ("start_date", "STRING", cls._format_timestamp(params.start_date)),
            ("end_date", "STRING", cls._format_timestamp(params.end_date)),
        ]
        return cls.PARAM_QUERY, query_parameters

    @classmethod
    def build_test_query(cls, limit: int = 1000) -> str:
        """Build a test query for development/testing"""
        return f"""
        SELECT DISTINCT
          DATETIME(datahora, "America/Sao_Paulo") AS datahora,
          placa,
          codcet,
          camera_latitude AS latitude,
          camera_longitude AS longitude,
          '' AS bairro,
          '' AS localidade,
          '' AS logradouro,
          velocidade,
          CONCAT('Test Location (', codcet, ')') AS "localidade (codcet)"
        FROM `rj-civitas.cerco_digital.vw_readings`
        WHERE
          (camera_latitude != 0 AND camera_longitude != 0)
          AND datahora >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        ORDER BY datahora DESC
        LIMIT {limit};
        """

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        """Format datetime for BigQuery parameters"""
        return value.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def estimate_query_cost(cls, params: QueryParameters) -> dict[str, Any]:
        """Estimate BigQuery processing cost and complexity"""
        days_span = (params.end_date - params.start_date).days

        estimated_rows_scanned = days_span * 10000
        estimated_bytes = estimated_rows_scanned * 200

        return {
            "estimated_days_span": days_span,
            "estimated_rows_scanned": estimated_rows_scanned,
            "estimated_bytes_processed": estimated_bytes,
            "complexity_score": "HIGH"
            if days_span > 30
            else "MEDIUM"
            if days_span > 7
            else "LOW",
            "recommendations": cls._get_optimization_recommendations(days_span),
        }

    @classmethod
    def _get_optimization_recommendations(cls, days_span: int) -> list:
        """Get query optimization recommendations"""
        recommendations = []

        if days_span > 30:
            recommendations.append("Consider splitting into smaller date ranges")
            recommendations.append("Use parametrized queries for better caching")

        if days_span > 7:
            recommendations.append("Consider adding additional filters if available")

        recommendations.append("Ensure proper indexing on plate and datahora columns")
        return recommendations
