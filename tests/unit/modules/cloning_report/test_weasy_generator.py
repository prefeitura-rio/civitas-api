import os
from unittest.mock import patch

import pandas as pd
import pytest

os.environ.setdefault("ENVIRONMENT", "dev")
os.environ.setdefault("INFISICAL_ADDRESS", "https://infisical.local")
os.environ.setdefault("INFISICAL_TOKEN", "dummy-token")
os.environ.setdefault("OIDC_BASE_URL", "https://oidc.local")
os.environ.setdefault("OIDC_CLIENT_ID", "client-id")
os.environ.setdefault("OIDC_CLIENT_SECRET", "client-secret")
os.environ.setdefault("OIDC_ISSUER_URL", "https://oidc.local/issuer")
os.environ.setdefault("OIDC_TOKEN_URL", "https://oidc.local/token")
os.environ.setdefault("GOOGLE_MAPS_API_KEY", "maps-key")
os.environ.setdefault("DATA_RELAY_BASE_URL", "https://relay.local")
os.environ.setdefault("DATA_RELAY_USERNAME", "user")
os.environ.setdefault("DATA_RELAY_PASSWORD", "pass")
os.environ.setdefault("DATA_RELAY_PUBLISH_TOKEN", "publish-token")
os.environ.setdefault("FOGOCRUZADO_BASE_URL", "https://fogocruzado.local")
os.environ.setdefault("FOGOCRUZADO_USERNAME", "fogouser")
os.environ.setdefault("FOGOCRUZADO_PASSWORD", "fogopass")
os.environ.setdefault("CORTEX_PESSOAS_BASE_URL", "https://cortex.local/pessoas")
os.environ.setdefault("CORTEX_VEICULOS_BASE_URL", "https://cortex.local/veiculos")
os.environ.setdefault("CORTEX_USERNAME", "cortex-user")
os.environ.setdefault("CORTEX_PASSWORD", "cortex-pass")
os.environ.setdefault("TIXXI_CAMERAS_LIST_URL", "https://tixxi.local/cameras")
os.environ.setdefault("WEAVIATE_SCHEMA_CLASS", "Report")
os.environ.setdefault("EMBEDDINGS_SOURCE_TABLE", "table")
os.environ.setdefault("EMBEDDINGS_SOURCE_TABLE_ID_COLUMN", "id")
os.environ.setdefault("EMBEDDINGS_SOURCE_TABLE_SOURCE_COLUMN", "source")
os.environ.setdefault("EMBEDDINGS_SOURCE_TABLE_TEXT_COLUMN", "text")
os.environ.setdefault("EMBEDDINGS_SOURCE_TABLE_TIMESTAMP_COLUMN", "timestamp")
os.environ.setdefault(
    "UPDATE_EMBEDDINGS_DEBUG_DISCORD_WEBHOOK", "https://discord.local"
)
os.environ.setdefault("GCP_SERVICE_ACCOUNT_CREDENTIALS", "{}")

with (
    patch("infisical.InfisicalClient") as MockInfisicalClient,
    patch("urllib.request.urlopen") as mock_urlopen,
):
    MockInfisicalClient.return_value.get_all_secrets.return_value = []
    mock_urlopen.return_value.read.return_value = b"{}"
    from app.modules.cloning_report.report.weasy_generator import (
        ClonagemReportWeasyGenerator,
    )


@pytest.fixture()
def generator(monkeypatch):
    gen = object.__new__(ClonagemReportWeasyGenerator)
    gen.placa = "ABC1D23"
    gen.periodo_inicio = pd.Timestamp("2024-01-01T00:00:00Z")
    gen.periodo_fim = pd.Timestamp("2024-01-07T23:59:59Z")
    gen.meta_marca_modelo = "FORD/FOCUS"
    gen.meta_cor = "PRETA"
    gen.meta_ano_modelo = 2022
    gen.total_deteccoes = 42
    gen.num_suspeitos = 3
    gen.dia_mais_sus = "05/01/2024"
    gen.sus_dia_mais_sus = "2 registros"
    gen.max_vel = 180.5
    gen.turno_mais_sus = "Manhã"
    gen.turno_mais_sus_count = 2
    gen.place_lider = "Radar Central"
    gen.place_lider_count = 5
    gen.top_pair_str = "Radar A - Radar B"
    gen.top_pair_count = 3
    gen.report_id = "20240101.123456789"
    gen.bairro_pairs_png = "bairros.png"
    gen.results = {
        "dataframe": pd.DataFrame(
            [
                {
                    "Data": "05/01/2024 08:00",
                    "Origem": "Radar A",
                    "Destino": "Radar B",
                    "Km": 12.5,
                    "s": 300,
                    "Km/h": 150.0,
                }
            ]
        ),
        "daily_figures": [{"date": "05/01/2024", "path": "map-dia.png"}],
        "daily_tables": {
            "05/01/2024": {
                "todas": pd.DataFrame(
                    [
                        {
                            "Data": "05/01/2024 08:00",
                            "Origem": "Radar A",
                            "Destino": "Radar B",
                            "Km": 12.5,
                            "s": 300,
                            "Km/h": 150.0,
                        }
                    ]
                )
            }
        },
        "daily_track_tables": {
            "05/01/2024": {
                "carro1": pd.DataFrame(
                    [
                        {
                            "Data": "05/01/2024 08:00",
                            "Origem": "Radar A",
                            "Destino": "Radar B",
                        }
                    ]
                ),
                "carro2": pd.DataFrame(
                    [
                        {
                            "Data": "05/01/2024 08:05",
                            "Origem": "Radar C",
                            "Destino": "Radar D",
                        }
                    ]
                ),
            }
        },
    }

    monkeypatch.setattr(
        "app.modules.cloning_report.report.weasy_generator.render_overall_map_png",
        lambda df: "map-geral.png",
    )
    monkeypatch.setattr(
        ClonagemReportWeasyGenerator,
        "_generate_trail_maps",
        lambda self, day, tracks: {"carro1": "trilha1.png", "carro2": "trilha2.png"},
    )
    return gen


def test_build_template_context(generator):
    context = generator._build_template_context()

    assert context["report_id"] == "20240101.123456789"
    assert context["plate"] == "ABC1D23"
    assert context["general_map_path"] == "map-geral.png"
    assert context["kpi_cards"][1]["value"] == "3"
    assert context["summary_stats"]["total_records"] == "42"
    assert context["analysis_highlights"][0]["value"] == "Manhã (2)"
    assert context["time_interval_str"] == context["time_interval_text"]
    assert context["readings_count"] == "42"
    assert context["suspicious_readings_count"] == "3"
    assert context["turno_summary"] == "Manhã (2)"
    assert context["place_summary"] == "Radar Central (5)"
    assert context["top_pair_summary"] == "Radar A - Radar B (3)"
    assert context["max_speed_summary"] == "180.50 km/h"
    assert context["most_suspicious_day"] == "05/01/2024"
    assert context["most_suspicious_day_count"] == "2 registros"
    assert context["icon_radar_path"]
    assert context["icon_warning_path"]
    assert context["icon_calendar_path"]
    assert context["icon_clock_path"]
    assert context["icon_location_path"]
    assert context["icon_speed_path"]
    assert context["example_splitable_pair_figure_path"]
    assert context["example_non_splitable_pair_figure_path"]
    assert context["grafo_limited_nodes_path"]
    assert context["total_monitored_plates"] == "1"
    assert context["detections"] == [
        {
            "data": "05/01/2024 08:00",
            "origem": "Radar A",
            "destino": "Radar B",
            "km": "12.50",
            "seconds": "300",
            "kmh": "150",
        }
    ]
    assert context["general_table"]["headers"] == [
        "Data",
        "Origem",
        "Destino",
        "Km",
        "s",
        "Km/h",
    ]
    assert context["general_table"]["rows"][0][0] == "05/01/2024 08:00"

    assert context["daily_sections"][0]["map_path"] == "map-dia.png"
    assert context["daily_sections"][0]["tracks"][0]["map_path"] == "trilha1.png"
    assert context["daily_sections"][0]["tracks"][1]["map_path"] == "trilha2.png"
    assert context["daily_sections"][0]["tracks"][0]["has_table"] is True
    assert context["bairro_pairs_chart_path"] == "bairros.png"
    assert "A tabela apresenta os registros suspeitos" in context["general_table_note"]
