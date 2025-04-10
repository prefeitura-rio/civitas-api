from collections import defaultdict
from pathlib import Path
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from app.pydantic_models import DetectionWindowList, PdfReportMultipleCorrelatedPlatesIn, RequestedPlateData
from google.cloud import bigquery
from google.cloud.bigquery.table import Row
from app.utils import get_bigquery_client, generate_report_id
from app import config
from loguru import logger
from fastapi_cache.decorator import cache as cache_decorator


class DataService():
    """
    Service for data operations.
    
    Args:
        bq_client: BigQuery client.
        base_query: Base query for data operations.        
    """
    def __init__(self):
        self.bq_client = get_bigquery_client()
        self.base_query = """
        WITH filters AS (
            SELECT
                STRUCT(
                    placa_target,
                    target_id,
                    n_minutes,
                    n_plates,
                    start_time,
                    end_time
                ) AS target_parameters,

            FROM UNNEST([
                __filter_monitored_plates__
            ])
        ),

        _all_ AS (
            SELECT
                placa,
                tipoveiculo,
                velocidade,
                camera_numero,
                DATETIME(datahora, 'America/Sao_Paulo') AS datahora_local,
                empresa,
                DATETIME(datahora_captura, 'America/Sao_Paulo') AS datahora_captura,
                ROW_NUMBER() OVER (PARTITION BY placa, datahora ORDER BY datahora) AS row_num_duplicate
            FROM `rj-cetrio.ocr_radar.readings_*`
            WHERE
                __filter_all_readings__
            QUALIFY(row_num_duplicate) = 1
            ORDER BY camera_numero, datahora
        ),


        unique_locations AS ( -- Get all unique locations and associated information
        SELECT
            t1.codcet,
            t2.camera_numero,
            t1.bairro,
            CAST(t1.latitude AS FLOAT64) AS latitude,
            CAST(t1.longitude AS FLOAT64) AS longitude,
            TRIM(
            REGEXP_REPLACE(
                REGEXP_REPLACE(t1.locequip, r'^(.*?) -.*', r'\\1'), -- Remove the part after " -"
                r'\s+', ' ') -- Remove extra spaces
            ) AS locequip,
            COALESCE(CONCAT(' - SENTIDO ', sentido), '') AS sentido,
            TO_BASE64(
            MD5(
                CONCAT(
                LEFT(t1.codcet, LENGTH(t1.codcet) -1), 
                COALESCE(t1.sentido, '') -- Combine codcet and sentido, omitting the last character of codcet
                )
            )
            ) AS hashed_coordinates, -- Generate a unique hash for the location
        FROM `rj-cetrio.ocr_radar.equipamento` t1
        JOIN `rj-cetrio.ocr_radar.equipamento_codcet_to_camera_numero` t2
            ON t1.codcet = t2.codcet
        ),

        -- Select unique coordinates for each location
        unique_location_coordinates  AS (
        SELECT
            hashed_coordinates,
            locequip,
            ROW_NUMBER() OVER(PARTITION BY hashed_coordinates) rn
        FROM unique_locations
        QUALIFY(rn) = 1
        ),


        camera_numero AS (
        SELECT 
            distinct camera_numero
        from _all_
        ),


        -- Group radar information with readings
        radar_group AS (
        SELECT
            l.camera_numero,
            l.codcet,
            l.bairro,
            l.latitude,
            l.longitude,
            b.locequip,
            l.sentido,
            l.hashed_coordinates
        FROM
            unique_locations l
            JOIN unique_location_coordinates  b ON l.hashed_coordinates = b.hashed_coordinates
            JOIN camera_numero c ON l.camera_numero = c.camera_numero

        ),

        all_readings_hashed AS (
            SELECT 
                r.hashed_coordinates,
                a.placa,
                a.tipoveiculo,
                a.datahora_local,
                a.datahora_captura,
                a.camera_numero,
                r.codcet,
                r.locequip,
                r.bairro,
                r.sentido,
                a.empresa,
                r.latitude,
                r.longitude,
                a.velocidade
            FROM _all_ a
            LEFT JOIN radar_group r ON a.camera_numero = r.camera_numero
        ),


        _all AS (
            SELECT
                a.*,
                f.target_parameters
            FROM all_readings_hashed a 
            JOIN filters AS f
                ON a.datahora_local BETWEEN f.target_parameters.start_time AND f.target_parameters.end_time
        ),


        target_filter AS (
            SELECT 
                placa,
                camera_numero,
                hashed_coordinates,
                ROW_NUMBER() OVER(PARTITION BY placa ORDER BY datahora_local) detection_id,
                datahora_local,
                target_parameters
            FROM _all
            WHERE target_parameters.placa_target = placa
        ),

        all_readings AS (
            SELECT 
                a.hashed_coordinates,
                t.detection_id,
                ROW_NUMBER() OVER(PARTITION BY a.hashed_coordinates ORDER BY a.datahora_local, a.placa) detection_index,
                a.placa,
                a.tipoveiculo,
                CASE
                    WHEN a.target_parameters.placa_target = a.placa
                    THEN true
                    ELSE false
                END as target,
                a.velocidade,
                a.camera_numero,
                a.codcet,
                a.locequip,
                a.bairro,
                a.sentido,
                a.datahora_local,
                a.empresa,
                a.latitude,
                a.longitude,
                a.datahora_captura,  
                STRUCT(
                    a.target_parameters.placa_target,
                    a.target_parameters.target_id,
                    a.target_parameters.n_minutes,
                    a.target_parameters.n_plates,
                    a.target_parameters.start_time,
                    a.target_parameters.end_time,
                    t.datahora_local as detection_datahora_local,
                    t.camera_numero as camera_numero

                )  as target_parameters,
            FROM _all a
            LEFT JOIN target_filter t
                ON a.target_parameters.target_id = t.target_parameters.target_id
                AND a.hashed_coordinates = t.hashed_coordinates
            WHERE a.datahora_local BETWEEN
                TIMESTAMP_SUB(t.datahora_local, INTERVAL t.target_parameters.n_minutes MINUTE) 
                AND
                TIMESTAMP_ADD(t.datahora_local, INTERVAL t.target_parameters.n_minutes MINUTE)
        ),

        target_index AS (
            SELECT 
                placa,
                hashed_coordinates,
                detection_index,
                detection_id,
                datahora_local,
                target_parameters
            FROM all_readings
            WHERE target_parameters.placa_target = placa
        ),


        final_result AS (
            SELECT 
                a.hashed_coordinates,
                t.detection_id,
                a.detection_index,
                a.placa,
                a.tipoveiculo,
                CASE
                    WHEN a.target_parameters.placa_target = a.placa
                    THEN true
                    ELSE false
                END as target,
                a.velocidade,
                a.camera_numero,
                a.codcet,
                a.locequip,
                a.bairro,
                a.sentido,
                a.datahora_local,
                a.empresa,
                a.latitude,
                a.longitude,
                a.datahora_captura,  
                a.target_parameters,
                CASE 
                WHEN a.detection_index > t.detection_index THEN 'after'
                WHEN a.detection_index < t.detection_index THEN 'before'
                ELSE 'same'
                END AS before_after
            FROM all_readings a
            LEFT JOIN target_index t
                ON a.target_parameters.target_id = t.target_parameters.target_id
                AND a.hashed_coordinates = t.hashed_coordinates
                AND a.target_parameters.detection_datahora_local = t.datahora_local

            WHERE t.detection_index - a.target_parameters.n_plates <= a.detection_index 
                AND 
                t.detection_index + a.target_parameters.n_plates >=  a.detection_index

        ),

        count_plates_target AS (
            SELECT
                target_parameters.placa_target,
                placa,
                COUNT( CASE WHEN target IS NOT TRUE THEN placa END) AS count_placa_target,
                COUNT( CASE WHEN before_after IN ('before') THEN placa END) AS count_placa_target_before,
                COUNT( CASE WHEN before_after IN ('after') THEN placa END) AS count_placa_target_after
            FROM final_result
            GROUP BY target_parameters.placa_target, placa
        ),

        count_plates_geral AS (
            SELECT
                placa,
                COUNT( placa ) AS count_placa_geral,
                COUNT( CASE WHEN before_after IN ('before') THEN placa END) AS count_placa_geral_before,
                COUNT( CASE WHEN before_after IN ('after') THEN placa END) AS count_placa_geral_after
            FROM final_result
            WHERE target IS FALSE
            GROUP BY placa
        ),

        count_plates_with_different_targets AS (
            SELECT
                placa,
                COUNT(DISTINCT target_parameters.placa_target) AS count_different_targets,
                COUNT(DISTINCT CASE WHEN before_after IN ('before') THEN target_parameters.placa_target END) AS count_different_targets_before,
                COUNT(DISTINCT CASE WHEN before_after IN ('after') THEN target_parameters.placa_target END) AS count_different_targets_after
            FROM final_result
            WHERE target IS FALSE
            GROUP BY placa
        ),

        final_data AS (
            SELECT 
                a.hashed_coordinates,
                a.detection_index,
                a.detection_id,
                ROW_NUMBER() OVER (PARTITION BY a.hashed_coordinates, a.detection_id, a.target_parameters.target_id ORDER BY a.datahora_local) AS index,
                a.before_after,
                a.target,
                a.target_parameters.placa_target,
                a.placa,
                a.tipoveiculo,
                b.count_placa_target_before,
                b.count_placa_target_after,
                b.count_placa_target,
                c.count_placa_geral_before,
                c.count_placa_geral_after,
                c.count_placa_geral,
                d.count_different_targets_before,
                d.count_different_targets_after,
                d.count_different_targets,
                a.datahora_local,
                a.datahora_captura,
                a.camera_numero,
                a.codcet,
                a.locequip,
                a.bairro,
                a.sentido,
                a.empresa,
                a.latitude,
                a.longitude,
                a.velocidade,
                a.target_parameters
            FROM final_result a
            LEFT JOIN count_plates_target b
                ON a.target_parameters.placa_target = b.placa_target
                AND a.placa = b.placa
            LEFT JOIN count_plates_geral c
                ON a.placa = c.placa
            LEFT JOIN count_plates_with_different_targets d
                ON a.placa = d.placa
        )

        SELECT * FROM final_data
        ORDER BY count_different_targets DESC
        """


    async def __build_filters(
        self,
        monitored: PdfReportMultipleCorrelatedPlatesIn | DetectionWindowList,  # todo: chage sql detections names to match the pydantic model
        is_detection: bool = False, 
        filter_plates: list[str] = None
    ) -> tuple[str, str]:
        """
        Builds the SQL filters for the queries.

        Args:
            monitored: A PdfReportMultipleCorrelatedPlatesIn object containing information about monitored plates.
                        Or a list of dictionaries with the detections found.
            is_detection: If True, builds filters for the detection window.
                        If False, builds filters for the full period.
            filter_plates: Optional list of plates to filter.

        Returns:
            Tuple with two strings: filter for all readings and filter for monitored plates.
        """
        if is_detection:
            period = "detection window"
            start_parameter = "start_window"
            end_parameter = "end_window"
            
        else:
            period = "full period"
            start_parameter = "start"
            end_parameter = "end"

        logger.debug(f"Building filters for {period}.")
        
        if isinstance(monitored, PdfReportMultipleCorrelatedPlatesIn):
            # Access the list of plate data from the monitored object
            plate_data_list = monitored.requested_plates_data
        elif isinstance(monitored, DetectionWindowList):
            plate_data_list = monitored.detection_window_list

        if filter_plates:
            filtered_monitored = [
                plate for plate in plate_data_list if plate.plate in filter_plates]
        else:
            filtered_monitored = plate_data_list

        all_readings_filters = []
        monitored_plates_filters = []

        for i, plate_data in enumerate(filtered_monitored):
            start_parameter_value = getattr(plate_data, start_parameter)
            end_parameter_value = getattr(plate_data, end_parameter)
            
            all_readings_filters.append(
                """
                        (datahora BETWEEN 
                        TIMESTAMP_ADD('{start_parameter_value}', INTERVAL 3 HOUR) AND 
                        TIMESTAMP_ADD('{end_parameter_value}', INTERVAL 3 HOUR)
                        )""".format(
                            start_parameter_value=start_parameter_value,
                            end_parameter_value=end_parameter_value
                        )
            )

            if not is_detection:  # only need when it is not detections
                monitored_plates_filters.append(
                    f"""
                    STRUCT(
                        '{plate_data.plate}' AS placa_target,
                        {i} AS target_id,
                        {monitored.n_minutes} AS n_minutes,
                        {monitored.n_plates} AS n_plates,
                        DATETIME '{plate_data.start}' AS start_time,
                        DATETIME '{plate_data.end}' AS end_time
                    )"""
                )

        __filter_monitored_plates__ = ",\n".join(monitored_plates_filters)
        __filter_all_readings__ = " OR ".join(all_readings_filters)
        
        logger.debug(f"Filters for {period} built.")
        
        return __filter_all_readings__, __filter_monitored_plates__


    async def __build_correlation_table_query(
        self,
        monitored: PdfReportMultipleCorrelatedPlatesIn,
        detections_dict: list[dict],
        filter_plates: list[str] = None,
    ) -> str:
        """
        Builds the SQL query for the correlation table, using detections as base.

        Args:
            monitored: List of dictionaries with the original monitored plates.
            detections_dict: List of dictionaries with the detections found.
            filter_plates: List of plates for filter (optional).

        Returns:
            A complete SQL query.
        """
        # logger.debug(f"DETECTIONS DICT STRUCTURE: {detections_dict[0]}")
        detection_window_list = DetectionWindowList(detection_window_list=detections_dict)
        
        logger.info("Building correlation table query.")
        # logger.info(f"Building correlation table query for {[data.plate for data in monitored.requested_plates_data]}.") # TODO: change data logged for len(data)
        __filter_all_readings__, _ = await self.__build_filters(
            monitored=detection_window_list, filter_plates=filter_plates, is_detection=True
        )
        _, __filter_monitored_plates__ = await self.__build_filters(
            monitored=monitored, filter_plates=filter_plates, is_detection=False
        )

        query = self.base_query.replace("__filter_all_readings__", __filter_all_readings__).replace(
            "__filter_monitored_plates__", __filter_monitored_plates__
        )
        
        logger.info(f"Correlation table query built.")
        # logger.debug(f"Correlation table query: {query}") # TODO: remove
        
        
        return query
        
    
    async def __get_most_common_vehicle_type(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Get the most common vehicle type for each license plate that has multiple vehicle types.
        
        Args:
            data: DataFrame containing vehicle data with 'placa' (license plate) and 'tipoveiculo' (vehicle type) columns.
            
        Returns:
            DataFrame with license plates, their vehicle types, and the count of occurrences for each combination.
            Contains only plates that have multiple vehicle types assigned.
        """
        plates_with_multiple_vehicle_types = data.groupby(
            "placa")["tipoveiculo"].nunique()

        plates_with_multiple_vehicle_types = plates_with_multiple_vehicle_types[
            plates_with_multiple_vehicle_types > 1
        ].index

        result = data[data["placa"].isin(
            plates_with_multiple_vehicle_types)]

        final_result = (
            result.groupby(["placa", "tipoveiculo"])
            .size()
            .reset_index(name="contagem")
        )

        return final_result    
    
    
    async def __overwrite_vehicle_types(
        self,
        data: pd.DataFrame,
        mapping_vehicle_types: dict[str, str] = None,
    ) -> pd.DataFrame:
        """
        Overwrites the vehicle types in the dataframe based on the mapping dictionary.
        If no mapping dictionary is provided, uses the default mapping.

        Args:
            data: DataFrame containing vehicle data with 'placa' (license plate) and 'tipoveiculo' (vehicle type) columns.
            mapping_vehicle_types: Dictionary mapping vehicle types to their most common type.

        Returns:
            DataFrame with the vehicle types overwritten.
        """
        logger.debug(f"Overwriting vehicle types.")
        if not mapping_vehicle_types:
            mapping_vehicle_types = config.VEHICLE_TYPES_MAPPING
        
        data["tipoveiculo"] = data["tipoveiculo"].apply(
            lambda x: mapping_vehicle_types.get(x)
        )
        divergent_vehicle_types = await self.__get_most_common_vehicle_type(data)

        # Choose the most common vehicle type for each plate
        most_common_vehicle_type = divergent_vehicle_types.sort_values(
            by="contagem", ascending=False
        ).drop_duplicates(subset="placa", keep="first")

        # Mapping dictionary using 'placa' and 'tipoveiculo' from the result
        plate_to_vehicle_type = most_common_vehicle_type.set_index(
            "placa")["tipoveiculo"].to_dict()

        # Substitute the values of 'tipoveiculo' in the df based on the plates
        data["tipoveiculo"] = (
            data["placa"].map(plate_to_vehicle_type).fillna(
                data["tipoveiculo"])
        )
        logger.debug(f"Vehicle types overwritten.")

        return data
  
    
    async def __filter_data(
        self,
        data: pd.DataFrame,
        min_different_targets: int = 2,
        before_after: str = None,
        vehicle_types: list[str] = None,
    ) -> pd.DataFrame:
        """
        Filters the correlation data based on specified criteria.
        
        Args:
            data (pd.DataFrame): DataFrame containing correlation data to be filtered.
            min_different_targets (int, optional): Minimum number of different target plates required. Defaults to 2.
            before_after (str, optional): Filter for detections before or after the target time. Options: 'before', 'after', or None for both.
            vehicle_types (list[str], optional): List of vehicle types to include in the results.
            
        Returns:
            pd.DataFrame: Filtered correlation data that meets all specified criteria.
        """
        if before_after:
            column = f"count_different_targets_{before_after}"
            msk = (
                (data[column] >= min_different_targets) | (
                    data["target"] == True)
            ) & (
                (data["before_after"] == before_after)
                | (data["before_after"] == "same")
            )

        else:
            column = "count_different_targets"
            msk = (data[column] >= min_different_targets) | (
                data["target"] == True
            )
        logger.debug(f"Filtering data for {column}.")
        
        data["weight"] = data[column]

        if vehicle_types:
            logger.debug(f"Filtering data for vehicle types.")
            msk &= data["tipoveiculo"].isin(vehicle_types)

        sort_columns = [
            "count_different_targets" +
            ("_" + before_after if before_after else ""),
            "count_placa_geral" + ("_" + before_after if before_after else ""),
        ]
        logger.debug(f"Sorting data for {sort_columns}.")
        
        df_filtered = data[msk].sort_values(by=sort_columns, ascending=False)
        
        logger.debug(f"Data filtered and sorted for {len(df_filtered)} plates.")
        return df_filtered
    
    
    async def __get_detections(
        self,
        monitored: PdfReportMultipleCorrelatedPlatesIn, 
        filter_plates: list[str] = None
    ) -> list[dict]:
        """
        Fetch initial detections for monitored plates.

        Args:
            monitored (PdfReportMultipleCorrelatedPlatesIn): Object containing information about monitored plates.
            filter_plates (list[str], optional): List of plates to filter the results. Defaults to None.

        Returns:
            list[dict]: A list of detection data for the monitored plates.
        """
        logger.info("Getting detections.")
        # logger.info(f"Getting detections for {[data.plate for data in monitored.requested_plates_data]}.") # TODO: change data logged for len(data)
        monitored.n_plates = 1_000_000_000 if monitored.n_plates is None else monitored.n_plates
        
        query_detections = """
        WITH filters AS (
            SELECT
                STRUCT(
                    placa_target,
                    target_id,
                    n_minutes,
                    n_plates,
                    start_time,
                    end_time
                ) AS target_parameters,

            FROM UNNEST([
                __filter_monitored_plates__
            ])
        ),

        _all_ AS (
            SELECT
                placa,
                camera_numero,
                DATETIME(datahora, 'America/Sao_Paulo') AS datahora_local,
                ROW_NUMBER() OVER (PARTITION BY placa, datahora ORDER BY datahora) AS row_num_duplicate
            FROM `rj-cetrio.ocr_radar.readings_*`
            WHERE
                __filter_all_readings__
            QUALIFY(row_num_duplicate) = 1
            ORDER BY camera_numero, datahora
        )

        SELECT 
            a.placa AS plate,
            a.camera_numero AS camera_number,
            ROW_NUMBER() OVER (PARTITION BY a.placa ORDER BY a.datahora_local) AS detection_index,
            f.target_parameters.target_id,
            f.target_parameters.n_minutes,
            f.target_parameters.n_plates,
            CAST(f.target_parameters.start_time AS STRING) as start_time,
            CAST(f.target_parameters.end_time AS STRING) as end_time,
            CAST(a.datahora_local AS string) as local_detection_datetime,
            CAST(TIMESTAMP_SUB(a.datahora_local, INTERVAL f.target_parameters.n_minutes MINUTE) AS STRING) as start_window,
            CAST(TIMESTAMP_ADD(a.datahora_local, INTERVAL f.target_parameters.n_minutes MINUTE) AS STRING) as end_window
        FROM _all_ a
        JOIN filters AS f
            ON a.datahora_local BETWEEN f.target_parameters.start_time AND f.target_parameters.end_time
        WHERE a.placa = f.target_parameters.placa_target
            AND a.datahora_local BETWEEN f.target_parameters.start_time AND f.target_parameters.end_time
        """

        __filter_all_readings__, __filter_monitored_plates__ = await self.__build_filters(
            monitored=monitored, filter_plates=filter_plates, is_detection=False
        )
        
        query_detections = query_detections.replace(
            "__filter_all_readings__", __filter_all_readings__
        ).replace("__filter_monitored_plates__", __filter_monitored_plates__)
        
        # logger.debug(f"Query: {query_detections}") # TODO: remove
        
        try:
            query_job = self.bq_client.query(query_detections)
            data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
            
            detections = []
            for page in data.pages:
                for row in page:
                    row: Row
                    row_data = dict(row.items())
                    detections.append(row_data)
            
        except Exception as e:
            logger.error(f"Error getting detections: {e}")
            raise e
        
        # logger.debug(f"Raw data: {detections}") # TODO: import logger
        # logger.debug(f"Detections raw data: {detections}") # TODO: remove

        logger.info("Detections retrieved.")
        # logger.info(f"Detections for {[data.plate for data in monitored.requested_plates_data]} retrieved.") # TODO: change data logged for len(data)
        
        return detections
    
    
    async def __get_correlated_detections(
        self,
        monitored: PdfReportMultipleCorrelatedPlatesIn,
        detections: list[dict],
        filter_plates: list[str] = None
    ) -> pd.DataFrame:
        """
        Get correlated detections for monitored plates.
        
        Args:
            monitored (PdfReportMultipleCorrelatedPlatesIn): Object containing information about monitored plates.
            detections (DetectionWindowList): List of detection dictionaries retrieved from BigQuery.
            filter_plates (list[str], optional): Optional list of plates to filter. Defaults to None.
            
        Returns:
            pd.DataFrame: DataFrame containing information about plates that were detected near the monitored plates 
            within the specified time windows.
        """
        query = await self.__build_correlation_table_query(
            monitored=monitored,
            detections_dict=detections,
            filter_plates=filter_plates
        )
        logger.info("Getting correlated detections.")
        query_job = self.bq_client.query(query)
        data = query_job.result(page_size=config.GOOGLE_BIGQUERY_PAGE_SIZE)
        
        correlated_detections = []
        for page in data.pages:
            for row in page:
                row: Row
                row_data = dict(row.items())
                correlated_detections.append(row_data)
                
        logger.info("Correlated detections retrieved.")
        # logger.info(f"Correlated detections for {[data.plate for data in monitored.requested_plates_data]} retrieved.") # TODO: change data logged for len(data)
        return pd.DataFrame(correlated_detections)
    
    async def get_correlations(
        self, 
        data: PdfReportMultipleCorrelatedPlatesIn, 
        filter_plates: list[str] = None
    ) -> pd.DataFrame:
        """
        Get correlations for monitored plates.
        
        Args:
            data (PdfReportMultipleCorrelatedPlatesIn): Object containing information about monitored plates.
            filter_plates (list[str], optional): Optional list of plates to filter. Defaults to None.

        Returns:
            pd.DataFrame: DataFrame containing the correlations for the monitored plates.
        """
        
        detections = await self.__get_detections(data, filter_plates=filter_plates)
        if not detections:
            logger.warning("No detections found.")
            return pd.DataFrame()
        
        correlated_detections = await self.__get_correlated_detections(data, detections, filter_plates=filter_plates)
        if correlated_detections.shape[0] <= 1:
            logger.warning("No correlated detections found.")
            return pd.DataFrame()
    
        logger.info(f"Detections: {len(detections)}")
        logger.info(f"Correlated detections: {correlated_detections.shape}")
    
        normalized_detections = await self.__overwrite_vehicle_types(correlated_detections)
        filtered_detections = await self.__filter_data(
            data=normalized_detections,
            min_different_targets=data.min_different_targets,
            before_after=data.before_after,
            vehicle_types=data.vehicle_types
        )

        if filtered_detections.shape[0] <= 1:
            logger.warning(
                "No correlated detections remaining after filtering."
                "Try to change 'min_different_targets', 'vehicle_types' or 'before_after' parameters.")
            return pd.DataFrame()
        
        return filtered_detections


class GraphService():
    """
    Service for graph operations.
    
    Args:
        G: Directed graph.
        dataframe: DataFrame with the data of the plates.
    """
    def __init__(self):
        self.G: nx.DiGraph | None = None
        self.dataframe: pd.DataFrame | None = None
        logger.info("Initialized Graph service.")
        
    
    async def __limit_nodes_in_graph(self, G: nx.DiGraph, max_nodes: int = 30) -> nx.DiGraph:
        """
        Limits the number of nodes in the graph to improve visualization and avoid overlapping.

        Args:
            G (nx.DiGraph): The directed graph to be limited.
            max_nodes (int, default=30): Approximate reference value for the maximum number of nodes, not an exact limit.
            The algorithm prioritizes keeping nodes with higher weight (relevance) and may include a
            different number of nodes depending on the weight distribution in the graph.

        Returns:
            nx.DiGraph: The graph with a limited number of nodes.
        """
        # Count of target and batedor nodes by weight group
        weight_counts = {}
        for node, data in G.nodes(data=True):
            node_type = data.get("type")

            # For batedor nodes, get the weight of the edges
            if node_type == "batedor":
                edges = G.edges(node, data=True)
                for _, _, edge_data in edges:
                    weight = edge_data.get("weight", 0)
                    if weight not in weight_counts:
                        weight_counts[weight] = {"target": 0, "batedor": 0}
                    weight_counts[weight]["batedor"] += 1
            # For target nodes, add to counter with weight 0 (or other specific value)
            elif node_type == "target":
                if 0 not in weight_counts:
                    weight_counts[0] = {"target": 0, "batedor": 0}
                weight_counts[0]["target"] += 1

        # Sort weights in descending order
        sorted_weights = sorted(weight_counts.keys(), reverse=True)

        # Determine the minimum weight to reach at least 60 nodes
        min_weight = 1  # default value
        total_nodes = 0

        for weight in sorted_weights:
            total_nodes += (
                weight_counts[weight]["target"] + weight_counts[weight]["batedor"]
            )
            if total_nodes >= max_nodes:
                min_weight = weight
                break

        # Filter the graph to include only nodes with weight >= min_weight
        nodes_to_remove = []
        for node, data in G.nodes(data=True):
            if data.get("type") == "batedor":
                # Check if all edges of the batedor have weight < min_weight
                all_edges_below_threshold = True
                for _, _, edge_data in G.edges(node, data=True):
                    if edge_data.get("weight", 0) >= min_weight:
                        all_edges_below_threshold = False
                        break

                if all_edges_below_threshold:
                    nodes_to_remove.append(node)

        G.remove_nodes_from(nodes_to_remove)

        isolated_nodes = list(nx.isolates(G))
        G.remove_nodes_from(isolated_nodes)

        return G


    async def create_graph(self, dataframe: pd.DataFrame, limit_nodes: int = 30) -> None:
        """
        Creates and displays an interactive graph from a DataFrame,
        with colored nodes, detailed tooltips, and visualization options.

        Args:
            dataframe: pandas DataFrame with the data of the plates.  Must contain, at least,
                the columns 'placa_target', 'placa', 'count_different_targets' and 'target'.
                Ideally, it should also contain columns like 'datahora_local', 'bairro', etc.
                for more detailed information in the tooltips.
            limit_nodes: Approximate threshold for the maximum number of nodes in the graph.
                        The algorithm will select the nodes with the highest weight until it reaches
                        or approaches this number, prioritizing more relevant connections.
                        It is not an exact limit, but a reference value to control the density of the graph.
        """
        logger.info(f"Creating graph from dataframe.")
        self.dataframe = dataframe
        
        G = nx.DiGraph()

        logger.info("Preprocessing to identify target and batedor plates.")
        # Preprocessing to identify target and batedor plates
        target_plates = set(dataframe[dataframe["target"] == True]["placa"])

        logger.info("Iterating over dataframe rows to add nodes and edges.")
        for _, row in dataframe.iterrows():
            node_type = "batedor"  # Assume batedor by default
            if row["placa"] in target_plates:
                node_type = "target"  # Overwrites if the plate is in the target list

            G.add_node(row["placa"], type=node_type, **row.to_dict())

            if not row["target"]:  # Adds edges only for batedors
                G.add_edge(row["placa"], row["placa_target"], weight=row["weight"])

        logger.info("Removing isolated nodes.")
        isolated_nodes = list(nx.isolates(G))
        G.remove_nodes_from(isolated_nodes)

        logger.info("Limiting nodes in graph.")
        G = await self.__limit_nodes_in_graph(G, max_nodes=limit_nodes)

        # net.show_buttons(filter_=['physics'])  # Optional: show physics controls
        self.G = G
        logger.info("Graph created.")
        # return G
    
    
    async def to_png(
        self, 
        file_dir: Path | str = config.ASSETS_DIR,
        file_name: str = "grafo.png"
    ) -> Path:
        """
        Converts the graph to a PNG image.
        
        Args:
            file_dir: Directory to save the PNG file.
            file_name: Name of the PNG file.
            
        Returns:
            Path: Path to the PNG file.
        """
        logger.info("Converting graph to PNG.")
        # Ensure file_dir is a Path instance before joining with filename
        if not isinstance(file_dir, Path) and isinstance(file_dir, str):
            file_dir = Path(file_dir)
        
        if not isinstance(file_name, str):
            raise ValueError("file_name must be instance of pathlib.Path or a string")
        
        file_path = file_dir / file_name
        plt.figure(figsize=(16, 12))

        logger.info("Preprocessing to identify target and batedor plates.")
        # Preprocessing
        target_plates = set(self.dataframe[self.dataframe["target"] == True]["placa"])
        batedores = [
            node for node, data in self.G.nodes(data=True) if data.get("type") == "batedor"
        ]

        # Custom layout creation
        pos = {}

        logger.info("Positioning batedors in a regular polygon.")
        # 1. Positions the batedors in a regular polygon
        num_batedores = len(batedores)
        if num_batedores > 0:
            radius = 5  # Raio do polígono
            angles = np.linspace(0, 2 * np.pi, num_batedores, endpoint=False)
            for i, batedor in enumerate(batedores):
                angle = angles[i] - np.pi / 2  # Rotates to have a node at the top
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                pos[batedor] = np.array([x, y])

        logger.info("Grouping targets by connected batedors.")
        # 2. Groups targets by connected batedors
        connection_groups = defaultdict(list)
        for node, data in self.G.nodes(data=True):
            if data.get("type") == "target":
                connected = tuple(
                    sorted(p for p in self.G.predecessors(node) if p in batedores))
                connection_groups[connected].append(node)

        logger.info("Positioning each group dynamically.")
        # 3. Positions each group dynamically
        for connected_bats, nodes in connection_groups.items():
            if not connected_bats:
                continue

            # Calculates the centroid of the connected batedors
            bats_pos = [pos[b] for b in connected_bats]
            centroid = np.mean(bats_pos, axis=0)

            # Direction and distance from the center
            vec_from_center = centroid - \
                np.mean([pos[b] for b in batedores], axis=0)
            if np.linalg.norm(vec_from_center) > 0:
                direction = vec_from_center / np.linalg.norm(vec_from_center)
            else:
                direction = np.array([1, 0])

            # Base position with distance adjustment
            # Radius increases with the number of connections
            base_radius = 2 + len(connected_bats)
            base_pos = centroid + direction * base_radius

            # Circular distribution of nodes
            num_nodes = len(nodes)
            node_radius = 1.5 + 0.2 * num_nodes
            angles = np.linspace(0, 2 * np.pi, num_nodes, endpoint=False)

            for i, (node, angle) in enumerate(zip(nodes, angles)):
                offset = np.array([np.cos(angle), np.sin(angle)]) * node_radius
                pos[node] = base_pos + offset

        logger.info("Applying spring layout for remaining nodes.")
        # 4. Applies spring layout for remaining nodes
        unpositioned = list(set(self.G.nodes()) - set(pos.keys()))
        if unpositioned:
            sub_pos = nx.spring_layout(
                self.G.subgraph(unpositioned), k=150, iterations=500, seed=42
            )
            pos.update(sub_pos)

        # Dynamic visual configurations
        node_colors = []
        node_sizes = []
        for node in self.G.nodes():
            if self.G.nodes[node].get("type") == "target":
                node_colors.append("red")
                node_sizes.append(400)
            else:
                node_colors.append("blue")
                node_sizes.append(250)

        logger.info("Normalizing edge widths.")
        # Normalization of edge widths
        edge_weights = [d["weight"] for _, _, d in self.G.edges(data=True)]
        # logger.debug(f"Edge weights: {edge_weights}")
        
        if edge_weights and len(set(edge_weights)) > 1:
            min_w, max_w = min(edge_weights), max(edge_weights)
            edge_widths = [1 + 4 * (w - min_w) / (max_w - min_w)
                        for w in edge_weights]
        else:
            edge_widths = [1]

        logger.info("Drawing the graph.")
        # Drawing the graph
        nx.draw_networkx_nodes(
            self.G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9, linewidths=2
        )

        logger.info("Drawing edges.")
        nx.draw_networkx_edges(
            self.G,
            pos,
            # edge_color='gray',
            edge_color="black",
            width=edge_widths,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=15,
            connectionstyle="arc3,rad=0.15",
            alpha=0.7,
        )

        logger.info("Drawing node labels.")
        # Node labels
        for node, (x, y) in pos.items():
            plt.text(
                x,
                y - 0.5,
                node,
                fontsize=9,
                ha="center",
                va="center",
                color="black",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.7),
            )

        # Final adjustments
        plt.axis("off")
        plt.tight_layout()
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        logger.info(f"Graph converted to PNG")
        
        return file_path


class PdfService():
    """
    Service for PDF report operations.
    
    Args:
        report_id: ID of the report.
        report_title: Title of the report.
        time_interval_str: Time interval of the report.
        before_after_portuguese_str: Portuguese string of the before and after.
        min_different_targets: Minimum number of different targets.
        vehicle_types_str: String of the vehicle types.
        requested_vehicles: List of requested vehicles data (plate, start, end).
        total_monitored_plates: Total number of monitored plates.
        detections: List of detections.
        detailed_detections: Dictionary of detailed detections.
    """
    def __init__(self):
        self.report_id: str = ""
        self.report_title: str = ""
        self.before_after: str = ""
        
        self.time_interval_str: str = ""
        self.before_after_portuguese_str: str = ""
        self.min_different_targets: int = 0
        self.vehicle_types_str: str = ""
        self.requested_vehicles: list[RequestedPlateData] = []
        
        self.total_monitored_plates: int = 0
        self.detections: list[dict] = []
        self.detailed_detections: dict = {}
        
    
    async def initialize(self, data: PdfReportMultipleCorrelatedPlatesIn):
        """
        Initializes the PDF service.
        
        Args:
            data: Data of the PDF report.
        """
        self.report_id = await generate_report_id()
        self.report_title = data.report_title
        self.time_interval_str = f"{data.n_minutes} minutos"
        self.min_different_targets = data.min_different_targets
        self.vehicle_types_str = ", ".join(data.vehicle_types)
        self.requested_vehicles = data.requested_plates_data
        self.before_after = data.before_after
        
        if self.before_after == "after":
            self.before_after_portuguese_str = "depois"
            
        elif self.before_after == "before":
            self.before_after_portuguese_str = "antes"
            
        else:
            self.before_after_portuguese_str = "antes e depois"
            
        logger.info("Initialized PDF service.")


    async def set_detections(self, correlated_detections: pd.DataFrame) -> list[dict]:
        """
        Sets the detections for the PDF report.
        
        Args:
            correlated_detections: DataFrame with the correlated detections.
            
        """
        logger.info("Setting detections for PDF report.")
        count_placa_geral_column = "count_placa_geral" + (
            "_" + self.before_after if self.before_after else ""
        )
        count_different_targets_column = "count_different_targets" + (
            "_" + self.before_after if self.before_after else ""
        )

        df_selected = correlated_detections[
            [
                "placa",
                "tipoveiculo",
                count_different_targets_column,
                count_placa_geral_column,
            ]
        ].drop_duplicates()

        # Change the method to non-async since it doesn't need to be async
        def get_target_plates(plate: str, dataframe: pd.DataFrame) -> str:
            """Obtém a lista de placas alvo relacionadas a uma placa específica."""
            return ", ".join(
                sorted(
                    dataframe[(dataframe["placa"] == plate) & (dataframe["target"] == 0)][
                        "placa_target"
                    ]
                    .unique()
                    .tolist()
                )
            )

        logger.info("Getting target plates.")
        # Add column with target plates using the non-async function
        df_selected["placa_targets"] = df_selected["placa"].apply(
            lambda plate: get_target_plates(plate, correlated_detections)
        )

        # Remove lines without target plates
        df_selected = df_selected[df_selected["placa_targets"] != ""]

        df_selected.columns = [
            "plate",
            "vehicle_type",
            "count_different_targets",
            "count_plate_total",
            "target_plates"
        ]
        
        df_selected[["count_different_targets", "count_plate_total"]] = df_selected[["count_different_targets", "count_plate_total"]].astype(int)
        detections = df_selected.to_dict(orient="records")
        
        self.detections = detections
        await self.__set_total_monitored_plates()
        logger.info("Detections set.")
        
        
    async def set_detailed_detections(self, correlated_detections: pd.DataFrame) -> dict:
        """
        Sets the detailed detections for the PDF report.
        
        Args:
            correlated_detections: DataFrame with the correlated detections.
        """
        logger.info("Setting detailed detections for PDF report.")
        # Select columns and filter data for detailed detections
        detection_details = (
            correlated_detections[correlated_detections["placa"] != correlated_detections["placa_target"]][
                [
                    "detection_index",
                    "datahora_captura",
                    "placa",
                    "placa_target",
                    "codcet",
                    "locequip",
                    "bairro",
                    "sentido",
                    "latitude",
                    "longitude",
                    "velocidade",
                ]
            ]
            .drop_duplicates()
            .sort_values(by=["datahora_captura"], ascending=True)
        )

        logger.info("Grouping codcets by latitude and longitude.")
        # Group codcets by latitude and longitude
        columns_agg = (
            detection_details.groupby(
                ["latitude", "longitude", "locequip", "sentido"])
            .agg(
                {
                    "codcet": lambda x: sorted(
                        list(x.unique())
                    )  # Creates a list of unique codcets for each coordinate
                }
            )
            .reset_index()
        )

        # Create a DataFrame for each unique location
        location_dfs = {}

        logger.info("Iterating over grouped detailed detections.")
        # Iterate over each row of the DataFrame columns_agg
        for idx, row in columns_agg.iterrows():
            # Extract values to filter
            lat = row["latitude"]
            lon = row["longitude"]
            loc = row["locequip"]
            direction = row["sentido"]

            # Create a unique identifier for this location
            location_id = f"loc_{idx}"

            # Filter detection_details based on criteria
            filtered_df:pd.DataFrame = detection_details[
                (detection_details["latitude"] == lat)
                & (detection_details["longitude"] == lon)
                & (detection_details["locequip"] == loc)
                & (detection_details["sentido"] == direction)
            ].copy()

            # Create a new column with the formatted dates
            filtered_df['datahora_captura'] = filtered_df['datahora_captura'].dt.strftime('%d/%m/%Y %H:%M:%S')
            
            # For each group, we will build the desired JSON structure
            location_data = {
                "codcet_list": sorted(filtered_df["codcet"].drop_duplicates().tolist()),
                "locequip": filtered_df["locequip"].iloc[0],
                "bairro": filtered_df["bairro"].iloc[0],
                "sentido": filtered_df["sentido"].iloc[0],
                "latitude": filtered_df["latitude"].iloc[0],
                "longitude": filtered_df["longitude"].iloc[0],
                "data": filtered_df[["detection_index", "datahora_captura", "placa", "placa_target", "velocidade"]].to_dict(orient="records")
            }

            # # Store the filtered DataFrame in the dictionary
            location_dfs[location_id] = location_data

        logger.info("Detailed detections set.")
        self.detailed_detections = location_dfs
        
    
    async def __set_total_monitored_plates(self):
        """
        Sets the total number of monitored plates.
        """
        self.total_monitored_plates = sum([d['count_plate_total'] for d in self.detections])
        
    
    async def get_template_context(self) -> dict:
        """
        Builds the template context for the PDF report.
        
        Returns:
            dict: Template context for the PDF report.
        """
        logger.info("Building template context for PDF report.")
        requested_vehicles = [
            {
                "plate": vehicle.plate,
                "start": vehicle.start.strftime('%d/%m/%Y %H:%M:%S'),
                "end": vehicle.end.strftime('%d/%m/%Y %H:%M:%S')
            }
            for vehicle in self.requested_vehicles
        ]
        
        logger.info("Template context built.")
        return {
            "report_id": self.report_id,
            "report_title": self.report_title,
            "requested_vehicles": requested_vehicles,
            "time_interval_str": self.time_interval_str,
            "before_after_str": self.before_after_portuguese_str,
            "min_different_targets": self.min_different_targets,
            "vehicle_types_str": self.vehicle_types_str,
            "detections": self.detections,
            "total_monitored_plates": self.total_monitored_plates,
            "detailed_detections": self.detailed_detections,
            "grafo_path": config.ASSETS_DIR / "grafo.png"
        }
        
