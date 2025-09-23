"""Map rendering utilities with parallel processing support"""
import multiprocessing
import pandas as pd
import os
import time
from typing import List, Dict, Optional
from pathlib import Path

from ...utils import VMAX_KMH, ensure_dir
from .map_generator import MapGenerator
from ..export.screenshot import take_html_screenshot, take_html_screenshots_batch, ScreenshotTask


class MapRenderer:
    """High-performance map renderer with parallel screenshot processing by default"""
    
    def __init__(self, use_clusters: bool = True, vmax_kmh: float = VMAX_KMH, 
                enable_parallel: bool = True, max_workers: Optional[int] = None):
        self.map_generator = MapGenerator(use_clusters, vmax_kmh)
        self.enable_parallel = enable_parallel
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 8)
    
    def render_overall_map_png(self, df_sus: pd.DataFrame) -> Optional[str]:
        """Render overall map as PNG"""
        if df_sus is None or df_sus.empty:
            return None
        
        tmp = ensure_dir('temp_files') / 'mapa_clonagem_overall.html'
        out = ensure_dir('figs') / 'mapa_clonagem_overall.png'
        
        html = self.map_generator.generate_map_clonagem(
            df_sus, base_only=True
        )
        
        return self._save_html_to_png(html, tmp, out)
    
    def render_daily_figures(self, df_sus: pd.DataFrame) -> List[Dict[str, str]]:
        """Render daily figures - optimized with parallel processing"""
        if df_sus is None or df_sus.empty:
            return []
        
        df = df_sus.copy()
        df['Data_ts'] = pd.to_datetime(df['Data_ts'], errors='coerce', utc=True)
        
        daily_data = []
        for day, _g in df.groupby(df['Data_ts'].dt.strftime('%d/%m/%Y'), sort=True):
            day_data = df[df['Data_ts'].dt.strftime('%d/%m/%Y') == day]
            daily_data.append((day, day_data))
        
        if not self.enable_parallel:
            return self._render_daily_sequential(daily_data)
        else:
            return self._render_daily_parallel(daily_data)
    
    def _render_daily_sequential(self, daily_data: List[tuple]) -> List[Dict[str, str]]:
        """Sequential daily rendering (original method)"""
        figs = []
        
        for day, day_data in daily_data:
            html_str = self.map_generator.generate_map_clonagem(day_data)
            safe_day = pd.to_datetime(day, dayfirst=True).strftime('%Y-%m-%d')
            tmp = ensure_dir('temp_files') / f"mapa_clonagem_{safe_day}.html"
            out = ensure_dir('figs') / f"mapa_clonagem_{safe_day}.png"
            
            result = self._save_html_to_png(html_str, tmp, out)
            if result:
                figs.append({'date': day, 'path': result})
        
        return figs
    
    def _render_daily_parallel(self, daily_data: List[tuple]) -> List[Dict[str, str]]:
        """Parallel daily rendering - HIGH PERFORMANCE"""
        html_files = []
        png_files = []
        day_mapping = {}
        
        for day, day_data in daily_data:
            html_str = self.map_generator.generate_map_clonagem(day_data)
            safe_day = pd.to_datetime(day, dayfirst=True).strftime('%Y-%m-%d')
            
            tmp_path = ensure_dir('temp_files') / f"mapa_clonagem_{safe_day}.html"
            out_path = ensure_dir('figs') / f"mapa_clonagem_{safe_day}.png"

            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(html_str)
            
            html_files.append(str(tmp_path))
            png_files.append(str(out_path))
            day_mapping[str(out_path)] = day
        

        try:
            result = take_html_screenshots_batch(
                html_files, png_files, 
                width=1280, height=800,
                max_workers=self.max_workers  
            )

            figs = []
            successful_pngs = set()
            
            for task_result in result['results']:
                if task_result['success']:
                    png_path = task_result['task'].png_path
                    successful_pngs.add(png_path)
                    day = day_mapping[png_path]
                    figs.append({'date': day, 'path': png_path})
                else:
                    print(f"[WARN] Screenshot failed: {task_result['message']}")
            
            
            return sorted(figs, key=lambda x: x['date'])
            
        finally:
            for html_file in html_files:
                try:
                    os.remove(html_file)
                except Exception:
                    pass
    
    def _save_html_to_png(self, html: str, tmp_path: Path, out_path: Path) -> Optional[str]:
        """Save HTML as PNG (single file)"""
        with open(tmp_path, 'w', encoding='utf-8') as f:
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
