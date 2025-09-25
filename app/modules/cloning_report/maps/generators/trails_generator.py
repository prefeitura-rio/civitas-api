"""Trails map generation"""

import folium
import pandas as pd
import numpy as np
import os
from folium.plugins import BeautifyIcon

from ...clustering.graph_builder import GraphBuilder

from ...utils import BLUE_LIGHT, BLUE_DARK

# from ...clustering import graph_from_pairs_day
from ...utils import ensure_dir
from ..utils.formatting import format_timestamp
from ..export.screenshot import take_html_screenshot


class TrailsMapGenerator:
    """Gerador de mapas de trilhas"""

    def __init__(self, width: int = 1200, height: int = 800):
        self.width = width
        self.height = height

    def generate_trails_map(
        self, df_sus: pd.DataFrame, day: str, trails_tables_day: dict
    ) -> dict[str, str | None]:
        """Gera mapas de trilhas para um dia específico"""
        out_paths = {"carro1": None, "carro2": None}
        if self._is_invalid_data(df_sus, trails_tables_day):
            return out_paths

        day_data = self._get_day_data(df_sus, day)
        if day_data.empty:
            return out_paths

        key_to_xy = self._build_coordinate_mapping(day_data)

        return {
            "carro1": self._build_map_for_car(
                "carro1", BLUE_LIGHT, trails_tables_day, key_to_xy, day
            ),
            "carro2": self._build_map_for_car(
                "carro2", BLUE_DARK, trails_tables_day, key_to_xy, day
            ),
        }

    def _is_invalid_data(self, df_sus: pd.DataFrame, trails_tables_day: dict) -> bool:
        """Verifica se os dados são inválidos"""
        return df_sus is None or df_sus.empty or trails_tables_day is None

    def _get_day_data(self, df_sus: pd.DataFrame, day: str) -> pd.DataFrame:
        """Obtém dados de um dia específico"""
        dfx = df_sus.copy()
        dfx["Data_ts"] = pd.to_datetime(dfx["Data_ts"], errors="coerce", utc=True)
        dfx["_day"] = dfx["Data_ts"].dt.strftime("%d/%m/%Y")
        return dfx[dfx["_day"] == day].reset_index(drop=True)

    def _build_coordinate_mapping(
        self, day_data: pd.DataFrame
    ) -> dict[tuple[str, str], tuple[float, float]]:
        """Constrói mapeamento de coordenadas"""
        # df_nodes, _ = graph_from_pairs_day(day_data)
        df_nodes, _ = GraphBuilder.create_nodes_and_edges(day_data)

        df_nodes = df_nodes.copy()
        dh = pd.to_datetime(df_nodes["datahora"], errors="coerce")
        df_nodes["DataHora_str"] = dh.dt.tz_convert(None).dt.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
        df_nodes["Local"] = df_nodes.get("logradouro", "").astype(str)

        return dict(
            zip(
                zip(df_nodes["DataHora_str"], df_nodes["Local"]),
                zip(
                    df_nodes["latitude"].astype(float),
                    df_nodes["longitude"].astype(float),
                ),
            )
        )

    def _build_map_for_car(
        self,
        car_key: str,
        color_hex: str,
        trails_tables_day: dict,
        key_to_xy: dict[tuple[str, str], tuple[float, float]],
        day: str,
    ) -> str | None:
        """Constrói mapa para um carro específico"""
        tbl = trails_tables_day.get(car_key)
        if tbl is None or tbl.empty:
            return None

        coords = self._extract_coordinates(tbl, key_to_xy)
        if not coords:
            return None

        m = self._create_map(coords)
        self._add_markers(m, coords, tbl, color_hex)
        self._fit_bounds(m, coords)

        return self._save_map(m, day, car_key)

    def _build_map_html_for_car(
        self, df_sus: pd.DataFrame, day: str, trails_tables_day: dict, car_key: str
    ) -> str | None:
        """Builds HTML for a car trail map without saving to file"""
        tbl = trails_tables_day.get(car_key)
        if tbl is None or tbl.empty:
            return None

        day_data = self._get_day_data(df_sus, day)
        if day_data.empty:
            return None

        key_to_xy = self._build_coordinate_mapping(day_data)
        coords = self._extract_coordinates(tbl, key_to_xy)
        if not coords:
            return None

        color_hex = BLUE_LIGHT if car_key == "carro1" else BLUE_DARK
        m = self._create_map(coords)
        self._add_markers(m, coords, tbl, color_hex)
        self._fit_bounds(m, coords)

        return m.get_root().render()

    def _extract_coordinates(
        self, tbl: pd.DataFrame, key_to_xy: dict[tuple[str, str], tuple[float, float]]
    ) -> list:
        """Extrai coordenadas da tabela"""
        t = tbl.copy()
        t["DataHora"] = pd.to_datetime(
            t["DataHora"], errors="coerce", format="%Y-%m-%d %H:%M:%S"
        )
        t = t.sort_values("DataHora").reset_index(drop=True)
        t["DataHora_str"] = t["DataHora"].dt.strftime("%d/%m/%Y %H:%M:%S")
        t["Local"] = t["Local"].astype(str)

        coords = []
        for _, rr in t.iterrows():
            xy = self._find_coordinate(rr, key_to_xy)
            if xy is not None:
                coords.append((float(xy[0]), float(xy[1])))

        return coords

    def _find_coordinate(
        self, row: pd.Series, key_to_xy: dict[tuple[str, str], tuple[float, float]]
    ) -> tuple[float, float] | None:
        """Encontra coordenada para uma linha"""
        xy = key_to_xy.get((row["DataHora_str"], row["Local"]))
        if xy is None:
            xy = next(
                (v for (kk, _loc), v in key_to_xy.items() if kk == row["DataHora_str"]),
                None,
            )
        return xy

    def _create_map(self, coords: list) -> folium.Map:
        """Cria mapa base"""
        lat_center = float(np.mean([c[0] for c in coords]))
        lon_center = float(np.mean([c[1] for c in coords]))
        return folium.Map(
            location=[lat_center, lon_center],
            zoom_start=13,
            tiles="CartoDB Positron",
            control_scale=True,
        )

    def _add_markers(
        self, m: folium.Map, coords: list, tbl: pd.DataFrame, color_hex: str
    ) -> None:
        """Adiciona marcadores ao mapa"""
        for idx, ((lat, lon), (_, rr)) in enumerate(
            zip(coords, tbl.iterrows()), start=1
        ):
            self._add_single_marker(m, lat, lon, rr, color_hex, idx)

    def _add_single_marker(
        self,
        m: folium.Map,
        lat: float,
        lon: float,
        row: pd.Series,
        color_hex: str,
        idx: int,
    ) -> None:
        """Adiciona um marcador individual"""
        label = str(row.get("Local") or "").strip()
        ts_str = format_timestamp(row.get("DataHora"))
        tooltip_txt = f"{label} - {ts_str}"
        popup_txt = tooltip_txt
        text_color = "#000000" if color_hex.lower() == BLUE_LIGHT.lower() else "#ffffff"

        icon = BeautifyIcon(
            icon="arrow-down",
            icon_shape="marker",
            number=str(idx),
            text_color=text_color,
            border_color="rgba(0,0,0,.35)",
            background_color=color_hex,
            inner_icon_style="font-weight:700;font-size:15px;",
        )

        folium.Marker(
            [lat, lon],
            icon=icon,
            tooltip=tooltip_txt,
            popup=folium.Popup(popup_txt, max_width=360),
        ).add_to(m)

    def _fit_bounds(self, m: folium.Map, coords: list) -> None:
        """Aplica bounds ao mapa"""
        lat_min, lat_max = (
            float(np.min([c[0] for c in coords])),
            float(np.max([c[0] for c in coords])),
        )
        lon_min, lon_max = (
            float(np.min([c[1] for c in coords])),
            float(np.max([c[1] for c in coords])),
        )
        pad_lat = max((lat_max - lat_min) * 0.15, 0.01)
        pad_lon = max((lon_max - lon_min) * 0.15, 0.01)
        bounds = [
            [lat_min - pad_lat, lon_min - pad_lon],
            [lat_max + pad_lat, lon_max + pad_lon],
        ]
        try:
            m.fit_bounds(bounds)
        except Exception:
            pass

    def _save_map(self, m: folium.Map, day: str, car_key: str) -> str | None:
        """Salva mapa como PNG"""
        safe_day = pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")
        tmp_html = ensure_dir("temp_files") / f"trilha_{safe_day}_{car_key}.html"
        out_png = (
            ensure_dir("app/assets/cloning_report/figs")
            / f"trilha_{safe_day}_{car_key}.png"
        )

        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(m.get_root().render())

        try:
            take_html_screenshot(
                str(tmp_html), str(out_png), width=self.width, height=self.height
            )
            return str(out_png)
        finally:
            try:
                os.remove(tmp_html)
            except Exception:
                pass
