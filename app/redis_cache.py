# -*- coding: utf-8 -*-
import asyncio
from typing import Dict, List, Tuple

import aiohttp
import pytz
from pendulum import DateTime
from redis.asyncio import Redis

from app import config


class Cache:
    def __init__(self) -> None:
        self._cache = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
        )
        self._car_position_hash_key_template = "car:{placa}:position:{timestamp}"
        self._car_positions_sorted_set_key_template = "car:{placa}:positions"
        self._cortex_token_key = "cortex_token"
        self._data_relay_token_key = "data_relay_token"
        self._fogocruzado_token_key = "fogocruzado_token"

    async def add_position(
        self,
        placa: str,
        data: Dict[str, float | str],
        expire: int = config.CACHE_CAR_POSITIONS_TTL,
    ) -> None:
        """
        Adds a car position to cache.

        Args:
            placa (str): The vehicle license plate.
            data (Dict[str, float | str]): The position data in the format:
                {
                    "latitude": float,
                    "longitude": float,
                    "datahora": str, # The datetime in the format "YYYY-MM-DDTHH:MM:SS"
                }
            expire (int, optional): The expiration time in seconds. Defaults to
                config.CACHE_CAR_POSITIONS_TTL.
        """
        # Get keys
        sorted_set_key = self._car_positions_sorted_set_key_template.format(placa=placa)
        timestamp: DateTime = data["datahora"]
        score = int(timestamp.timestamp())
        hash_key = self._car_position_hash_key_template.format(
            placa=placa, timestamp=timestamp
        )

        # Store the detailed data in a hash
        data["datahora"] = timestamp.to_iso8601_string()
        await self._cache.hmset(hash_key, data)
        await self._cache.expire(hash_key, expire)

        # Add the timestamp to the sorted set
        await self._cache.zadd(sorted_set_key, {hash_key: score})
        await self._cache.expire(sorted_set_key, expire)

    async def get_missing_range(
        self, placa: str, start_time: DateTime, end_time: DateTime
    ) -> Tuple[DateTime, DateTime] | None:
        """
        Fetch the missing range of positions of a vehicle within a time range.

        Args:
            placa (str): The vehicle license plate.
            start_time (DateTime): The minimum datetime of the range.
            end_time (DateTime): The maximum datetime of the range.

        Returns:
            Tuple[DateTime, DateTime] | None: The missing range of positions of the vehicle.
        """
        # Get keys
        sorted_set_key = self._car_positions_sorted_set_key_template.format(placa=placa)

        # Generate the hours list
        hours: List[DateTime] = []
        current = start_time
        current = current.in_tz(config.TIMEZONE)
        end_time = end_time.in_tz(config.TIMEZONE)
        end_time = end_time.add(hours=1)
        while current <= end_time:
            hours.append(current)
            current = current.add(hours=1).in_timezone(config.TIMEZONE)

        start_score = int(hours[0].timestamp())
        end_score = int(hours[-1].timestamp())

        # Fetch the range of cached timestamps
        cached_ranges: List[Tuple[bytes, float]] = await self._cache.zrangebyscore(
            sorted_set_key, start_score, end_score, withscores=True
        )

        # Iterate over the hours from beginning to end, verifying that there is data between them.
        # If there is a gap, this is our missing range start.
        missing_start = None
        missing_end = None
        for i in range(len(hours) - 1):
            start_hour = hours[i]
            end_hour = hours[i + 1]
            start_score = int(start_hour.timestamp())
            end_score = int(end_hour.timestamp())

            # Check if there is a gap between the hours
            if not any(start_score <= score <= end_score for _, score in cached_ranges):
                missing_start = start_hour
                break

        # Now do the same, but from the end to the beginning
        for i in range(len(hours) - 1, 0, -1):
            start_hour = hours[i - 1]
            end_hour = hours[i]
            start_score = int(start_hour.timestamp())
            end_score = int(end_hour.timestamp())

            # Check if there is a gap between the hours
            if not any(start_score <= score <= end_score for _, score in cached_ranges):
                missing_end = end_hour
                break

        return missing_start, missing_end

    async def get_positions(
        self, placa: str, start_time: DateTime, end_time: DateTime
    ) -> List[Dict[str, float | str]]:
        """
        Fetch the positions of a vehicle within a time range.

        Args:
            placa (str): The vehicle license plate.
            start_time (DateTime): The minimum datetime of the range.
            end_time (DateTime): The maximum datetime of the range.

        Returns:
            List[Dict[str, float | str]]: The positions of the vehicle.
        """
        # Get keys
        sorted_set_key = self._car_positions_sorted_set_key_template.format(placa=placa)
        start_score = int(start_time.timestamp())
        end_score = int(end_time.timestamp())
        hash_keys = await self._cache.zrangebyscore(
            sorted_set_key, start_score, end_score
        )

        # Get the positions
        awaitables = [self._cache.hgetall(hash_key) for hash_key in hash_keys]
        positions_raw: List[Dict[bytes, bytes]] = await asyncio.gather(*awaitables)
        positions = [
            {key.decode(): value.decode() for key, value in position.items()}
            for position in positions_raw
            if len(position.keys()) > 0
        ]
        for position in positions:
            position["datahora"] = DateTime.fromisoformat(position["datahora"])
            position["datahora"] = position["datahora"].in_tz(config.TIMEZONE)
        return positions

    async def get_data_relay_token(self) -> str:
        """
        Fetch the Data Relay token from cache (or reauthenticate if it's not present or expired).

        Returns:
            str: The Data Relay token.
        """
        # Get token from cache
        token: bytes = await self._cache.get(self._data_relay_token_key)
        if token:
            return token.decode()

        # Authenticate and store the token in cache
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.DATA_RELAY_BASE_URL}/auth/token",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "username": config.DATA_RELAY_USERNAME,
                    "password": config.DATA_RELAY_PASSWORD,
                },
            ) as response:
                response.raise_for_status()
                data = await response.json()
                token = data["access_token"]
                await self._cache.set(
                    self._data_relay_token_key, token, ex=data["expires_in"]
                )
                return token

    async def get_fogocruzado_token(self) -> str:
        """
        Fetch the Fogo Cruzado API token from cache (or reauthenticate if it's not present or
        expired).

        Returns:
            str: The Fogo Cruzado API token.
        """
        # Get token from cache
        token: bytes = await self._cache.get(self._fogocruzado_token_key)
        if token:
            return token.decode()

        # Authenticate and store the token in cache
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.FOGOCRUZADO_BASE_URL}/api/v2/auth/login",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "email": config.FOGOCRUZADO_USERNAME,
                    "password": config.FOGOCRUZADO_PASSWORD,
                },
            ) as response:
                response.raise_for_status()
                data = await response.json()
                token = data["data"]["accessToken"]
                await self._cache.set(
                    self._fogocruzado_token_key, token, ex=data["data"]["expiresIn"]
                )
                return token

    async def get_cortex_token(self) -> str:
        """
        Fetch the Cortex API token from cache (or reauthenticate if it's not present or
        expired).

        Returns:
            str: The Cortex API token.
        """
        # Get token from cache
        token: bytes = await self._cache.get(self._cortex_token_key)

        # Refresh the token if it's present
        if token:
            token = token.decode()
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.CORTEX_VEICULOS_BASE_URL}/auth/refresh_token",
                    headers={"Authorization": f"Bearer {token}"},
                ) as response:
                    response.raise_for_status()
                    token = (
                        response.headers.get("Authorization")
                        .replace("Bearer ", "")
                        .strip()
                    )
                    expiration_str = response.headers.get("expirationDate")
                    expiration = DateTime.strptime(
                        expiration_str, "%a %b %d %H:%M:%S %Z %Y"
                    )
                    time_until_expiration = int(
                        expiration.diff(
                            DateTime.now(tz=pytz.timezone(config.TIMEZONE))
                        ).total_seconds()
                    )
                    await self._cache.set(
                        self._cortex_token_key, token, ex=time_until_expiration
                    )
                    return token

        # Authenticate and store the token in cache if it's not
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.CORTEX_VEICULOS_BASE_URL}/login",
                json={
                    "email": config.CORTEX_USERNAME,
                    "senha": config.CORTEX_PASSWORD,
                },
            ) as response:
                response.raise_for_status()
                token = (
                    response.headers.get("Authorization").replace("Bearer ", "").strip()
                )
                expiration_str = response.headers.get("expirationDate")
                expiration = DateTime.strptime(
                    expiration_str, "%a %b %d %H:%M:%S %Z %Y"
                )
                time_until_expiration = int(
                    expiration.diff(
                        DateTime.now(tz=pytz.timezone(config.TIMEZONE))
                    ).total_seconds()
                )
                await self._cache.set(
                    self._cortex_token_key, token, ex=time_until_expiration
                )
                return token


cache = Cache()
