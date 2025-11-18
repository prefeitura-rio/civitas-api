from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from typing import Any

import pandas as pd
from fpdf.enums import XPos, YPos
from app.modules.cloning_report.detection.preprocessing import DetectionPreprocessor
from app.modules.cloning_report.detection.pipeline import DetectionPipeline
from app.modules.cloning_report.analytics import (
    compute_clonagem_kpis,
    compute_bairro_pair_stats,
    plot_bairro_pair_stats,
)
from app.modules.cloning_report.maps import render_overall_map_png, generate_trails_map
from app.modules.cloning_report.report import ReportPDF
from app.modules.cloning_report.report.font_config import FontSize
from app.modules.cloning_report.utils import strftime_safe
from app.modules.cloning_report.utils.archive import create_report_temp_dir


# =========================================================
# GERADOR - estrutura com KPIs de clonagem
# =========================================================
class ClonagemReportGenerator:
    DATETIME_DISPLAY_FORMAT = "%d/%m/%Y %H:%M:%S"

    def __init__(
        self,
        df: pd.DataFrame,
        placa: str,
        periodo_inicio: pd.Timestamp,
        periodo_fim: pd.Timestamp,
        report_id: str = None,
    ):
        self.report_id = report_id or self._generate_unique_report_id()
        self._initialize_parameters(df, placa, periodo_inicio, periodo_fim)
        self._initialize_attributes()
        self._setup()

    # ---------- geração ----------
    def generate(self, output_path: str | Path | None = None):
        if output_path is None:
            base_dir = create_report_temp_dir(self.report_id)
            file_name = (
                f"relatorio_clonagem_{self.placa}_"
                f"{self.periodo_inicio.strftime('%Y%m%d')}_"
                f"{self.periodo_fim.strftime('%Y%m%d')}.pdf"
            )
            output_path = base_dir / file_name
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf = self._create_pdf()
        self._add_all_pages(pdf)
        pdf.output(str(output_path))
        return output_path

    def _generate_unique_report_id(self):
        """Generate unique report ID"""
        import random
        from datetime import datetime

        now = datetime.now()
        return f"{now.strftime('%Y%m%d.%H%M%S')}{random.randint(0, 999):03d}"

    def _initialize_parameters(
        self,
        df: pd.DataFrame,
        placa: str,
        periodo_inicio: pd.Timestamp,
        periodo_fim: pd.Timestamp,
    ):
        self.df_raw = df
        self.placa = placa
        self.periodo_inicio = periodo_inicio
        self.periodo_fim = periodo_fim

    def _initialize_attributes(self):
        self.df = pd.DataFrame()
        self.results: dict[str, Any] = {}

    # ---------- preparação ----------
    def _setup(self):
        self._prepare_dataframe()
        self._set_metadata()
        self._run_analysis()
        self._extract_kpis()

    def _prepare_dataframe(self):
        dfx = DetectionPreprocessor.prepare_dataframe(self.df_raw.copy())
        self.df = dfx[
            (dfx["datahora"] >= self.periodo_inicio)
            & (dfx["datahora"] <= self.periodo_fim)
        ].copy()
        self.total_deteccoes = int(len(self.df))

    def _set_metadata(self):
        self.meta_marca_modelo = (
            (str(self.df["marca"].iloc[0]) + "/" + str(self.df["modelo"].iloc[0]))
            if {"marca", "modelo"}.issubset(self.df.columns)
            and not self.df[["marca", "modelo"]].isna().any().any()
            else "CHEV/TRACKER 12T A PR"  # mock do exemplo
        )
        self.meta_cor = (
            str(self.df["cor"].iloc[0]).upper()
            if "cor" in self.df.columns and pd.notna(self.df["cor"].iloc[0])
            else "PRETA"  # mock do exemplo
        )
        self.meta_ano_modelo = (
            int(self.df["ano_modelo"].iloc[0])
            if "ano_modelo" in self.df.columns
            and pd.notna(self.df["ano_modelo"].iloc[0])
            else 2021  # mock do exemplo
        )

    def _run_analysis(self):
        self.results = DetectionPipeline.detect_cloning(self.df, plot=True)

    def _extract_kpis(self):
        k = compute_clonagem_kpis(self.results)
        self._assign_kpi_values(k)
        self.bairro_pairs_df = compute_bairro_pair_stats(self.results)
        self.bairro_pairs_png = plot_bairro_pair_stats(self.bairro_pairs_df, top_n=12)

    def _assign_kpi_values(self, k):
        self._assign_basic_kpis(k)
        self._assign_advanced_kpis(k)

    def _assign_basic_kpis(self, k):
        self.num_suspeitos = k["num_suspeitos"]
        self.max_vel = k["max_vel"]
        self.dia_mais_sus = k["dia_mais_sus"]
        self.sus_dia_mais_sus = k["sus_dia_mais_sus"]

    def _assign_advanced_kpis(self, k):
        self._assign_turn_kpis(k)
        self._assign_place_kpis(k)
        self._assign_pair_kpis(k)

    def _assign_turn_kpis(self, k):
        self.turno_mais_sus = k["turno_mais_sus"]
        self.turno_mais_sus_count = k["turno_mais_sus_count"]

    def _assign_place_kpis(self, k):
        self.place_lider = k["place_lider"]
        self.place_lider_count = k["place_lider_count"]

    def _assign_pair_kpis(self, k):
        self.top_pair_str = k["top_pair_str"]
        self.top_pair_count = k["top_pair_count"]

    # =====================================================
    # Páginas
    # =====================================================
    def _add_instructions_page(self, pdf):
        self._add_title_section(pdf)
        self._add_objective_section(pdf)
        self._add_methodology_section(pdf)
        self._add_structure_section(pdf)
        self._add_limitations_section(pdf)

    def _add_title_section(self, pdf):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", FontSize.MAIN_TITLE)
        pdf.cell(
            0,
            10,
            "Relatório de Suspeita de Clonagem de Placa",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="C",
        )
        pdf.ln(5)

    def _add_objective_section(self, pdf):
        self._add_objective_title(pdf)
        self._add_objective_content(pdf)

    def _add_objective_title(self, pdf):
        pdf.set_font("Helvetica", "B", FontSize.SECTION_TITLE)
        pdf.cell(0, 10, "1. Objetivo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)

    def _add_objective_content(self, pdf):
        pdf.chapter_body(
            "    Este relatório tem como objetivo identificar e analisar indícios de possível clonagem "
            "de placas de veículos a partir dos registros de passagem capturados pelos radares da "
            "cidade. O foco está na detecção de pares suspeitos, ou seja, situações em que a mesma "
            "placa é registrada em pontos distintos em um intervalo de tempo que tornaria inviável um "
            "deslocamento compatível com a realidade urbana.\n\n"
            "    Quando os dados atendem aos critérios mínimos necessários, busca-se também "
            "reconstruir possíveis trilhas de movimentação dos dois veículos distintos (denominados "
            "Veículo 1 e Veículo 2), fornecendo uma visualização dos pontos de detecção possivelmente "
            "atribuíveis a cada um, dos dias em que ocorreram as ocorrências suspeitas e da localização "
            "exata de cada registro.\n\n"
            "    O objetivo final é sinalizar visual e analiticamente a suspeita de clonagem, de forma "
            "a apoiar a identificação de veículos potencialmente clonados e subsidiar análises ou "
            "investigações complementares."
        )
        pdf.ln(2)

    def _add_methodology_section(self, pdf):
        self._add_methodology_title(pdf)
        self._add_methodology_content(pdf)

    def _add_methodology_content(self, pdf):
        self._add_data_section(pdf)
        self._add_analysis_criteria_section(pdf)
        self._add_suspicious_pairs_section(pdf)
        self._add_general_map_methodology_section(pdf)
        self._add_daily_maps_methodology_section(pdf)

    def _add_methodology_title(self, pdf):
        pdf.set_font("Helvetica", "B", FontSize.SECTION_TITLE)
        pdf.cell(0, 10, "2. Metodologia", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)

    def _add_data_section(self, pdf):
        pdf.chapter_body("2.1 Dados utilizados neste relatório:")
        pdf.chapter_body(
            "- Registros de leitura de OCR de placas dos radares da cidade do Rio de Janeiro. Estas "
            "informações contêm placa, data, hora, latitude e longitude da detecção em um radar."
        )
        pdf.ln(1)

    def _add_analysis_criteria_section(self, pdf):
        pdf.chapter_body(
            "2.2 Critério de análise para identificação da suspeita de clone:"
        )
        pdf.chapter_body(
            "    Para identificar uma suspeita de clonagem, primeiro calcula-se a distância em linha "
            "reta entre duas detecções consecutivas, utilizando a fórmula de Haversine. Em seguida, é "
            "realizado o cálculo de intervalo de tempo entre essas detecções para identificar o tempo "
            "entre duas detecções consecutivas. A partir disso, estima-se a velocidade média necessária "
            "para que o veículo percorresse a distância no tempo registrado.\n\n"
            "    Quando a velocidade calculada ultrapassa os limites razoáveis de deslocamento em "
            "uma área urbana, o par de detecções consecutivas é classificado como suspeito. Por outro "
            "lado, quando o par de detecções consecutivas apresenta uma velocidade média "
            "considerada razoável, não há alerta de suspeita de clonagem e o par de detecções é "
            "considerado compatível com os padrões de deslocamento urbano."
        )
        pdf.ln(1)

    def _add_suspicious_pairs_section(self, pdf):
        pdf.chapter_body("2.3 Par de Detecções Suspeitas")
        pdf.chapter_body(
            "    Um par de detecção corresponde a duas passagens consecutivas de um mesmo "
            "veículo registradas pelos radares da cidade, contendo informações de placa, data, hora e "
            "localização (latitude/longitude). Esse par é considerado suspeito quando, ao calcular a "
            "distância em linha reta entre os dois pontos de detecção e dividir pelo intervalo de tempo "
            "registrado, obtém-se uma velocidade média implícita incompatível com um deslocamento "
            "real em área urbana.\n\n"
            "    Assim, o par de detecção suspeita é a unidade básica de análise do relatório, "
            "servindo como indício de que podem existir dois veículos distintos circulando com a mesma "
            "placa em locais diferentes no mesmo intervalo de tempo."
        )
        pdf.ln(1)

    def _add_general_map_methodology_section(self, pdf):
        pdf.chapter_body("2.4 Metodologia do mapa Geral da análise")
        pdf.chapter_body(
            "    Indica todos os pares de detecções classificadas como suspeita no período "
            "analisado."
        )
        pdf.ln(1)

    def _add_daily_maps_methodology_section(self, pdf):
        self._add_daily_maps_intro(pdf)
        self._add_separation_methods(pdf)
        self._add_separation_conditions(pdf)
        self._add_separation_criteria(pdf)

    def _add_daily_maps_intro(self, pdf):
        pdf.chapter_body("2.4 Metodologia da Separação em trilhas nos Mapas Diários")
        pdf.chapter_body(
            "    Os mapas diários apresentam os pares de detecção suspeita identificados em cada "
            "dia do período analisado. Isso significa que, ainda que existam outras detecções do veículo "
            "ao longo dia, elas apenas aparecem no mapa se for constatada no seu par a suspeita de "
            "clonagem.\n\n"
            "    A partir da identificação de pares com suspeita de clonagem, busca-se separar os "
            "registros em duas possíveis trilhas de movimentação (denominadas Veículo 1 e Veículo "
            "2), de modo a representar graficamente trajetos alternativos que reforçam a suspeita de "
            "clonagem. Isto é feito a partir da separação em trilhas a partir de duas metodologias, "
            "descritas a seguir."
        )
        pdf.ln(1)

    def _add_separation_methods(self, pdf):
        self._add_separation_methods_intro(pdf)
        self._add_temporal_method(pdf)
        self._add_geographic_method(pdf)

    def _add_separation_methods_intro(self, pdf):
        pdf.chapter_body(
            "2.4.1 Para a separação em trilhas, são empregadas duas metodologias:"
        )
        pdf.chapter_body("São aplicados dois métodos principais:")

    def _add_temporal_method(self, pdf):
        pdf.chapter_body(
            "1. Método Temporal: baseado no tempo, os registros de detecção são analisados em "
            "ordem cronológica. Quando a inclusão de um ponto de detecção em determinada "
            "trilha gera um deslocamento considerado inviável, esse ponto de detecção é "
            "atribuído ao outro veículo."
        )
        pdf.ln(1)

    def _add_geographic_method(self, pdf):
        pdf.chapter_body(
            "2. Método Geográfico: baseado na localização: os registros são agrupados de acordo "
            "com a proximidade geográfica. Em seguida, são realizados ajustes para evitar que "
            "origem e destino de um mesmo par fiquem no mesmo grupo."
        )
        pdf.ln(1)

    def _add_separation_conditions(self, pdf):
        self._add_separation_conditions_title(pdf)
        self._add_separation_conditions_content(pdf)
        self._add_separation_conditions_conclusion(pdf)

    def _add_separation_conditions_title(self, pdf):
        pdf.chapter_body("2.4.2 Condições para aplicação da separação")

    def _add_separation_conditions_content(self, pdf):
        pdf.chapter_body(
            "- Em dias com apenas um par de detecções, a separação é automática: um ponto é "
            "atribuído ao Veículo 1 e o outro ao Veículo 2."
        )
        pdf.chapter_body(
            "- Em dias com múltiplos pares, a separação somente é realizada quando há ao menos "
            "04 pares de registros com suspeitas de clone e todas as distâncias entre radares "
            "envolvidos superam 2 km. Esse critério evita segmentações artificiais em trajetos "
            "muito curtos ou pouco representativos."
        )
        pdf.chapter_body(
            "- Em situações com dados insuficientes ou inconsistentes para reconstrução de "
            "trajetos confiáveis, a separação não é realizada."
        )
        pdf.ln(1)

    def _add_separation_conditions_conclusion(self, pdf):
        pdf.chapter_body(
            "    Quando os dados permitem separar os registros em duas trilhas consistentes, isso "
            "sugere a presença de dois veículos distintos usando a mesma placa. Quando não é possível "
            "estabelecer duas trilhas coerentes, os registros permanecem em cinza, sinalizando suspeita "
            "que requer investigação adicional."
        )
        pdf.ln(1)

    def _add_separation_criteria(self, pdf):
        self._add_method_choice_criteria(pdf)
        self._add_separation_limitations(pdf)

    def _add_method_choice_criteria(self, pdf):
        pdf.chapter_body(
            "2.4.3 Critério de escolha entre o método temporal e o método geográfico"
        )
        pdf.chapter_body(
            "    Quando a separação é possível, ambos os métodos (temporal e espacial) são "
            "testados, e adota-se aquele que não gere inconsistências, como a ocorrência de origem e "
            "destino de um mesmo par sendo atribuídos ao mesmo veículo."
        )
        pdf.ln(1)

    def _add_separation_limitations(self, pdf):
        self._add_separation_limitations_title(pdf)
        self._add_separation_limitations_content(pdf)

    def _add_separation_limitations_title(self, pdf):
        pdf.chapter_body("2.4.4 Limitações da separação de veículos em trilhas")

    def _add_separation_limitations_content(self, pdf):
        pdf.chapter_body(
            "- Os métodos são aproximações baseadas em regras práticas, não garantindo acerto "
            "total."
        )
        pdf.chapter_body(
            "- Podem ser impactados por erros de horário, coordenadas ou falhas de OCR dos "
            "radares."
        )
        pdf.chapter_body(
            "- O limite de 2 km é um parâmetro de segurança para evitar separações artificiais, "
            "mas pode ser ajustado conforme o contexto urbano."
        )
        pdf.ln(2)

    def _add_structure_section(self, pdf):
        # Verificar se há espaço suficiente para o título + conteúdo
        # Se não houver, forçar nova página
        if pdf.get_y() > 250:  # Se estiver muito próximo do final da página
            pdf.add_page()

        self._add_structure_title(pdf)
        self._add_structure_intro(pdf)
        self._add_structure_content(pdf)

    def _add_structure_content(self, pdf):
        pdf.chapter_body(
            "Este relatório busca apresentar análises de suspeita de clonagem de placas de \n"
            "veículos, a partir dos registros de passagem capturados pelos radares da cidade. \n"
            "Especificamente, pretende-se separar as detecções suspeitas em diferentes trilhas \n"
            "atribuíveis a dois veículos distintos (Veículo 1 e Veículo 2), com foco em evidenciar e \n"
            "caracterizar as possíveis dinâmicas de circulação de cada um deles paralelamente na \n"
            "cidade. O processo é dividido em quatro etapas: \n\n"
            "        <b>1. Recebimento da demanda</b>\n"
            "        Autoridade solicitante fornece a placa de veículo e período de busca para identificação de possíveis suspeitas de clonagem\n"
            "        <b>2. Identificação de suspeita de clonagem</b>\n"
            "        Mapeamento de pares de detecções (duas passagens consecutivas) que apontem suspeita de clone no período\n"
            "        <b>3. Geração de Mapa Geral da Análise</b>\n"
            "        Consolidação de todos os pares de detecções classificados como suspeitos ao longo do período analisado. \n\n"
            "        <b>4. Geração de Mapas Diários: separação em trilhas</b>\n"
            "        Identificação de pontos de detecções atribuíveis a possíveis veículos distintos (Veículo 1 e Veículo 2) diariamente."
            ""
        )
        # self._add_analysis_parameters_section(pdf)
        # self._add_summary_section(pdf)
        # self._add_reading_guide_section(pdf)
        # self._add_general_analysis_section(pdf)
        # self._add_daily_analysis_section(pdf)
        pass

    def _add_structure_title(self, pdf):
        pdf.set_font("Helvetica", "B", FontSize.SECTION_TITLE)
        pdf.cell(0, 8, "3. Estrutura do Relatório", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(0.5)
        pdf.set_font("Helvetica", "", FontSize.BODY_TEXT_LARGE)

    def _add_structure_intro(self, pdf):
        pdf.chapter_body("    O relatório está organizado da seguinte forma:")
        pdf.ln(0.5)

    def _add_analysis_parameters_section(self, pdf):
        pdf.chapter_body("3.1 Parâmetros da Análise")
        pdf.chapter_body(
            "    Tabela com as informações de referência da análise, incluindo:\n"
            "     - Placa consultada\n"
            "     - Data de início e data de fim do período analisado"
        )
        pdf.ln(1)

    def _add_summary_section(self, pdf):
        pdf.chapter_body("3.2 Quadro Resumo Inicial")
        pdf.chapter_body(
            "    Panorama geral da análise, reunindo os principais indicadores:\n"
            "     - Número total de passagens analisadas.\n"
            "     - Quantidade de pares classificados como suspeitos.\n"
            "     - Dia com mais registros de suspeita de clonagem"
        )
        pdf.ln(1)

    def _add_reading_guide_section(self, pdf):
        pdf.chapter_body("3.3 Introdução: como ler este relatório")
        pdf.chapter_body(
            "    Seção que tem como finalidade orientar a interpretação das informações "
            "apresentadas."
        )
        pdf.ln(1)

    def _add_general_analysis_section(self, pdf):
        pdf.chapter_body("3.4 Mapa e Tabela Geral da Análise")
        pdf.chapter_body(
            "     Representação consolidada de todas as ocorrências suspeitas identificadas ao longo "
            "do período. Permite observar a distribuição espacial dos registros e identificar "
            "concentrações de ocorrências em determinadas regiões da cidade."
        )
        pdf.ln(1)

    def _add_daily_analysis_section(self, pdf):
        pdf.chapter_body("3.5 Mapas e Tabelas Diários")
        pdf.chapter_body(
            "    Detalham, dia a dia, os pares de detecção suspeitos. Quando há condições mínimas "
            "para reconstrução de duas trilhas distintas (Veículo 1 e Veículo 2), os pontos são "
            "representados em cores diferentes (azul escuro e azul claro), evidenciando os trajetos "
            "alternativos. Quando a separação não é possível, os registros aparecem em cinza, indicando "
            "ausência de evidências suficientes para segmentar as trilhas."
        )
        pdf.ln(2)

    def _add_limitations_section(self, pdf):
        self._add_limitations_title(pdf)
        self._add_limitations_content(pdf)

    def _add_limitations_title(self, pdf):
        pdf.set_font("Helvetica", "B", FontSize.SECTION_TITLE)
        pdf.cell(0, 10, "4. Limitações da análise", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", FontSize.BODY_TEXT_LARGE)

    def _add_limitations_content(self, pdf):
        self._add_detection_limitations(pdf)
        self._add_technical_limitations(pdf)
        self._add_data_limitations(pdf)

    def _add_detection_limitations(self, pdf):
        pdf.chapter_body(
            "- A ausência de detecção não implica ausência de passagem (falhas de OCR, "
            "obstruções, manutenção ou indisponibilidade do equipamento)."
        )
        pdf.chapter_body(
            '- Falhas de OCR (ex.: confusão entre caracteres como "O/0" ou "B/8").'
        )
        pdf.chapter_body("- Erro de sincronização de relógio entre equipamentos.")

    def _add_technical_limitations(self, pdf):
        pdf.chapter_body(
            "- Distâncias são calculadas em linha reta - não correspondem ao trajeto real percorrido."
        )
        pdf.chapter_body(
            "- Parâmetros fixos de velocidade podem não contemplar situações excepcionais (ex.: deslocamentos de emergência)."
        )

    def _add_data_limitations(self, pdf):
        pdf.chapter_body(
            "- Dependência da qualidade e integridade dos dados capturados pelos radares, sujeitos a variações técnicas ou climáticas."
        )
        pdf.chapter_body(
            "- Histórico de dados disponível apenas a partir de 01/06/2024."
        )
        pdf.ln(2)

    def _add_summary_page(self, pdf: ReportPDF):
        self._add_parameters_section(pdf)
        self._add_kpi_section(pdf)

    def _add_parameters_section(self, pdf: ReportPDF):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", FontSize.PARAMETERS_SECTION_TITLE)
        pdf.cell(
            0, 10, "Parâmetros de Busca", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
        )
        pdf.ln(4)
        self._add_parameters_table(pdf)

    def _add_parameters_table(self, pdf: ReportPDF):
        periodo_txt = (
            f"De {self.periodo_inicio:%d/%m/%Y às %H:%M:%S} "
            f"até {self.periodo_fim:%d/%m/%Y às %H:%M:%S}"
        )
        suspeita_txt = "Sim" if getattr(self, "num_suspeitos", 0) > 0 else "Não"
        rows = [
            ("Placa monitorada:", self.placa),
            ("Marca/Modelo:", self.meta_marca_modelo),
            ("Cor:", self.meta_cor),
            ("Ano Modelo:", str(self.meta_ano_modelo)),
            ("Período analisado:", periodo_txt),
            ("Total de pontos detectados:", str(self.total_deteccoes)),
            ("Suspeita de placa clonada:", suspeita_txt),
        ]
        pdf.add_params_table(rows)

    def _add_kpi_section(self, pdf: ReportPDF):
        pdf.set_font("Helvetica", "B", FontSize.KPI_SECTION_TITLE)
        pdf.cell(0, 10, "Quadro Resumo", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
        pdf.ln(6)
        self._add_kpi_boxes(pdf)

    def _add_kpi_boxes(self, pdf: ReportPDF):
        self._setup_kpi_layout(pdf)
        self._add_kpi_boxes_content(pdf)

    def _setup_kpi_layout(self, pdf: ReportPDF):
        self._calculate_kpi_dimensions(pdf)
        self._calculate_kpi_positions(pdf)
        self._store_kpi_layout()

    def _calculate_kpi_dimensions(self, pdf: ReportPDF):
        col_gap = 8
        cols = 3
        box_w = (pdf.epw - (cols - 1) * col_gap) / cols
        row_h1 = 50
        self._kpi_dims = {
            "col_gap": col_gap,
            "cols": cols,
            "box_w": box_w,
            "row_h1": row_h1,
        }

    def _calculate_kpi_positions(self, pdf: ReportPDF):
        y0 = pdf.get_y()
        col_x = [
            pdf.l_margin + i * (self._kpi_dims["box_w"] + self._kpi_dims["col_gap"])
            for i in range(self._kpi_dims["cols"])
        ]
        self._kpi_pos = {"y0": y0, "col_x": col_x}

    def _store_kpi_layout(self):
        self._kpi_layout = {**self._kpi_dims, **self._kpi_pos}

    def _add_kpi_boxes_content(self, pdf: ReportPDF):
        layout = self._kpi_layout
        self._add_total_records_box(pdf, layout)
        self._add_suspicious_records_box(pdf, layout)
        self._add_most_suspicious_day_box(pdf, layout)

    def _add_total_records_box(self, pdf: ReportPDF, layout):
        pdf.add_kpi_box(
            "Número total de registros",
            str(self.total_deteccoes),
            layout["col_x"][0],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

    def _add_suspicious_records_box(self, pdf: ReportPDF, layout):
        num_txt = str(self.num_suspeitos) if self.num_suspeitos > 0 else "0"
        pdf.add_kpi_box(
            "Número de registros suspeitos",
            num_txt,
            layout["col_x"][1],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

    def _add_most_suspicious_day_box(self, pdf: ReportPDF, layout):
        dia_txt = self.dia_mais_sus if self.dia_mais_sus != "N/A" else "N/A"
        if self.dia_mais_sus != "N/A":
            dia_txt = f"{self.dia_mais_sus} ({self.sus_dia_mais_sus})"
        pdf.add_kpi_box(
            "Dia com mais registros suspeitos",
            dia_txt,
            layout["col_x"][2],
            layout["y0"],
            layout["box_w"],
            layout["row_h1"],
        )

    def _add_how_to_read_page(self, pdf: ReportPDF):
        self._add_introduction_section(pdf)
        self._add_visual_examples_section(pdf)

    def _add_introduction_section(self, pdf: ReportPDF):
        self._add_introduction_header(pdf)
        self._add_introduction_content(pdf)

    def _add_introduction_header(self, pdf: ReportPDF):
        pdf.add_page()
        pdf.chapter_title("1. Introdução: como ler este relatório")

    def _add_introduction_content(self, pdf: ReportPDF):
        self._add_intro_paragraph(pdf)
        self._add_introduction_explanations(pdf)

    def _add_introduction_explanations(self, pdf: ReportPDF):
        self._add_dashed_lines_explanation(pdf)
        self._add_color_interpretation(pdf)
        self._add_trails_explanation(pdf)
        self._add_trail_criteria(pdf)
        self._add_conclusion(pdf)

    def _add_intro_paragraph(self, pdf: ReportPDF):
        pdf.chapter_html(
            "&nbsp;&nbsp;&nbsp;&nbsp;"
            "Esta seção tem como finalidade orientar a interpretação das informações apresentadas. "
            "É importante destacar que este relatório <b>não comprova a existência de clonagem de placa</b>. "
            "Ele reúne <b>indícios e suspeitas</b> baseados em padrões de deslocamento considerados improváveis "
            "para um único veículo, a partir dos registros capturados pelos radares da cidade."
        )

    def _add_dashed_lines_explanation(self, pdf: ReportPDF):
        pdf.sub_title("Linhas tracejadas conectando pontos nos mapas")
        pdf.chapter_html(
            "- Representam pares de detecções consecutivas que sugerem um deslocamento improvável para um único veículo, "
            "em função da distância e do tempo entre registros.<br>"
            "- Indicam velocidades médias calculadas que superam limites plausíveis em área urbana.<br>"
            "- Funcionam como <b>sinalizadores de inconsistências</b>."
        )

    def _add_color_interpretation(self, pdf: ReportPDF):
        pdf.sub_title("Interpretação das cores nos mapas")
        pdf.chapter_html(
            "<b>Cinza</b>: pares suspeitos onde não foi possível separar os registros em duas trilhas distintas. "
            "O deslocamento parece improvável, mas os dados não permitem identificar com clareza dois veículos diferentes.<br><br>"
            "<b>Azul claro</b> e <b>azul escuro</b>: usados quando os registros foram agrupados em "
            "<b>duas trilhas consistentes</b>, sugerindo a possibilidade de dois veículos distintos utilizando a mesma placa. "
            "Cada cor corresponde a uma trilha independente."
        )

    def _add_trails_explanation(self, pdf: ReportPDF):
        pdf.sub_title("O que são as trilhas neste relatório?")
        pdf.chapter_html(
            "&nbsp;&nbsp;&nbsp;&nbsp;"
            "A trilha é a sequência ordenada, no tempo, de detecções atribuídas a um mesmo veículo hipotético. "
            "Ela representa o percurso plausível que esse veículo poderia ter realizado."
        )

    def _add_trail_criteria(self, pdf: ReportPDF):
        pdf.chapter_html(
            "Critérios adotados para a construção das trilhas:<br><br>"
            "- <b>Ordenação temporal</b>: registros organizados conforme data e hora.<br>"
            "- <b>Coerência espacial</b>: pontos sucessivos devem compor trajetos viáveis, sem deslocamentos impossíveis.<br>"
            "- <b>Velocidade plausível</b>: as médias calculadas precisam estar dentro de limites compatíveis com a mobilidade urbana."
        )

    def _add_conclusion(self, pdf: ReportPDF):
        pdf.chapter_html(
            "&nbsp;&nbsp;&nbsp;&nbsp;"
            "Quando os dados permitem separar os registros em duas trilhas consistentes, isso sugere a presença "
            "de dois veículos distintos usando a mesma placa. Quando não é possível estabelecer duas trilhas coerentes, os registros "
            "permanecem em <b>cinza</b>, sinalizando suspeita que requer investigação adicional."
        )

    def _add_visual_examples_section(self, pdf: ReportPDF):
        pdf.add_page()
        pdf.sub_title("Exemplos de pares suspeitos")
        pdf.chapter_body(
            "Os exemplos abaixo ilustram como os indícios de clonagem são apresentados nos mapas. "
            "Eles mostram cenários onde as detecções foram ou não separadas em trilhas distintas, ajudando a entender os padrões identificados."
        )
        self._add_separable_example(pdf)
        self._add_non_separable_example(pdf)

    def _add_separable_example(self, pdf: ReportPDF):
        pdf.add_figure(
            "app/assets/cloning_report/figs/par_separavel.jpeg",
            "Exemplo de par separável",
            text=None,
            width_factor=0.45,
        )
        pdf.chapter_html(
            """Neste exemplo, os pontos foram divididos em duas trilhas distintas, marcadas em <b>azul claro</b> e <b>azul escuro</b>.<br><br>
            - <b>Azul claro</b>: Representa possível veículo 1.<br>
            - <b>Azul escuro</b>: Representa possível veículo 2.<br>"""
        )

    def _add_non_separable_example(self, pdf: ReportPDF):
        pdf.add_figure(
            "app/assets/cloning_report/figs/par_nao_separavel.png",
            "Exemplo de par não separável",
            text=None,
            width_factor=0.45,
        )
        pdf.chapter_html(
            """Neste caso, os pontos, marcados em <b>cinza</b>, indicam deslocamentos improváveis, mas não foi possível separá-los em trilhas distintas. Isso ocorre quando os dados são insuficientes para confirmar a presença de dois veículos.<br><br>
            - <b>Cinza</b>: Sinaliza que o padrão de deslocamento é suspeito, mas não permite divisão clara em dois veículos.<br>
            - Resultado: Indica uma possível clonagem ou erro nos dados, exigindo investigação adicional."""
        )

    def _add_cloning_section(self, pdf: ReportPDF):
        suspeitos = self.results.get("dataframe", pd.DataFrame())
        daily_figs = self.results.get("daily_figures", [])
        self._add_cloning_title(pdf)
        self._add_general_analysis(pdf, suspeitos)
        self._add_daily_analysis(pdf, daily_figs, suspeitos)

    def _add_cloning_title(self, pdf: ReportPDF):
        pdf.add_page()
        pdf.chapter_title("1. Análise de Possíveis Sinais de Clonagem")

    def _add_general_analysis(self, pdf: ReportPDF, suspeitos):
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            self._add_vehicle_separation_methodology_section(pdf)
            self._add_general_map_section(pdf, suspeitos)
            self._add_general_table_section(pdf, suspeitos)
        else:
            self._add_no_suspicious_records_message(pdf)

    def _add_vehicle_separation_methodology_section(self, pdf: ReportPDF):
        pdf.sub_title("Metodologia de Separação de Veículos")
        pdf.chapter_body(
            "A análise parte da identificação de pares de clonagem. Cada par é formado por duas detecções sucessivas "
            "da mesma placa em radares distintos: um registro considerado viável e outro cuja velocidade implícita o "
            "torna inviável. Essa comparação é o ponto de partida para indicar possíveis inconsistências e orientar "
            "a aplicação dos métodos de separação em dois veículos.\n\n"
            "Métodos empregados:\n\n"
            "- Método baseado no tempo (Temporal Viável): os registros são avaliados em ordem cronológica. "
            "Se a inclusão de um ponto em determinado veículo gera uma trajetória inviável, esse ponto é atribuído "
            "ao outro veículo. Além disso, cada par de origem e destino é sempre separado entre os dois veículos.\n\n"
            "- Método baseado na localização (Espacial com Reparo): os registros são agrupados em dois conjuntos "
            "de acordo com a proximidade geográfica. Em seguida, são feitos ajustes para corrigir casos em que "
            "origem e destino do mesmo par tenham sido colocados no mesmo grupo.\n\n"
            "Quando aplicamos a separação:\n"
            "- Em dias com apenas um par, a separação é feita automaticamente (um ponto em cada veículo).\n"
            "- Em dias com vários pares, a separação só ocorre quando há quantidade suficiente de registros "
            "e todas as distâncias entre os radares ultrapassam 2 km. Esse critério evita separações artificiais "
            "em situações muito curtas ou pouco representativas.\n\n"
            "Critério de escolha:\n"
            "- Quando a separação é possível, ambos os métodos (tempo e localização) são testados, e utiliza-se "
            "aquele que gera menos inconsistências, como evitar que origem e destino do mesmo par fiquem atribuídos "
            "ao mesmo veículo.\n\n"
            "Quando a separação não é aplicada (marcadores em cinza):\n"
            "- Em dias com poucos registros ou quando ao menos um par apresenta distância de até 2 km.\n"
            "- Em situações com dados insuficientes ou inconsistentes para formar trajetos confiáveis.\n\n"
            "Limitações:\n"
            "- Os métodos são aproximados, baseados em regras práticas, e não garantem acerto total.\n"
            "- Podem ser afetados por erros de horário, coordenadas ou falhas de leitura dos radares.\n"
            "- O limite de 2 km é um parâmetro de segurança para evitar separações artificiais, mas pode ser ajustado "
            "conforme o contexto urbano.\n\n"
            "Nas próximas páginas, apresentamos recortes diários com mapas e tabelas, aplicando essa lógica sempre que apropriado."
        )

    def _add_general_map_section(self, pdf: ReportPDF, suspeitos):
        pdf.add_page()
        pdf.sub_title("1.1 Mapa geral do período - todas as detecções suspeitas")
        if isinstance(suspeitos, pd.DataFrame) and not suspeitos.empty:
            png_all = render_overall_map_png(suspeitos)
            if png_all:
                pdf.add_figure(png_all, title="", text=None, width_factor=0.98)
        else:
            pdf.chapter_body("Não há registros suspeitos para exibir no mapa geral.")

    def _add_general_table_section(self, pdf: ReportPDF, suspeitos):
        if not isinstance(suspeitos, pd.DataFrame) or suspeitos.empty:
            self._add_no_suspicious_records_message(pdf)
            return

        table_df = self._format_datetime_columns(
            suspeitos, ["Data", "DataDestino", "DataFormatada"]
        )
        table_text = (
            "A tabela apresenta os registros suspeitos identificados no período. "
            "Ela mostra Data (primeira detecção), Primeira Detecção (local e radar), "
            "Detecção Seguinte (local e radar) e a velocidade média."
        )
        pdf.add_table(
            table_df[["Data", "Origem", "Destino", "Km", "s", "Km/h"]],
            title="1.2 Tabela geral de detecções suspeitas",
            text=table_text,
        )

    def _add_no_suspicious_records_message(self, pdf: ReportPDF):
        pdf.chapter_body(
            "Não foram identificados registros suspeitos no período informado. "
            "Caso existam poucos registros no intervalo, experimente ampliar o período."
        )

    def _add_daily_analysis(self, pdf: ReportPDF, daily_figs, suspeitos):
        if daily_figs:
            self._setup_daily_analysis(pdf)
            self._process_daily_figures(pdf, daily_figs, suspeitos)

    def _setup_daily_analysis(self, pdf: ReportPDF):
        pdf.add_page()
        pdf.chapter_title("2. Registros e Mapas Diários")

    def _process_daily_figures(self, pdf: ReportPDF, daily_figs, suspeitos):
        daily_tables = self.results.get("daily_tables", {})
        tracks_by_day = self.results.get("daily_track_tables", {})
        df_sus_all = (
            suspeitos if isinstance(suspeitos, pd.DataFrame) else pd.DataFrame()
        )

        sorted_figs = sorted(
            daily_figs, key=lambda x: datetime.strptime(x["date"], "%d/%m/%Y")
        )
        for i, item in enumerate(sorted_figs):
            self._process_single_day(
                pdf, i, item, daily_tables, tracks_by_day, df_sus_all
            )

    def _process_single_day(
        self, pdf: ReportPDF, i, item, daily_tables, tracks_by_day, df_sus_all
    ):
        if i != 0:
            pdf.add_page()

        day_key = item["date"]
        self._add_day_map(pdf, item, day_key)
        df_day = self._get_day_data(daily_tables, day_key, df_sus_all)

        if df_day is not None and not df_day.empty:
            self._add_day_table(pdf, df_day, day_key)
            self._add_day_tracks(pdf, day_key, tracks_by_day, df_day)
        else:
            pdf.chapter_body("Sem registros suspeitos para tabular neste dia.")

    def _add_day_map(self, pdf: ReportPDF, item, day_key):
        titulo = f"Mapa do dia de registros suspeitos - {day_key}"
        pdf.add_figure(item["path"], titulo, text=None)

    def _get_day_data(self, daily_tables, day_key, df_sus_all):
        df_day = None
        if isinstance(daily_tables, dict) and day_key in daily_tables:
            df_day = daily_tables[day_key].get("todas")

        if (
            (df_day is None or df_day.empty)
            and isinstance(df_sus_all, pd.DataFrame)
            and not df_sus_all.empty
        ):
            df_day = self._extract_day_from_suspeitos(df_sus_all, day_key)

        return df_day

    def _extract_day_from_suspeitos(self, df_sus_all, day_key):
        df_tmp = df_sus_all.copy()
        dt = pd.to_datetime(df_tmp["Data"], errors="coerce")
        mask = dt.dt.strftime("%d/%m/%Y") == day_key
        cols = ["Data", "Origem", "Destino", "Km", "s", "Km/h"]
        subset = df_tmp.loc[mask, cols] if mask.any() else pd.DataFrame(columns=cols)
        if subset.empty:
            return subset
        return self._format_datetime_columns(subset, ["Data", "DataDestino"])

    def _add_day_table(self, pdf: ReportPDF, df_day, day_key):
        try:
            df_print = df_day.copy()
            df_print["Km/h"] = pd.to_numeric(df_print["Km/h"], errors="coerce")
        except Exception:
            df_print = df_day
        df_print = self._format_datetime_columns(
            df_print, ["Data", "DataDestino", "DataFormatada"]
        )

        pdf.add_table(
            df_print[["Data", "Origem", "Destino", "Km", "s", "Km/h"]],
            title=f"Registros suspeitos do dia - {day_key}",
            text=None,
        )

    def _add_day_tracks(self, pdf: ReportPDF, day_key, tracks_by_day, df_day):
        tracks = tracks_by_day.get(day_key) if isinstance(tracks_by_day, dict) else None
        df_c1, df_c2 = self._get_track_dataframes(tracks)
        tem_trilhas = self._check_tracks_exist(df_c1, df_c2)

        single_pair_with_tracks = (
            df_day is not None and len(df_day) == 1 and tem_trilhas
        )

        if single_pair_with_tracks:
            self._add_single_pair_tracks(pdf, df_c1, df_c2, day_key)
        elif tem_trilhas:
            self._add_multiple_tracks(pdf, day_key, tracks, df_c1, df_c2)

    def _get_track_dataframes(self, tracks):
        df_c1 = tracks.get("carro1", pd.DataFrame()) if tracks else pd.DataFrame()
        df_c2 = tracks.get("carro2", pd.DataFrame()) if tracks else pd.DataFrame()
        return df_c1, df_c2

    def _check_tracks_exist(self, df_c1, df_c2):
        return (
            isinstance(df_c1, pd.DataFrame)
            and not df_c1.empty
            and isinstance(df_c2, pd.DataFrame)
            and not df_c2.empty
        )

    def _add_single_pair_tracks(self, pdf: ReportPDF, df_c1, df_c2, day_key):
        df_c1_fmt = self._format_datetime_columns(
            df_c1, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        df_c2_fmt = self._format_datetime_columns(
            df_c2, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        pdf.add_table(df_c1_fmt, title=f"Tabela da trilha - Carro 1 - {day_key}")
        pdf.add_table(df_c2_fmt, title=f"Tabela da trilha - Carro 2 - {day_key}")

    def _add_multiple_tracks(self, pdf: ReportPDF, day_key, tracks, df_c1, df_c2):
        pdf.add_page()
        pdf.sub_title(f"Trilhas (clusters) - {day_key}")

        pngs = self._generate_trail_maps(day_key, tracks)

        if not df_c1.empty:
            self._add_car1_track(pdf, pngs, df_c1, day_key)

        if not df_c2.empty:
            self._add_car2_track(pdf, pngs, df_c2, day_key)

    def _generate_trail_maps(self, day_key, tracks):
        try:
            return generate_trails_map(self.results["dataframe"], day_key, tracks)
        except Exception:
            return {}

    def _add_car1_track(self, pdf: ReportPDF, pngs, df_c1, day_key):
        pdf.sub_title(f"Mapa da trilha - Carro 1 - {day_key}")
        if "carro1" in pngs and os.path.exists(pngs["carro1"]):
            pdf.image(pngs["carro1"], x=10, y=None, w=190)
        df_c1_fmt = self._format_datetime_columns(
            df_c1, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        pdf.add_table(df_c1_fmt, title=f"Tabela da trilha - Carro 1 - {day_key}")

    def _add_car2_track(self, pdf: ReportPDF, pngs, df_c2, day_key):
        pdf.add_page()
        pdf.sub_title(f"Mapa da trilha - Carro 2 - {day_key}")
        if "carro2" in pngs and os.path.exists(pngs["carro2"]):
            pdf.image(pngs["carro2"], x=10, y=None, w=190)
        df_c2_fmt = self._format_datetime_columns(
            df_c2, ["Data", "DataDestino", "DataHora", "DataHora_str"]
        )
        pdf.add_table(df_c2_fmt, title=f"Tabela da trilha - Carro 2 - {day_key}")

    def _format_datetime_columns(
        self, df: pd.DataFrame, columns: list[str]
    ) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        formatted = df.copy()
        for col in columns:
            if col in formatted.columns:
                formatted[col] = formatted[col].apply(
                    lambda value: strftime_safe(value, self.DATETIME_DISPLAY_FORMAT)
                )
        return formatted

    def get_suspicious_pairs(self):
        """Get suspicious pairs data"""
        return self.results.get("dataframe", pd.DataFrame()).to_dict("records")

    def get_analysis_summary(self):
        """Get analysis summary data"""
        return {
            "total_detections": getattr(self, "total_deteccoes", 0),
            "suspicious_pairs_count": getattr(self, "num_suspeitos", 0),
            "period_start": self.periodo_inicio.isoformat(),
            "period_end": self.periodo_fim.isoformat(),
            "plate": self.placa,
        }

    def _create_pdf(self):
        pdf = ReportPDF(report_id=self.report_id)
        self._setup_pdf_fonts(pdf)
        pdf.alias_nb_pages()
        return pdf

    def _setup_pdf_fonts(self, pdf):
        # Use default fonts directly - no need to add them
        pass

    def _add_all_pages(self, pdf):
        self._add_instructions_page(pdf)
        self._add_summary_page(pdf)
        self._add_how_to_read_page(pdf)
        self._add_cloning_section(pdf)
