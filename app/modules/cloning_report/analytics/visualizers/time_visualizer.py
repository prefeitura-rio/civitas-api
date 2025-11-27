"""Time-based data visualization functionality"""

import pandas as pd
import matplotlib.pyplot as plt
from app.modules.cloning_report.utils import ensure_dir
from app.modules.cloning_report.utils.filesystem import FileSystemService


class TimeVisualizer:
    """Creates visualizations for temporal analysis"""

    @staticmethod
    def plot_hourly_histogram(df: pd.DataFrame) -> str | None:
        """Create bar chart of counts by hour"""
        if df is None or df.empty:
            return None

        chart_path = TimeVisualizer._create_hourly_chart(df)
        return chart_path

    @staticmethod
    def _create_hourly_chart(df: pd.DataFrame) -> str:
        """Create and save hourly bar chart"""
        fig, ax = plt.subplots(figsize=(8, 4))
        TimeVisualizer._configure_hourly_chart(ax, df)
        return TimeVisualizer._save_chart(fig)

    @staticmethod
    def _configure_hourly_chart(ax, df: pd.DataFrame) -> None:
        """Configure hourly chart appearance and labels"""
        ax.bar(df["Hora"], df["Contagem"])
        ax.set_xlabel("Hora do dia")
        ax.set_ylabel("Registros suspeitos")
        ax.set_title("Distribuição horária de suspeitas")
        ax.set_xticks(range(0, 24, 2))
        plt.tight_layout()

    @staticmethod
    def _save_chart(fig) -> str:
        """Save chart to file and return path"""
        filename = FileSystemService.build_unique_filename("hour_profile.png")
        output_path = ensure_dir("app/assets/cloning_report/figs") / filename
        fig.savefig(output_path, dpi=220)
        plt.close(fig)
        return str(output_path)
