"""Unified batch processing for all map types with improved readability."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from app.modules.cloning_report.utils import ReportPaths
from app.modules.cloning_report.maps.generators import MapRenderer, TrailsMapGenerator
from app.modules.cloning_report.maps.export import (
    take_html_screenshots_batch,
    ScreenshotTask,
)


@dataclass(frozen=True)
class HtmlTask:
    kind: Literal["daily", "overall", "trail"]
    html_path: Path
    png_path: Path
    day: str | None = None
    car: str | None = None
    width: int = 1280
    height: int = 800

    def to_screenshot_task(self) -> ScreenshotTask:
        return ScreenshotTask(
            str(self.html_path), str(self.png_path), self.width, self.height
        )


class UnifiedMapBatchProcessor:
    """Processes ALL map types in a single parallel batch for maximum performance"""

    def __init__(self, enable_parallel: bool = True):
        self.enable_parallel = enable_parallel
        self.map_renderer = MapRenderer(enable_parallel=enable_parallel)
        self.trails_generator = TrailsMapGenerator()

    def process_all_maps(
        self,
        df_sus: pd.DataFrame,
        trails_tables: dict[str, Any],
        report_name: str | None = None,
    ) -> dict[str, Any]:
        """Process ALL maps (daily, overall, trails) in one parallel batch"""
        with ReportPaths.optional_report_context(report_name):
            if not self.enable_parallel:
                return self._process_sequential(df_sus, trails_tables)

            # Step 1: Generate all HTML content
            html_tasks = self._generate_all_html(df_sus, trails_tables)

            if not html_tasks:
                return {"daily_figures": [], "overall_map": None, "trails_maps": {}}

            # Step 2: Process all screenshots in one parallel batch
            screenshot_tasks = [task.to_screenshot_task() for task in html_tasks]
            result = take_html_screenshots_batch(
                [task.html_path for task in screenshot_tasks],
                [task.png_path for task in screenshot_tasks],
                max_workers=None,
            )

            # Step 3: Process results
            output = self._process_batch_results(html_tasks, result)
            return output

    def _generate_all_html(
        self, df_sus: pd.DataFrame, trails_tables: dict[str, Any]
    ) -> list[HtmlTask]:
        """Generate HTML for all map types"""
        html_tasks = []

        # 1. Daily maps
        html_tasks.extend(self._prepare_daily_maps(df_sus))

        # 2. Overall map
        overall_task = self._prepare_overall_map(df_sus)
        if overall_task:
            html_tasks.append(overall_task)

        # 3. Trail maps
        html_tasks.extend(self._prepare_trail_maps(df_sus, trails_tables))

        return html_tasks

    def _prepare_daily_maps(self, df_sus: pd.DataFrame) -> list[HtmlTask]:
        """Prepare daily map HTML files"""
        if df_sus is None or df_sus.empty:
            return []

        df = df_sus.copy()
        df["Data_ts"] = pd.to_datetime(df["Data_ts"], errors="coerce", utc=True)

        daily_tasks = []
        for day, _g in df.groupby(df["Data_ts"].dt.strftime("%d/%m/%Y"), sort=True):
            day_data = df[df["Data_ts"].dt.strftime("%d/%m/%Y") == day]

            html_str = self.map_renderer.map_generator.generate_map_clonagem(day_data)
            safe_day = pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")

            tmp_path = ReportPaths.temp_html_path(f"batch_daily_{safe_day}.html")
            out_path = ReportPaths.figure_path(f"mapa_clonagem_{safe_day}.png")

            # Write HTML file
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(html_str)

            daily_tasks.append(
                HtmlTask(kind="daily", day=day, html_path=tmp_path, png_path=out_path)
            )

        return daily_tasks

    def _prepare_overall_map(self, df_sus: pd.DataFrame) -> HtmlTask | None:
        """Prepare overall map HTML file"""
        if df_sus is None or df_sus.empty:
            return None

        tmp_path = ReportPaths.temp_html_path("batch_overall.html")
        out_path = ReportPaths.figure_path("mapa_clonagem_overall.png")

        html = self.map_renderer.map_generator.generate_map_clonagem(
            df_sus, base_only=True
        )

        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(html)

        return HtmlTask(kind="overall", html_path=tmp_path, png_path=out_path)

    def _prepare_trail_maps(
        self, df_sus: pd.DataFrame, trails_tables: dict[str, Any]
    ) -> list[HtmlTask]:
        """Prepare trail map HTML files"""
        trail_tasks = []

        if df_sus is None or df_sus.empty or not trails_tables:
            return trail_tasks

        # Process each day's trails
        df = df_sus.copy()
        df["Data_ts"] = pd.to_datetime(df["Data_ts"], errors="coerce", utc=True)

        for day, _g in df.groupby(df["Data_ts"].dt.strftime("%d/%m/%Y"), sort=True):
            trails_tables_day = trails_tables.get(day, {})
            if not trails_tables_day:
                continue

            # Generate trail HTML for each car
            for car_key in ["carro1", "carro2"]:
                trail_html = self._generate_trail_html(
                    df_sus, day, trails_tables_day, car_key
                )
                if trail_html:
                    safe_day = pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")
                    tmp_path = ReportPaths.temp_html_path(
                        f"batch_trail_{safe_day}_{car_key}.html"
                    )
                    out_path = ReportPaths.figure_path(
                        f"trilha_{safe_day}_{car_key}.png"
                    )

                    # Write HTML file
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        f.write(trail_html)

                    trail_tasks.append(
                        HtmlTask(
                            kind="trail",
                            day=day,
                            car=car_key,
                            html_path=tmp_path,
                            png_path=out_path,
                            width=1200,
                            height=800,
                        )
                    )

        return trail_tasks

    def _generate_trail_html(
        self,
        df_sus: pd.DataFrame,
        day: str,
        trails_tables_day: dict[str, Any],
        car_key: str,
    ) -> str | None:
        """Generate HTML for a specific trail map"""
        return self.trails_generator._build_map_html_for_car(
            df_sus, day, trails_tables_day, car_key
        )

    def _process_batch_results(
        self, html_tasks: list[HtmlTask], result: dict[str, Any]
    ) -> dict[str, Any]:
        """Process batch screenshot results"""
        daily_figures = []
        overall_map = None
        trails_maps = {}

        # Map results back to original tasks
        for task, task_result in zip(html_tasks, result["results"], strict=False):
            if not task_result["success"]:
                continue

            png_path = task_result["task"].png_path

            if task.kind == "daily" and task.day:
                daily_figures.append({"date": task.day, "path": png_path})
            elif task.kind == "overall":
                overall_map = png_path
            elif task.kind == "trail" and task.day and task.car:
                trails_maps.setdefault(task.day, {})[task.car] = png_path

        return {
            "daily_figures": sorted(daily_figures, key=lambda x: x["date"]),
            "overall_map": overall_map,
            "trails_maps": trails_maps,
        }

    def _process_sequential(
        self, df_sus: pd.DataFrame, trails_tables: dict[str, Any]
    ) -> dict[str, Any]:
        """Fallback to sequential processing"""
        print("📝 Using sequential processing...")

        # Use original methods
        daily_figures = self.map_renderer.render_daily_figures(df_sus)
        overall_map = self.map_renderer.render_overall_map_png(df_sus)

        # Generate trails maps
        trails_maps = {}
        if df_sus is not None and not df_sus.empty and trails_tables:
            df = df_sus.copy()
            df["Data_ts"] = pd.to_datetime(df["Data_ts"], errors="coerce", utc=True)

            for day, _g in df.groupby(df["Data_ts"].dt.strftime("%d/%m/%Y"), sort=True):
                trails_tables_day = trails_tables.get(day, {})
                if trails_tables_day:
                    trails_maps[day] = self.trails_generator.generate_trails_map(
                        df_sus, day, trails_tables_day
                    )

        return {
            "daily_figures": daily_figures,
            "overall_map": overall_map,
            "trails_maps": trails_maps,
        }
