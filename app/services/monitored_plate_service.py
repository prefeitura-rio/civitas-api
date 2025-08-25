# -*- coding: utf-8 -*-
"""
Monitored Plate service for handling plate monitoring operations.

This service encapsulates business logic related to monitored plates,
including CRUD operations and history tracking.
"""
import asyncio
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import pendulum
from fastapi import HTTPException
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from loguru import logger
from tortoise.transactions import in_transaction

from app import config
from app.models import MonitoredPlate, NotificationChannel, Operation, User
from app.pydantic_models import (
    MonitoredPlateHistory,
    MonitoredPlateIn,
    MonitoredPlateOut,
    MonitoredPlateUpdate,
)


class MonitoredPlateService:
    """Service for managing monitored plate operations."""

    @staticmethod
    async def get_monitored_plates(
        params: Params,
        operation_id: Optional[UUID] = None,
        operation_title: Optional[str] = None,
        active: Optional[bool] = None,
        start_time_create: Optional[datetime] = None,
        end_time_create: Optional[datetime] = None,
        notification_channel_id: Optional[UUID] = None,
        notification_channel_title: Optional[str] = None,
        plate_contains: Optional[str] = None,
    ) -> Page[MonitoredPlateOut]:
        """
        Get paginated list of monitored plates with filters.
        
        Args:
            params: Pagination parameters
            operation_id: Filter by operation ID
            operation_title: Filter by operation title
            active: Filter by active status
            start_time_create: Filter by creation start time
            end_time_create: Filter by creation end time
            notification_channel_id: Filter by notification channel ID
            notification_channel_title: Filter by notification channel title
            plate_contains: Filter by plate containing string
            
        Returns:
            Paginated list of monitored plates
        """
        offset = params.size * (params.page - 1)
        queryset = MonitoredPlate
        filtered = False

        # Apply filters
        if operation_id:
            operation = await Operation.get_or_none(id=operation_id)
            if not operation:
                raise HTTPException(status_code=404, detail="Operation not found")
            queryset = queryset.filter(operation=operation)
            filtered = True

        if operation_title:
            queryset = queryset.filter(operation__title__icontains=operation_title)
            filtered = True

        if active is not None:
            queryset = queryset.filter(active=active)
            filtered = True

        if notification_channel_id:
            channel = await NotificationChannel.get_or_none(id=notification_channel_id)
            if not channel:
                raise HTTPException(
                    status_code=404, detail="Notification channel not found"
                )
            queryset = queryset.filter(notification_channels=channel)
            filtered = True

        if notification_channel_title:
            queryset = queryset.filter(
                notification_channels__title__icontains=notification_channel_title
            )
            filtered = True

        if plate_contains:
            queryset = queryset.filter(plate__icontains=plate_contains)
            filtered = True

        if start_time_create and end_time_create:
            queryset = queryset.filter(
                created_at__gte=start_time_create, created_at__lte=end_time_create
            )
            filtered = True

        # Execute query
        if not filtered:
            queryset = queryset.all()

        monitored_plates_obj = await (
            queryset.order_by("plate").limit(params.size).offset(offset)
        )

        # Convert to output format
        awaitables = [
            MonitoredPlateOut.from_monitored_plate(plate) 
            for plate in monitored_plates_obj
        ]
        monitored_plates = await asyncio.gather(*awaitables)

        return create_page(
            monitored_plates, 
            params=params, 
            total=await queryset.count()
        )

    @staticmethod
    async def create_monitored_plate(
        plate_data: MonitoredPlateIn, user: User
    ) -> MonitoredPlateOut:
        """
        Create a new monitored plate.
        
        Args:
            plate_data: Plate data to create
            user: User creating the plate
            
        Returns:
            Created monitored plate
        """
        # Get operation and notification channels
        operation = await Operation.get_or_none(id=plate_data.operation_id)
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")

        notification_channels = []
        for channel_id in plate_data.notification_channel_ids:
            channel = await NotificationChannel.get_or_none(id=channel_id)
            if not channel:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Notification channel {channel_id} not found"
                )
            notification_channels.append(channel)

        # Create monitored plate
        monitored_plate = await MonitoredPlate.create(
            plate=plate_data.plate.upper(),
            operation=operation,
            notes=plate_data.notes,
            additional_info=plate_data.additional_info,
            created_by=user,
        )

        # Add notification channels
        for channel in notification_channels:
            await monitored_plate.notification_channels.add(channel)

        return await MonitoredPlateOut.from_monitored_plate(monitored_plate)

    @staticmethod
    async def get_monitored_plate(plate: str) -> MonitoredPlateOut:
        """
        Get a monitored plate by plate number.
        
        Args:
            plate: License plate number
            
        Returns:
            Monitored plate details
            
        Raises:
            HTTPException: If plate not found
        """
        plate = plate.upper()
        monitored_plate = await MonitoredPlate.filter(plate=plate).first()
        if not monitored_plate:
            raise HTTPException(status_code=404, detail="Plate not found")
        
        return await MonitoredPlateOut.from_monitored_plate(monitored_plate)

    @staticmethod
    async def update_monitored_plate(
        plate: str, update_data: MonitoredPlateUpdate, user: User
    ) -> MonitoredPlateOut:
        """
        Update a monitored plate.
        
        Args:
            plate: License plate number
            update_data: Data to update
            user: User performing the update
            
        Returns:
            Updated monitored plate
        """
        plate = plate.upper()
        monitored_plate = await MonitoredPlate.filter(plate=plate).first()
        if not monitored_plate:
            raise HTTPException(status_code=404, detail="Plate not found")

        # Update fields
        if update_data.active is not None:
            monitored_plate.active = update_data.active
        if update_data.notes is not None:
            monitored_plate.notes = update_data.notes
        if update_data.additional_info is not None:
            monitored_plate.additional_info = update_data.additional_info

        monitored_plate.updated_by = user
        await monitored_plate.save()

        return await MonitoredPlateOut.from_monitored_plate(monitored_plate)

    @staticmethod
    async def delete_monitored_plate(plate: str, user: User) -> dict:
        """
        Delete a monitored plate.
        
        Args:
            plate: License plate number
            user: User performing the deletion
            
        Returns:
            Deletion confirmation
        """
        plate = plate.upper()
        monitored_plate = await MonitoredPlate.filter(plate=plate).first()
        if not monitored_plate:
            raise HTTPException(status_code=404, detail="Plate not found")

        await monitored_plate.delete()
        return {"message": f"Plate {plate} deleted successfully"}

    @staticmethod
    async def get_monitored_plates_history(
        params: Params,
        plate: Optional[str] = None,
        start_time_create: Optional[datetime] = None,
        end_time_create: Optional[datetime] = None,
        start_time_delete: Optional[datetime] = None,
        end_time_delete: Optional[datetime] = None,
    ) -> Page[MonitoredPlateHistory]:
        """
        Get history of monitored plates operations.
        
        Args:
            params: Pagination parameters
            plate: Filter by specific plate
            start_time_create: Start time for creation filter
            end_time_create: End time for creation filter
            start_time_delete: Start time for deletion filter
            end_time_delete: End time for deletion filter
            
        Returns:
            Paginated history of monitored plates
        """
        # Parse datetime parameters
        timezone = config.TIMEZONE
        
        if start_time_create:
            start_time_create = pendulum.instance(start_time_create, tz=timezone)
        else:
            start_time_create = pendulum.DateTime(1970, 1, 1)
            
        if end_time_create:
            end_time_create = pendulum.instance(end_time_create, tz=timezone)
        else:
            end_time_create = pendulum.now(tz=timezone)
            
        if start_time_delete:
            start_time_delete = pendulum.instance(start_time_delete, tz=timezone)
        else:
            start_time_delete = pendulum.DateTime(1970, 1, 1)
            
        if end_time_delete:
            end_time_delete = pendulum.instance(end_time_delete, tz=timezone)
        else:
            end_time_delete = pendulum.now(tz=timezone)

        # Build plate filter
        plate_filter = ""
        if plate:
            plate_filter = " AND (add_history.plate = $7 OR del_history.plate = $7)"

        offset = (params.page - 1) * params.size
        
        # Complex SQL query for history tracking
        query = f"""
        WITH plate_adding_history AS (
            SELECT
                body->>'plate' AS plate,
                body->>'notes' AS notes,
                timestamp AS created_timestamp,
                user_id::text AS created_by
            FROM userhistory
            WHERE path = '/cars/monitored'
                AND status_code >= 200
                AND status_code < 300
                AND timestamp BETWEEN $1 AND $2
        ),
        plate_deleting_history AS (
            SELECT
                regexp_replace(path, '/cars/monitored/', '') AS plate,
                timestamp AS deleted_timestamp,
                user_id::text AS deleted_by
            FROM userhistory
            WHERE path LIKE '/cars/monitored/%'
                AND method = 'DELETE'
                AND status_code >= 200
                AND status_code < 300
                AND timestamp BETWEEN $3 AND $4
        ),
        final_history AS (
            SELECT
                COALESCE(add_history.plate, del_history.plate) AS plate,
                add_history.created_timestamp,
                add_history.created_by,
                del_history.deleted_timestamp,
                del_history.deleted_by,
                add_history.notes
            FROM plate_adding_history add_history
            FULL OUTER JOIN plate_deleting_history del_history
            ON add_history.plate = del_history.plate
            WHERE TRUE {plate_filter}
            ORDER BY COALESCE(add_history.created_timestamp, del_history.deleted_timestamp) DESC
        )
        SELECT
            *,
            COUNT(*) OVER() AS total
        FROM final_history
        OFFSET $5
        LIMIT $6;
        """

        # Execute query
        async with in_transaction() as conn:
            args = [
                start_time_create,
                end_time_create,
                start_time_delete,
                end_time_delete,
                offset,
                params.size,
            ]
            if plate:
                args.append(plate)
                
            _, results = await conn.execute_query(query, args)

        if not results:
            return create_page([], params=params, total=0)

        total = results[0]["total"]
        
        # Format results
        user_ids = set()
        for result in results:
            if result["created_by"]:
                user_ids.add(result["created_by"])
            if result["deleted_by"]:
                user_ids.add(result["deleted_by"])

        # Get user objects
        users = await asyncio.gather(
            *[User.get_or_none(id=user_id) for user_id in user_ids]
        )
        users_dict = {str(user.id): user for user in users if user}

        # Build response
        plates = [
            {
                "plate": result["plate"],
                "created_timestamp": result["created_timestamp"],
                "created_by": users_dict.get(result["created_by"]),
                "deleted_timestamp": result["deleted_timestamp"],
                "deleted_by": users_dict.get(result["deleted_by"]),
                "notes": result["notes"],
            }
            for result in results
        ]

        return create_page(
            [MonitoredPlateHistory(**plate) for plate in plates],
            params=params,
            total=total,
        )
