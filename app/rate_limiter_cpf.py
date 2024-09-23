# -*- coding: utf-8 -*-
import re
from typing import Tuple

from redis.asyncio import Redis, WatchError

from app import config
from app.pydantic_models import UserCortexRemainingCreditOut


class RateLimiterCPF:
    def __init__(self) -> None:
        self._redis = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
        )
        self._max_requests, self._time_window = self.parse_rate_limit(config.CORTEX_CPF_RATE_LIMIT)

    @classmethod
    def parse_rate_limit(cls, limit_text: str) -> Tuple[int, int]:
        """
        Parse the rate limit from the text.

        Args:
            limit_text (str): The text containing the rate limit.

        Returns:
            Tuple[int, int]: A tuple containing the rate limit and the time window.
        """
        match = re.match(r"(\d+)/(\w+)", limit_text)
        if not match:
            raise ValueError("Invalid format. Use 'N/period' (e.g., '1/second').")

        count = int(match.group(1))
        period = match.group(2)

        # Convert period to Redis TTL and time window
        time_mapping = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
        }

        if period not in time_mapping:
            raise ValueError(
                f"Unsupported period '{period}'. Supported periods: {', '.join(time_mapping.keys())}"
            )

        return count, time_mapping[period]

    async def check(self, cpf: str) -> bool:
        """
        Check if a request is allowed for the given CPF.

        Args:
            cpf (str): The CPF to check.

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        key = f"cpf_rate_limiter:{cpf}"
        async with self._redis.pipeline() as pipe:
            try:
                # Watch the key to detect changes from other clients
                await pipe.watch(key)

                # Get the current count
                current_count = await pipe.get(key)
                if current_count is None:
                    # Key does not exist, this is the first request
                    pipe.multi()
                    await pipe.set(key, 1, ex=self._time_window)
                    await pipe.execute()
                    return True  # Allow the request

                else:
                    current_count = int(current_count)

                    if current_count < self._max_requests:
                        # We are below the limit, increment the count
                        pipe.multi()
                        await pipe.incr(key)
                        await pipe.execute()
                        return True  # Allow the request

                    else:
                        # Rate limit exceeded
                        return False
            except WatchError:
                # Another client changed the key, retry
                return self.check(cpf)

    async def get_remaining(self, cpf: str) -> UserCortexRemainingCreditOut:
        """
        Get the remaining credit for the given CPF.

        Args:
            cpf (str): The CPF to check.

        Returns:
            UserCortexRemainingCreditOut: The remaining credit for the CPF.
        """
        key = f"cpf_rate_limiter:{cpf}"
        current_count = await self._redis.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        time_to_live = await self._redis.ttl(key)
        if time_to_live == -2:
            # Key does not exist, this is the first request
            time_to_live = self._time_window

        return UserCortexRemainingCreditOut(
            remaining_credit=self._max_requests - current_count,
            time_until_reset=time_to_live,
        )


cpf_limiter = RateLimiterCPF()
