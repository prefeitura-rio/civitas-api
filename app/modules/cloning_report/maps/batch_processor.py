"""Unified batch processing for all map types - MAXIMUM PERFORMANCE"""
import pandas as pd
import time
from typing import Dict, List, Optional, Any
from pathlib import Path

from ..utils import ensure_dir
from .generators import MapRenderer, TrailsMapGenerator
from .export import take_html_screenshots_batch, ScreenshotTask


class UnifiedMapBatchProcessor:
    """Processes ALL map types in a single parallel batch for maximum performance"""
    
    def __init__(self, enable_parallel: bool = True):
        self.enable_parallel = enable_parallel
        self.map_renderer = MapRenderer(enable_parallel=enable_parallel)
        self.trails_generator = TrailsMapGenerator()
    
    def process_all_maps(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any]) -> Dict[str, Any]:
        """Process ALL maps (daily, overall, trails) in one parallel batch"""
        if not self.enable_parallel:
            return self._process_sequential(df_sus, trails_tables)
        
        print("🚀 UNIFIED BATCH PROCESSOR: Processing all maps in parallel...")
        start_time = time.time()
        
        # Step 1: Generate all HTML content
        html_tasks = self._generate_all_html(df_sus, trails_tables)
        
        if not html_tasks:
            return {'daily_figures': [], 'overall_map': None, 'trails_maps': {}}
        
        # Step 2: Process all screenshots in one parallel batch
        screenshot_tasks = [task['screenshot_task'] for task in html_tasks]
        result = take_html_screenshots_batch(
            [task.html_path for task in screenshot_tasks],
            [task.png_path for task in screenshot_tasks],
            max_workers=None  # Auto-detect optimal workers
        )
        
        # Step 3: Process results
        output = self._process_batch_results(html_tasks, result)
        
        total_time = time.time() - start_time
        successful = sum(1 for r in result['results'] if r['success'])
        
        print(f"📊 UNIFIED BATCH PERFORMANCE:")
        print(f"   🎯 ALL map types processed together!")
        print(f"   ✅ Successful: {successful}/{len(screenshot_tasks)} screenshots")
        print(f"   ⏱️  Total time: {total_time:.2f}s")
        print(f"   ⚡ Avg per screenshot: {result['avg_time_per_screenshot']:.2f}s")
        print(f"   🔥 MAXIMUM EFFICIENCY ACHIEVED!")
        
        return output
    
    def _generate_all_html(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any]) -> List[Dict[str, Any]]:
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
    
    def _prepare_daily_maps(self, df_sus: pd.DataFrame) -> List[Dict[str, Any]]:
        """Prepare daily map HTML files"""
        if df_sus is None or df_sus.empty:
            return []
        
        df = df_sus.copy()
        df['Data_ts'] = pd.to_datetime(df['Data_ts'], errors='coerce', utc=True)
        
        daily_tasks = []
        for day, _g in df.groupby(df['Data_ts'].dt.strftime('%d/%m/%Y'), sort=True):
            day_data = df[df['Data_ts'].dt.strftime('%d/%m/%Y') == day]
            
            html_str = self.map_renderer.map_generator.generate_map_clonagem(day_data)
            safe_day = pd.to_datetime(day, dayfirst=True).strftime('%Y-%m-%d')
            
            tmp_path = ensure_dir('temp_files') / f"batch_daily_{safe_day}.html"
            out_path = ensure_dir('figs') / f"mapa_clonagem_{safe_day}.png"
            
            # Write HTML file
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(html_str)
            
            daily_tasks.append({
                'type': 'daily',
                'day': day,
                'screenshot_task': ScreenshotTask(str(tmp_path), str(out_path), 1280, 800),
                'temp_html': tmp_path
            })
        
        return daily_tasks
    
    def _prepare_overall_map(self, df_sus: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Prepare overall map HTML file"""
        if df_sus is None or df_sus.empty:
            return None
        
        tmp_path = ensure_dir('temp_files') / 'batch_overall.html'
        out_path = ensure_dir('figs') / 'mapa_clonagem_overall.png'
        
        html = self.map_renderer.map_generator.generate_map_clonagem(
            df_sus, base_only=True
        )
        
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return {
            'type': 'overall',
            'screenshot_task': ScreenshotTask(str(tmp_path), str(out_path), 1280, 800),
            'temp_html': tmp_path
        }
    
    def _prepare_trail_maps(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare trail map HTML files"""
        trail_tasks = []
        
        if df_sus is None or df_sus.empty or not trails_tables:
            return trail_tasks
        
        # Process each day's trails
        df = df_sus.copy()
        df['Data_ts'] = pd.to_datetime(df['Data_ts'], errors='coerce', utc=True)
        
        for day, _g in df.groupby(df['Data_ts'].dt.strftime('%d/%m/%Y'), sort=True):
            trails_tables_day = trails_tables.get(day, {})
            if not trails_tables_day:
                continue
            
            # Generate trail HTML for each car
            for car_key in ['carro1', 'carro2']:
                trail_html = self._generate_trail_html(df_sus, day, trails_tables_day, car_key)
                if trail_html:
                    safe_day = pd.to_datetime(day, dayfirst=True).strftime("%Y-%m-%d")
                    tmp_path = ensure_dir('temp_files') / f"batch_trail_{safe_day}_{car_key}.html"
                    out_path = ensure_dir('figs') / f"trilha_{safe_day}_{car_key}.png"
                    
                    # Write HTML file
                    with open(tmp_path, 'w', encoding='utf-8') as f:
                        f.write(trail_html)
                    
                    trail_tasks.append({
                        'type': 'trail',
                        'day': day,
                        'car': car_key,
                        'screenshot_task': ScreenshotTask(str(tmp_path), str(out_path), 1200, 800),
                        'temp_html': tmp_path
                    })
        
        return trail_tasks
    
    def _generate_trail_html(self, df_sus: pd.DataFrame, day: str, trails_tables_day: Dict[str, Any], car_key: str) -> Optional[str]:
        """Generate HTML for a specific trail map"""
        return self.trails_generator._build_map_html_for_car(df_sus, day, trails_tables_day, car_key)
    
    def _process_batch_results(self, html_tasks: List[Dict[str, Any]], 
                             result: Dict[str, Any]) -> Dict[str, Any]:
        """Process batch screenshot results"""
        daily_figures = []
        overall_map = None
        trails_maps = {}
        
        # Map results back to original tasks
        for i, task_result in enumerate(result['results']):
            if task_result['success']:
                html_task = html_tasks[i]
                task_type = html_task['type']
                
                if task_type == 'daily':
                    daily_figures.append({
                        'date': html_task['day'],
                        'path': task_result['task'].png_path
                    })
                elif task_type == 'overall':
                    overall_map = task_result['task'].png_path
                elif task_type == 'trail':
                    day = html_task['day']
                    car = html_task['car']
                    if day not in trails_maps:
                        trails_maps[day] = {}
                    trails_maps[day][car] = task_result['task'].png_path
        
        # Cleanup temp HTML files
        self._cleanup_temp_files(html_tasks)
        
        return {
            'daily_figures': sorted(daily_figures, key=lambda x: x['date']),
            'overall_map': overall_map,
            'trails_maps': trails_maps
        }
    
    def _cleanup_temp_files(self, html_tasks: List[Dict[str, Any]]) -> None:
        """Clean up temporary HTML files"""
        for task in html_tasks:
            try:
                task['temp_html'].unlink(missing_ok=True)
            except Exception:
                pass
    
    def _process_sequential(self, df_sus: pd.DataFrame, trails_tables: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to sequential processing"""
        print("📝 Using sequential processing...")
        
        # Use original methods
        daily_figures = self.map_renderer.render_daily_figures(df_sus)
        overall_map = self.map_renderer.render_overall_map_png(df_sus)
        
        # Generate trails maps
        trails_maps = {}
        if df_sus is not None and not df_sus.empty and trails_tables:
            df = df_sus.copy()
            df['Data_ts'] = pd.to_datetime(df['Data_ts'], errors='coerce', utc=True)
            
            for day, _g in df.groupby(df['Data_ts'].dt.strftime('%d/%m/%Y'), sort=True):
                trails_tables_day = trails_tables.get(day, {})
                if trails_tables_day:
                    trails_maps[day] = self.trails_generator.generate_trails_map(df_sus, day, trails_tables_day)
        
        return {
            'daily_figures': daily_figures,
            'overall_map': overall_map,
            'trails_maps': trails_maps
        }