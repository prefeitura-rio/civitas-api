"""Main map generator class"""

import folium
import pandas as pd

from app.modules.cloning_report.clustering.clustering_validator import (
    ClusteringValidator,
)

from app.modules.cloning_report.utils import VMAX_KMH

# from ...clustering import is_clusterizable_day
from app.modules.cloning_report.maps.layers.layer_control import add_layer_control
from app.modules.cloning_report.maps.utils.mapping import fit_bounds_to_data
from app.modules.cloning_report.maps.generators.data_processor import DataProcessor
from app.modules.cloning_report.maps.generators.bounds_manager import BoundsManager
from app.modules.cloning_report.maps.generators.base_layer import BaseLayer
from app.modules.cloning_report.maps.generators.clustered_pairs_layer import (
    ClusteredPairsLayer,
)
from app.modules.cloning_report.maps.generators.other_detections_layer import (
    OtherDetectionsLayer,
)


class MapGenerator:
    """Gerador principal de mapas"""

    def __init__(
        self,
        use_clusters: bool = True,
        vmax_kmh: float = VMAX_KMH,
        verbose: bool = False,
    ):
        self.use_clusters = use_clusters
        self.vmax_kmh = vmax_kmh
        self.verbose = verbose

    def generate_map_clonagem(
        self,
        df_pairs: pd.DataFrame,
        *,
        base_only: bool = False,
        df_all: pd.DataFrame | None = None,
        show_other_daily: bool = False,
        include_non_sus_days: bool = False,
    ) -> str:
        """Gera mapa principal de clonagem"""
        if df_pairs is None or df_pairs.empty:
            return self._create_empty_map()

        processor = DataProcessor(df_pairs)
        center = processor.get_center()
        m = folium.Map(
            location=center, zoom_start=11, tiles="CartoDB Positron", control_scale=True
        )

        base_layer = BaseLayer(m, "Pares suspeitos de todo o período", "#808080", True)
        base_layer.add_to_map(processor.df_pairs)

        if base_only:
            add_layer_control(m, collapsed=False)
            all_lats, all_lons = processor.get_coordinates()
            if not all_lats.empty:
                BoundsManager.fit_simple_bounds(m, all_lats, all_lons)
            return m.get_root().render()

        self._process_daily_layers(m, processor, df_all, show_other_daily)
        self._process_non_suspicious_days(m, processor, df_all, include_non_sus_days)

        bounds_lats, bounds_lons = processor.get_bounds_coordinates(
            df_all, show_other_daily, include_non_sus_days
        )
        fit_bounds_to_data(m, bounds_lats, bounds_lons)
        add_layer_control(m, collapsed=False)

        return m.get_root().render()

    def _create_empty_map(self) -> str:
        """Cria mapa vazio"""
        m = folium.Map(
            location=[-22.90, -43.20],
            zoom_start=11,
            tiles="CartoDB Positron",
            control_scale=True,
        )
        add_layer_control(m, collapsed=False)
        return m.get_root().render()

    def _process_daily_layers(
        self,
        m: folium.Map,
        processor: DataProcessor,
        df_all: pd.DataFrame | None,
        show_other_daily: bool,
    ) -> None:
        """Processa layers diários"""
        order = processor.get_ordered_days()
        endpoints = set()

        for day in order:
            g = processor.get_day_data(day)
            if g.empty:
                continue

            can_cluster, labels = self._get_cluster_info(g)
            clustered_layer = ClusteredPairsLayer(m, f"{day} - Pares suspeitos", False)
            _, day_endpoints = clustered_layer.add_to_map(g, labels)
            endpoints.update(day_endpoints)

            if (
                show_other_daily
                and isinstance(df_all, pd.DataFrame)
                and not df_all.empty
            ):
                self._add_other_daily_detections(m, df_all, day, endpoints)

    def _get_cluster_info(self, g: pd.DataFrame) -> tuple[bool, dict[str, int] | None]:
        """Obtém informações de clusterização"""
        if not self.use_clusters:
            return False, None

        try:
            # can_cluster, meta = is_clusterizable_day(g, vmax_kmh=self.vmax_kmh)
            can_cluster, meta = ClusteringValidator.is_clusterizable(
                g, vmax_kmh=self.vmax_kmh
            )
            labels = meta.get("labels", {}) if can_cluster else None
            return can_cluster, labels
        except Exception as e:
            if self.verbose:
                print(f"[WARN] is_clusterizable_day falhou: {e}")
            return False, None

    def _add_other_daily_detections(
        self,
        m: folium.Map,
        df_all: pd.DataFrame,
        day: str,
        endpoints: set[tuple[float, float, pd.Timestamp]],
    ) -> None:
        """Adiciona outras detecções diárias"""
        dfa = df_all.copy()
        dfa["datahora"] = pd.to_datetime(dfa.get("datahora"), errors="coerce")
        dfa["_day"] = dfa["datahora"].dt.strftime("%d/%m/%Y")
        df_day_all = (
            dfa[dfa["_day"] == day]
            .dropna(subset=["latitude", "longitude", "datahora"])
            .copy()
        )

        other_layer = OtherDetectionsLayer(m, f"{day} - Detecções não suspeitas", False)
        other_layer.add_to_map(df_day_all, endpoints)

    def _process_non_suspicious_days(
        self,
        m: folium.Map,
        processor: DataProcessor,
        df_all: pd.DataFrame | None,
        include_non_sus_days: bool,
    ) -> None:
        """Processa dias não suspeitos"""
        if not include_non_sus_days or df_all is None:
            return

        dfa = df_all.copy()
        dfa["datahora"] = pd.to_datetime(dfa.get("datahora"), errors="coerce")
        dfa["_day"] = dfa["datahora"].dt.strftime("%d/%m/%Y")

        days_all = [d for d in dfa["_day"].dropna().unique().tolist()]
        sus_days = set(processor.get_ordered_days())
        extra_days = [
            d
            for d in sorted(days_all, key=lambda s: pd.to_datetime(s, dayfirst=True))
            if d not in sus_days
        ]

        for d in extra_days:
            gg = (
                dfa[dfa["_day"] == d]
                .dropna(subset=["latitude", "longitude", "datahora"])
                .copy()
            )
            other_layer = OtherDetectionsLayer(m, f"{d} (sem suspeitos)", False)
            other_layer.add_to_map(gg, set())
