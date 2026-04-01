"""Testes do job de validade (expiração + aviso 7 dias), com SQLite em memória."""

import uuid
from unittest.mock import AsyncMock, patch

import pendulum
import pytest
import pytest_asyncio
from tortoise import Tortoise

from app.models import Demandant, MonitoredPlate, MonitoredPlateDemandant, Organization
from app.services.monitored_plate_validity import (
    expire_demandant_links,
    run_monitored_plate_validity_jobs,
    send_validity_seven_day_warnings,
)


def _unique_plate() -> str:
    """7 caracteres alfanuméricos (formato livre para o modelo)."""
    return (uuid.uuid4().hex[:7]).upper()


async def _force_created_at(link_id, when: pendulum.DateTime) -> None:
    """Tortoise ignora `created_at` no `create()` quando há auto_now_add; força via SQL."""
    conn = Tortoise.get_connection("default")
    await conn.execute_query(
        "UPDATE monitoredplate_demandant SET created_at = ? WHERE id = ?",
        [when.to_iso8601_string(), str(link_id)],
    )


async def _force_updated_at(link_id, when: pendulum.DateTime) -> None:
    conn = Tortoise.get_connection("default")
    await conn.execute_query(
        "UPDATE monitoredplate_demandant SET updated_at = ? WHERE id = ?",
        [when.to_iso8601_string(), str(link_id)],
    )


TEST_DB = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.sqlite",
            "credentials": {"file_path": ":memory:"},
        }
    },
    "apps": {
        "app": {
            "models": ["app.models"],
            "default_connection": "default",
        },
    },
}


@pytest_asyncio.fixture
async def initialize_db():
    """Escopo por teste: evita RuntimeError de lock/event loop com asyncio strict."""
    await Tortoise.init(config=TEST_DB)
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest_asyncio.fixture
async def seed_plate_and_demandant(initialize_db):
    org = await Organization.create(
        name="Test Org",
        organization_type="test",
        acronym="TO",
        jurisdiction_level="local",
    )
    dem = await Demandant.create(organization=org, name="Demandante Teste")
    plate = await MonitoredPlate.create(plate=_unique_plate(), notes="test")
    return plate, dem


@pytest.mark.asyncio
async def test_expire_sets_inactive_when_valid_until_passed(seed_plate_and_demandant):
    plate, dem = seed_plate_and_demandant
    yesterday = pendulum.now(tz="America/Sao_Paulo").subtract(days=1)
    link = await MonitoredPlateDemandant.create(
        monitored_plate=plate,
        demandant=dem,
        reference_number="REF-1",
        valid_until=yesterday,
        active=True,
    )
    with patch(
        "app.services.monitored_plate_validity._post_discord_for_plate",
        new_callable=AsyncMock,
    ) as mock_dc:
        n = await expire_demandant_links()
    assert n == 1
    mock_dc.assert_awaited()
    await link.refresh_from_db()
    assert link.active is False


@pytest.mark.asyncio
async def test_seven_day_warning_only_when_eligible_and_correct_day(
    seed_plate_and_demandant,
):
    plate, dem = seed_plate_and_demandant
    fixed_now = pendulum.datetime(2026, 3, 20, 12, 0, 0, tz="America/Sao_Paulo")
    valid_until = pendulum.datetime(2026, 3, 27, 23, 59, 0, tz="America/Sao_Paulo")
    created_back = pendulum.datetime(2026, 3, 1, 10, 0, 0, tz="America/Sao_Paulo")
    link = await MonitoredPlateDemandant.create(
        monitored_plate=plate,
        demandant=dem,
        reference_number="REF-7D",
        valid_until=valid_until,
        active=True,
    )
    await _force_created_at(link.id, created_back)
    await _force_updated_at(link.id, created_back)

    with (
        patch(
            "app.services.monitored_plate_validity.pendulum.now",
            return_value=fixed_now,
        ),
        patch(
            "app.services.monitored_plate_validity._post_discord_for_plate",
            new_callable=AsyncMock,
        ) as mock_dc,
    ):
        n = await send_validity_seven_day_warnings()

    assert n == 1
    mock_dc.assert_awaited()
    await link.refresh_from_db()
    assert link.validity_warning_sent_at is not None


@pytest.mark.asyncio
async def test_seven_day_skipped_when_vigencia_menor_que_7_dias(
    seed_plate_and_demandant,
):
    plate, dem = seed_plate_and_demandant
    fixed_now = pendulum.datetime(2026, 3, 20, 12, 0, 0, tz="America/Sao_Paulo")
    valid_until = pendulum.datetime(2026, 3, 27, 23, 59, 0, tz="America/Sao_Paulo")
    created_recent = pendulum.datetime(2026, 3, 25, 10, 0, 0, tz="America/Sao_Paulo")
    link = await MonitoredPlateDemandant.create(
        monitored_plate=plate,
        demandant=dem,
        reference_number="REF-SHORT",
        valid_until=valid_until,
        active=True,
    )
    await _force_updated_at(link.id, created_recent)

    with (
        patch(
            "app.services.monitored_plate_validity.pendulum.now",
            return_value=fixed_now,
        ),
        patch(
            "app.services.monitored_plate_validity._post_discord_for_plate",
            new_callable=AsyncMock,
        ) as mock_dc,
    ):
        n = await send_validity_seven_day_warnings()

    assert n == 0
    mock_dc.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_monitored_plate_validity_jobs_runs_both(seed_plate_and_demandant):
    plate, dem = seed_plate_and_demandant
    yesterday = pendulum.now(tz="America/Sao_Paulo").subtract(days=1)
    await MonitoredPlateDemandant.create(
        monitored_plate=plate,
        demandant=dem,
        reference_number="REF-X",
        valid_until=yesterday,
        active=True,
    )
    with patch(
        "app.services.monitored_plate_validity._post_discord_for_plate",
        new_callable=AsyncMock,
    ):
        result = await run_monitored_plate_validity_jobs()
    assert result["expired_links"] == 1
    assert result["seven_day_warnings"] == 0
