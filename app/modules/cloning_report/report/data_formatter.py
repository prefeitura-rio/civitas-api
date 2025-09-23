"""Data formatting and processing for PDF content."""

from typing import Dict
import pandas as pd


class DataFormatter:
    """Handles data formatting and processing for PDF content."""
    
    @staticmethod
    def format_text_replacements(text: str, replacements: Dict[str, str]) -> str:
        """Apply text replacements"""
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @staticmethod
    def prepare_table_data(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare table data with text formatting"""
        df = df.copy()
        replacements = {
            'AVENIDA': 'AV.', 'ESTRADA': 'ESTR.', 'NOSSA SENHORA': 'N. S.ª',
            'VIA EXPRESSA': 'V. EXPR.', 'PRESIDENTE': 'PRES.'
        }
        return df.map(lambda x: DataFormatter.format_text_replacements(x, replacements) 
                     if isinstance(x, str) else x)

    @staticmethod
    def identify_table_type(df: pd.DataFrame) -> str:
        """Identify table type (clonagem, trilha, or generic)"""
        is_clonagem_table = all(c in df.columns for c in ['Km', 'Km/h'])
        is_trilha_table = all(c in df.columns for c in ['DataHora', 'Local', 'Bairro'])
        
        if is_clonagem_table:
            return 'clonagem'
        elif is_trilha_table:
            return 'trilha'
        else:
            return 'generic'

    @staticmethod
    def process_clonagem_data(df: pd.DataFrame) -> pd.DataFrame:
        """Process clonagem table data"""
        df = df.copy()
        df['Km'] = pd.to_numeric(df['Km'], errors='coerce').round().astype('Int64')
        df['Km/h'] = pd.to_numeric(df['Km/h'], errors='coerce').round().astype('Int64')
        df = DataFormatter._process_clonagem_table(df)

        for col in ('Primeira Detecção', 'Detecção Seguinte'):
            if col in df.columns:
                df[col] = df[col].apply(DataFormatter.format_local_with_radar)
        
        return df

    @staticmethod
    def process_trilha_data(df: pd.DataFrame) -> pd.DataFrame:
        """Process trilha table data"""
        df = df.copy()
        if 'Sentido' in df.columns:
            df = df.drop(columns=['Sentido'])
        
        if 'Local' in df.columns:
            df['Local'] = df['Local'].apply(DataFormatter.format_local_with_radar)
        
        return df

    @staticmethod
    def _process_clonagem_table(df: pd.DataFrame) -> pd.DataFrame:
        """Process clonagem table structure"""
        df = df.copy()
        df = df.rename(columns={
            'Origem': 'Primeira Detecção',
            'Destino': 'Detecção Seguinte'
        })
        df.drop(['Km', 's'], axis=1, inplace=True, errors='ignore')
        
        if 'Latitude' in df.columns:
            df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce').round(6)
        if 'Longitude' in df.columns:
            df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce').round(6)

        final_cols = [
            'Data', 'Primeira Detecção', 'Detecção Seguinte',
            'Latitude', 'Longitude', 'Km/h'
        ]
        df = df[[c for c in final_cols if c in df.columns]]
        return df

    @staticmethod
    def format_local_with_radar(text: str) -> str:
        """Convert 'AV. ATLANTICA (703 - 1)' -> 'AV. ATLANTICA\nRadar: 703 - 1'"""
        if not isinstance(text, str):
            return "" if pd.isna(text) else str(text)
        if ' (' in text and text.endswith(')'):
            base, inside = text.rsplit(' (', 1)
            inside = inside[:-1]
            return f"{base}\nRadar: {inside}"
        return text

    @staticmethod
    def get_header_mapping() -> Dict[str, str]:
        """Get column header mapping"""
        return {
            'Data': 'Data',
            'Primeira Detecção': 'Primeira Detecção',
            'Detecção Seguinte': 'Detecção Seguinte',
            'Km/h': 'Km/h',
            'Logradouro': 'Localização do Radar',
            'DataHora': 'Data/Hora',
            'Local': 'Local',
            'Bairro': 'Bairro',
            'Sentido': 'Sentido',
            'Latitude': 'Latitude',
            'Longitude': 'Longitude',
        }