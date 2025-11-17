"""Map rendering utilities with parallel processing support"""

import multiprocessing
import pandas as pd
import os
from pathlib import Path
from uuid import uuid4

from app.modules.cloning_report.utils import VMAX_KMH, ensure_dir, get_temp_dir
from app.modules.cloning_report.maps.generators.map_generator import MapGenerator
from app.modules.cloning_report.maps.export.screenshot import (
    take_html_screenshot,
    take_html_screenshots_batch,
)


class MapRenderer:
    """High-performance map renderer with parallel screenshot processing by default"""

    def __init__(
        self,
        use_clusters: bool = True,
        vmax_kmh: float = VMAX_KMH,
        enable_parallel: bool = True,
        max_workers: int | None = None,
        output_dir: Path | None = None,
    ):
        self.map_generator = MapGenerator(use_clusters, vmax_kmh)
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
        base_dir = get_temp_dir("maps")
        self.temp_dir = ensure_dir(base_dir / "html")
        self.output_dir = ensure_dir(output_dir or base_dir / "png")

    def render_overall_map_png(self, df_sus: pd.DataFrame) -> str | None:
        """Render overall map as PNG"""
        if df_sus is None or df_sus.empty:
            return None

        tmp = self._temp_file("mapa_clonagem_overall", suffix=".html")
        out = self.output_dir / "mapa_clonagem_overall.png"

        html = self.map_generator.generate_map_clonagem(df_sus, base_only=True)

        return self._save_html_to_png(html, tmp, out)

    def render_daily_figures(self, df_sus: pd.DataFrame) -> list[dict[str, str]]:
        """Render daily figures - optimized with parallel processing"""
        if df_sus is None or df_sus.empty:
            return []

        df = df_sus.copy()
        df["Data_ts"] = pd.to_datetime(df["Data_ts"], errors="coerce", utc=True)

        daily_data = []
        for day, _g in df.groupby(df["Data_ts"].dt.strftime("%d/%m/%Y"), sort=True):
            day_data = df[df["Data_ts"].dt.strftime("%d/%m/%Y") == day]
            daily_data.append((day, day_data))

        if not self.enable_parallel:
            return self._render_daily_sequential(daily_data)
        else:
            return self._render_daily_parallel(daily_data)

    def _render_daily_sequential(self, daily_data: list[tuple]) -> list[dict[str, str]]:
        """Sequential daily rendering (original method)"""
        figs = []

        for day, day_data in daily_data:
            html_str = self.map_generator.generate_map_clonagem(day_data)
            safe_day = pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")
            tmp = self._temp_file(f"mapa_clonagem_{safe_day}", suffix=".html")
            out = self.output_dir / f"mapa_clonagem_{safe_day}.png"

            result = self._save_html_to_png(html_str, tmp, out)
            if result:
                figs.append({"date": day, "path": result})

        return figs

    def _render_daily_parallel(self, daily_data: list[tuple]) -> list[dict[str, str]]:
        """Parallel daily rendering - HIGH PERFORMANCE"""
        html_files = []
        png_files = []
        day_mapping = {}

        for day, day_data in daily_data:
            html_str = self.map_generator.generate_map_clonagem(day_data)
            safe_day = pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")

            tmp_path = self._temp_file(f"mapa_clonagem_{safe_day}", suffix=".html")
            out_path = self.output_dir / f"mapa_clonagem_{safe_day}.png"

            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(html_str)

            html_files.append(str(tmp_path))
            png_files.append(str(out_path))
            day_mapping[str(out_path)] = day

        try:
            result = take_html_screenshots_batch(
                html_files,
                png_files,
                width=1280,
                height=800,
                max_workers=self.max_workers,
            )

            figs = []
            successful_pngs = set()

            for task_result in result["results"]:
                if task_result["success"]:
                    png_path = task_result["task"].png_path
                    successful_pngs.add(png_path)
                    day = day_mapping[png_path]
                    figs.append({"date": day, "path": png_path})
                else:
                    print(f"[WARN] Screenshot failed: {task_result['message']}")

            return sorted(figs, key=lambda x: x["date"])

        finally:
            for html_file in html_files:
                try:
                    os.remove(html_file)
                except Exception:
                    pass

    def _save_html_to_png(
        self, html: str, tmp_path: Path, out_path: Path
    ) -> str | None:
        """Save HTML as PNG (single file)"""
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(html)

        try:
            take_html_screenshot(str(tmp_path), str(out_path))
            return str(out_path)
        except Exception as e:
            print(f"[WARN] Screenshot failed: {e}")
            return None
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    def _temp_file(self, base_name: str, suffix: str = "") -> Path:
        """Generate a unique temporary file path for parallel-safe usage."""
        unique_name = f"{base_name}_{uuid4().hex}{suffix}"
        return self.temp_dir / unique_name
