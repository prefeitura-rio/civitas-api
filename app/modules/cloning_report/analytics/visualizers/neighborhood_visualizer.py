"""Neighborhood data visualization functionality"""

import matplotlib

matplotlib.use("Agg")  # use non-interactive backend (runs in worker threads)
import matplotlib.pyplot as plt
import pandas as pd
from app.modules.cloning_report.utils import ReportPaths


class NeighborhoodVisualizer:
    """Creates visualizations for neighborhood pair analysis"""

    @staticmethod
    def plot_bairro_pair_stats(df: pd.DataFrame, top_n: int = 12) -> str | None:
        """Create horizontal bar chart of top neighborhood pairs"""
        if df is None or df.empty:
            return None

        top_data = NeighborhoodVisualizer._prepare_chart_data(df, top_n)
        chart_path = NeighborhoodVisualizer._create_bar_chart(top_data)
        return chart_path

    @staticmethod
    def _prepare_chart_data(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
        """Prepare and reverse data for horizontal bar chart"""
        return df.head(int(top_n)).iloc[::-1]

    @staticmethod
    def _create_bar_chart(data: pd.DataFrame) -> str:
        """Create and save horizontal bar chart"""
        fig, ax = plt.subplots(figsize=(8, 5))
        NeighborhoodVisualizer._configure_chart(ax, data)
        return NeighborhoodVisualizer._save_chart(fig)

    @staticmethod
    def _configure_chart(ax, data: pd.DataFrame) -> None:
        """Configure chart appearance and labels"""
        labels = data["Bairro Origem"] + " → " + data["Bairro Destino"]
        ax.barh(labels, data["Contagem"])
        ax.set_xlabel("Contagem")
        ax.set_ylabel("Par de Bairros")
        ax.set_title("Pares de bairros mais frequentes (suspeitos)")
        plt.tight_layout()

    @staticmethod
    def _save_chart(fig) -> str:
        """Save chart to file and return path"""
        output_path = ReportPaths.analytics_path("bairro_pairs_top.png")
        fig.savefig(output_path, dpi=220)
        plt.close(fig)
        return str(output_path)
