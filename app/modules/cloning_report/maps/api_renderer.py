"""FastAPI-friendly map renderer with clean logging"""
import pandas as pd
import time
from typing import Dict, List, Optional, Any, Callable

from ..utils import get_logger, configure_logging, LogLevel, ScreenshotProgressTracker
from ..utils.progress import TaskProgress
from .generators import MapRenderer, TrailsMapGenerator
from .export.screenshot_clean import CleanScreenshotProcessor, ScreenshotTask
from ..config import APIConfig, ScreenshotConfig


class APIMapRenderer:
    """Production-ready map renderer for FastAPI deployment"""
    
    def __init__(self, log_level: LogLevel = LogLevel.INFO, 
                 progress_callback: Optional[Callable[[TaskProgress], None]] = None):
        self._setup_logging(log_level)
        self._initialize_components(progress_callback)
        self.logger.info("APIMapRenderer initialized")

    def _setup_logging(self, log_level: LogLevel):
        configure_logging(log_level)
        self.logger = get_logger()

    def _initialize_components(self, progress_callback: Optional[Callable[[TaskProgress], None]]):
        self.map_renderer = MapRenderer(enable_parallel=True)
        self.trails_generator = TrailsMapGenerator()
        self.screenshot_processor = CleanScreenshotProcessor(
            max_workers=ScreenshotConfig.DEFAULT_MAX_WORKERS,
            progress_callback=progress_callback
        )
    
    def generate_report_maps(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any],
                           task_id: str = "map_generation") -> Dict[str, Any]:
        """Generate all maps for a cloning report with clean progress tracking"""
        self.logger.info(f"Starting map generation for {len(df_sus)} suspicious pairs")
        start_time = time.time()
        
        try:
            # Prepare all HTML files
            html_tasks = self._prepare_all_html(df_sus, trails_tables)
            
            if not html_tasks:
                self.logger.warning("No HTML tasks generated")
                return self._empty_result()
            
            # Process all screenshots in one batch
            screenshot_tasks = [task['screenshot_task'] for task in html_tasks]
            result = self.screenshot_processor.process_screenshots(screenshot_tasks, task_id)
            
            # Process results
            output = self._process_results(html_tasks, result)
            
            total_time = time.time() - start_time
            self.logger.info(f"Map generation completed in {total_time:.2f}s")
            
            return output
            
        except Exception as e:
            error_msg = f"Map generation failed: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _prepare_all_html(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare HTML for all map types"""
        if df_sus is None or df_sus.empty:
            return []
        
        html_tasks = []
        self._add_all_map_types(html_tasks, df_sus, trails_tables)
        self._log_html_preparation(html_tasks)
        return html_tasks

    def _add_all_map_types(self, html_tasks: List[Dict[str, Any]], df_sus: pd.DataFrame, trails_tables: Dict[str, Any]):
        self._add_daily_maps(html_tasks, df_sus)
        self._add_overall_map(html_tasks, df_sus)
        self._add_trail_maps(html_tasks, df_sus, trails_tables)

    def _log_html_preparation(self, html_tasks: List[Dict[str, Any]]):
        self.logger.info(f"Prepared {len(html_tasks)} HTML files for processing")

    def _add_daily_maps(self, html_tasks: List[Dict[str, Any]], df_sus: pd.DataFrame):
        html_tasks.extend(self._prepare_daily_maps(df_sus))

    def _add_overall_map(self, html_tasks: List[Dict[str, Any]], df_sus: pd.DataFrame):
        overall_task = self._prepare_overall_map(df_sus)
        if overall_task:
            html_tasks.append(overall_task)

    def _add_trail_maps(self, html_tasks: List[Dict[str, Any]], df_sus: pd.DataFrame, trails_tables: Dict[str, Any]):
        html_tasks.extend(self._prepare_trail_maps(df_sus, trails_tables))
    
    def _prepare_daily_maps(self, df_sus: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare daily map HTML files"""
        daily_tasks = []
        df = self._prepare_daily_dataframe(df_sus)
        self._process_daily_groups(df, daily_tasks)
        return daily_tasks

    def _process_daily_groups(self, df: pd.DataFrame, daily_tasks: List[Dict[str, Any]]):
        for day, _g in df.groupby(df['Data_ts'].dt.strftime('%d/%m/%Y'), sort=True):
            self._process_daily_map(day, df, daily_tasks)

    def _prepare_daily_dataframe(self, df_sus: pd.DataFrame) -> pd.DataFrame:
        df = df_sus.copy()
        df['Data_ts'] = pd.to_datetime(df['Data_ts'], errors='coerce', utc=True)
        return df

    def _process_daily_map(self, day: str, df: pd.DataFrame, daily_tasks: List[Dict[str, Any]]):
        day_data = self._get_day_data(df, day)
        html_str = self._generate_daily_html(day_data)
        safe_day = self._get_safe_day(day)
        tmp_path, out_path = self._get_daily_paths(safe_day)
        self._save_daily_html(html_str, tmp_path)
        self._add_daily_task(day, tmp_path, out_path, daily_tasks)

    def _get_day_data(self, df: pd.DataFrame, day: str) -> pd.DataFrame:
        return df[df['Data_ts'].dt.strftime('%d/%m/%Y') == day]

    def _generate_daily_html(self, day_data: pd.DataFrame) -> str:
        return self.map_renderer.map_generator.generate_map_clonagem(day_data)

    def _get_safe_day(self, day: str) -> str:
        return pd.to_datetime(day, dayfirst=True).strftime('%Y-%m-%d')

    def _get_daily_paths(self, safe_day: str):
        from ..utils import ensure_dir
        tmp_path = ensure_dir('temp_files') / f"api_daily_{safe_day}.html"
        out_path = ensure_dir('figs') / f"mapa_clonagem_{safe_day}.png"
        return tmp_path, out_path

    def _save_daily_html(self, html_str: str, tmp_path):
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(html_str)

    def _add_daily_task(self, day: str, tmp_path, out_path, daily_tasks: List[Dict[str, Any]]):
        daily_tasks.append({
            'type': 'daily',
            'day': day,
            'screenshot_task': ScreenshotTask(str(tmp_path), str(out_path), 1280, 800),
            'temp_html': tmp_path
        })
    
    def _prepare_overall_map(self, df_sus: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Prepare overall map HTML file"""
        tmp_path, out_path = self._get_overall_paths()
        html = self._generate_overall_html(df_sus)
        self._save_overall_html(html, tmp_path)
        return self._create_overall_task(tmp_path, out_path)

    def _get_overall_paths(self):
        from ..utils import ensure_dir
        tmp_path = ensure_dir('temp_files') / 'api_overall.html'
        out_path = ensure_dir('figs') / 'mapa_clonagem_overall.png'
        return tmp_path, out_path

    def _generate_overall_html(self, df_sus: pd.DataFrame) -> str:
        return self.map_renderer.map_generator.generate_map_clonagem(
            df_sus, base_only=True
        )

    def _save_overall_html(self, html: str, tmp_path):
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(html)

    def _create_overall_task(self, tmp_path, out_path) -> Dict[str, Any]:
        return {
            'type': 'overall',
            'screenshot_task': ScreenshotTask(str(tmp_path), str(out_path), 1280, 800),
            'temp_html': tmp_path
        }
    
    def _prepare_trail_maps(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare trail map HTML files"""
        if not trails_tables:
            return []
        
        trail_tasks = []
        df = self._prepare_trail_dataframe(df_sus)
        self._process_trail_groups(df, df_sus, trails_tables, trail_tasks)
        return trail_tasks

    def _process_trail_groups(self, df: pd.DataFrame, df_sus: pd.DataFrame, trails_tables: Dict[str, Any], trail_tasks: List[Dict[str, Any]]):
        for day, _g in df.groupby(df['Data_ts'].dt.strftime('%d/%m/%Y'), sort=True):
            self._process_trail_day(day, df_sus, trails_tables, trail_tasks)

    def _prepare_trail_dataframe(self, df_sus: pd.DataFrame) -> pd.DataFrame:
        df = df_sus.copy()
        df['Data_ts'] = pd.to_datetime(df['Data_ts'], errors='coerce', utc=True)
        return df

    def _process_trail_day(self, day: str, df_sus: pd.DataFrame, trails_tables: Dict[str, Any], trail_tasks: List[Dict[str, Any]]):
        trails_tables_day = trails_tables.get(day, {})
        if not trails_tables_day:
            return
        
        for car_key in ['carro1', 'carro2']:
            self._process_trail_car(day, car_key, df_sus, trails_tables_day, trail_tasks)

    def _process_trail_car(self, day: str, car_key: str, df_sus: pd.DataFrame, trails_tables_day: Dict[str, Any], trail_tasks: List[Dict[str, Any]]):
        from ..utils import ensure_dir
        
        trail_html = self.trails_generator._build_map_html_for_car(
            df_sus, day, trails_tables_day, car_key
        )
        if trail_html:
            self._save_trail_html(day, car_key, trail_html, trail_tasks)

    def _save_trail_html(self, day: str, car_key: str, trail_html: str, trail_tasks: List[Dict[str, Any]]):
        safe_day = self._get_trail_safe_day(day)
        tmp_path, out_path = self._get_trail_paths(safe_day, car_key)
        self._write_trail_html(trail_html, tmp_path)
        self._add_trail_task(day, car_key, tmp_path, out_path, trail_tasks)

    def _get_trail_safe_day(self, day: str) -> str:
        return pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")

    def _get_trail_paths(self, safe_day: str, car_key: str):
        from ..utils import ensure_dir
        tmp_path = ensure_dir('temp_files') / f"api_trail_{safe_day}_{car_key}.html"
        out_path = ensure_dir('figs') / f"trilha_{safe_day}_{car_key}.png"
        return tmp_path, out_path

    def _write_trail_html(self, trail_html: str, tmp_path):
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(trail_html)

    def _add_trail_task(self, day: str, car_key: str, tmp_path, out_path, trail_tasks: List[Dict[str, Any]]):
        trail_tasks.append({
            'type': 'trail',
            'day': day,
            'car': car_key,
            'screenshot_task': ScreenshotTask(str(tmp_path), str(out_path), 1200, 800),
            'temp_html': tmp_path
        })
    
    def _process_results(self, html_tasks: List[Dict[str, Any]], 
                        result: Dict[str, Any]) -> Dict[str, Any]:
        """Process screenshot results into clean API response"""
        daily_figures = []
        overall_map = None
        trails_maps = {}
        
        if result['success']:
            self._process_successful_results(html_tasks, result, daily_figures, overall_map, trails_maps)
        
        self._cleanup_temp_files(html_tasks)
        return self._build_final_result(result, daily_figures, overall_map, trails_maps)

    def _process_successful_results(self, html_tasks: List[Dict[str, Any]], result: Dict[str, Any], 
                                   daily_figures: List[Dict[str, Any]], overall_map: Optional[str], 
                                   trails_maps: Dict[str, Any]):
        for i, task_result in enumerate(result['results']):
            if task_result['success']:
                self._process_single_result(html_tasks[i], task_result, daily_figures, overall_map, trails_maps)

    def _process_single_result(self, html_task: Dict[str, Any], task_result: Dict[str, Any], 
                              daily_figures: List[Dict[str, Any]], overall_map: Optional[str], 
                              trails_maps: Dict[str, Any]):
        task_type = html_task['type']
        
        if task_type == 'daily':
            daily_figures.append({
                'date': html_task['day'],
                'path': task_result['path']
            })
        elif task_type == 'overall':
            overall_map = task_result['path']
        elif task_type == 'trail':
            self._add_trail_result(html_task, task_result, trails_maps)

    def _add_trail_result(self, html_task: Dict[str, Any], task_result: Dict[str, Any], trails_maps: Dict[str, Any]):
        day = html_task['day']
        car = html_task['car']
        if day not in trails_maps:
            trails_maps[day] = {}
        trails_maps[day][car] = task_result['path']

    def _build_final_result(self, result: Dict[str, Any], daily_figures: List[Dict[str, Any]], 
                           overall_map: Optional[str], trails_maps: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'success': result['success'],
            'daily_figures': sorted(daily_figures, key=lambda x: x['date']),
            'overall_map': overall_map,
            'trails_maps': trails_maps,
            'processing_summary': result['summary']
        }
    
    def _cleanup_temp_files(self, html_tasks: List[Dict[str, Any]]) -> None:
        """Clean up temporary HTML files"""
        for task in html_tasks:
            try:
                task['temp_html'].unlink(missing_ok=True)
            except Exception:
                pass
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'success': True,
            'daily_figures': [],
            'overall_map': None,
            'trails_maps': {},
            'processing_summary': {
                'total_screenshots': 0,
                'successful': 0,
                'failed': 0,
                'total_time': 0.0,
                'avg_time_per_screenshot': 0.0
            }
        }
