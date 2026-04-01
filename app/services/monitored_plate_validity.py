"""Job de validade para vínculos placa–demandante: expiração e aviso Discord."""

from __future__ import annotations

from datetime import timedelta

import httpx
import pendulum
from loguru import logger

from app import config
from app.enums import NotificationChannelTypeEnum
from app.models import MonitoredPlate, MonitoredPlateDemandant

DISCORD_CONTENT_MAX = 1900
SEVEN_DAYS = timedelta(days=7)


def _to_tz(dt) -> pendulum.DateTime:
    if dt is None:
        raise ValueError("datetime is None")
    return pendulum.instance(dt).in_timezone(config.TIMEZONE)


def _vigencia_start(link: MonitoredPlateDemandant) -> pendulum.DateTime:
    """Referência para (valid_until − início) ≥ 7 dias: `updated_at`, senão `created_at`."""
    raw = link.updated_at if link.updated_at is not None else link.created_at
    return _to_tz(raw)


async def _post_discord_webhook(webhook_url: str, content: str) -> None:
    text = (
        content
        if len(content) <= DISCORD_CONTENT_MAX
        else content[: DISCORD_CONTENT_MAX - 3] + "..."
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(webhook_url, json={"content": text})
        r.raise_for_status()


async def _post_discord_for_plate(plate: MonitoredPlate, content: str) -> None:
    channels = await plate.notification_channels.filter(active=True).all()
    for ch in channels:
        if ch.channel_type != NotificationChannelTypeEnum.DISCORD:
            continue
        url = (ch.parameters or {}).get("webhook_url")
        if not url:
            logger.warning(
                "Discord channel {} has no webhook_url; skipping",
                ch.id,
            )
            continue
        try:
            await _post_discord_webhook(url, content)
        except Exception as exc:
            logger.error(
                "Discord webhook failed for channel {} plate {}: {}",
                ch.id,
                plate.plate,
                exc,
            )


async def expire_demandant_links() -> int:
    """Define active=false quando valid_until passou. Retorna quantidade atualizada."""
    now = pendulum.now(tz=config.TIMEZONE)
    qs = MonitoredPlateDemandant.filter(
        active=True,
        valid_until__isnull=False,
        valid_until__lt=now,
    )
    links = await qs.prefetch_related("monitored_plate", "demandant")
    count = 0
    for link in links:
        demandant = await link.demandant
        plate = await link.monitored_plate
        link.active = False
        await link.save(update_fields=["active", "updated_at"])
        count += 1
        dname = demandant.name or str(demandant.id)
        msg = (
            f"[CIVITAS] Vínculo placa **{plate.plate}** / demandante **{dname}** "
            f"(ref. {link.reference_number}) expirou em {link.valid_until}."
        )
        await _post_discord_for_plate(plate, msg)
    if count:
        logger.info("expire_demandant_links: {} link(s) inativado(s)", count)
    return count


async def send_validity_seven_day_warnings() -> int:
    """
    Aviso Discord exatamente 7 dias antes da data de valid_until (no fuso TIMEZONE),
    somente se o intervalo (início da vigência -> valid_until) for >= 7 dias.
    O início da vigência é ``updated_at`` do vínculo (última alteração), ou
    ``created_at`` se ``updated_at`` for nulo (legado).
    """
    now = pendulum.now(tz=config.TIMEZONE)
    qs = MonitoredPlateDemandant.filter(
        active=True,
        valid_until__isnull=False,
        validity_warning_sent_at__isnull=True,
    )
    links = await qs.prefetch_related("monitored_plate", "demandant")
    sent = 0
    for link in links:
        valid = _to_tz(link.valid_until)
        vigencia_start = _vigencia_start(link)
        if valid - vigencia_start < SEVEN_DAYS:
            continue
        warning_day = valid.subtract(days=7).date()
        if now.date() != warning_day:
            continue
        demandant = await link.demandant
        plate = await link.monitored_plate
        dname = demandant.name or str(demandant.id)
        msg = (
            f"[CIVITAS] Aviso: vínculo placa **{plate.plate}** / demandante **{dname}** "
            f"(ref. {link.reference_number}) expira em 7 dias (**{valid.date()}**)."
        )
        await _post_discord_for_plate(plate, msg)
        link.validity_warning_sent_at = now
        await link.save(update_fields=["validity_warning_sent_at", "updated_at"])
        sent += 1
    if sent:
        logger.info("send_validity_seven_day_warnings: {} aviso(s) enviado(s)", sent)
    return sent


async def run_monitored_plate_validity_jobs() -> dict:
    """Executa expiração e, em seguida, avisos de 7 dias."""
    expired = await expire_demandant_links()
    warned = await send_validity_seven_day_warnings()
    return {"expired_links": expired, "seven_day_warnings": warned}
