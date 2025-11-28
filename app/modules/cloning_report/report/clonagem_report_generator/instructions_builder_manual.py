from datetime import datetime
from fpdf.enums import XPos, YPos

from app.modules.cloning_report.report.pdf_base import ReportPDF
from app.modules.cloning_report.report.font_config import FontSize


class InstructionsBuilderManual:
    """
    Manual rendering of static instruction content using fpdf primitives
    (avoids write_html).
    """

    # Font sizes
    H2_SIZE = 14
    H3_SIZE = 11
    P_SIZE = FontSize.INSTRUCTIONS_BODY  # 9

    def render_static_content_first(self, pdf: ReportPDF) -> bool:
        return self._render_static_text_manual(pdf)

    def render_static_content_second(self, pdf: ReportPDF) -> bool:
        return self._render_static_text_manual_2(pdf)

    def _set_h2(self, pdf: ReportPDF):
        pdf.set_font("Helvetica", "B", self.H2_SIZE)
        pdf.set_text_color(0, 0, 0)

    def _set_h3(self, pdf: ReportPDF):
        pdf.set_font("Helvetica", "B", self.H3_SIZE)
        pdf.set_text_color(0, 0, 0)

    def _set_p(self, pdf: ReportPDF):
        pdf.set_font("Helvetica", "", self.P_SIZE)
        pdf.set_text_color(0, 0, 0)

    def _set_p_bold(self, pdf: ReportPDF):
        pdf.set_font("Helvetica", "B", self.P_SIZE)
        pdf.set_text_color(0, 0, 0)

    def _render_static_text_manual_2(self, pdf: ReportPDF) -> bool:
        """
        Manually render the content of static_text_2.html using FPDF primitives.
        """
        # Content
        pdf.ln(10)
        self._set_h2(pdf)
        pdf.multi_cell(
            0,
            6,
            "Como ler o relatório",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(4)

        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw, 4, "Definições:", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
        )
        pdf.ln(2)

        # Item 1
        pdf.multi_cell(
            pdf.epw,
            4,
            "- Linhas tracejadas conectando pontos nos mapas",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        indent = 10
        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(
            pdf.epw - indent,
            4,
            "Representam pares de detecções consecutivas que sugerem um deslocamento improvável para um único veículo, funcionando como sinalizadores de inconsistências.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(3)

        # Item 2
        pdf.multi_cell(
            pdf.epw,
            4,
            "- Interpretação das cores nos mapas",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        sub_indent = 15
        pdf.set_x(pdf.l_margin + sub_indent)
        pdf.multi_cell(
            pdf.epw - sub_indent,
            4,
            "- o Cinza: pares suspeitos onde não foi possível separar os registros em duas trilhas distintas. O deslocamento parece improvável, mas os dados não permitem identificar com clareza dois veículos diferentes.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        pdf.set_x(pdf.l_margin + sub_indent)
        pdf.multi_cell(
            pdf.epw - sub_indent,
            4,
            "- o Azul claro e azul escuro: usados quando os registros foram agrupados em duas trilhas consistentes, sugerindo a possibilidade de dois veículos distintos utilizando a mesma placa. Cada cor corresponde a uma trilha independente.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(3)

        # Item 3
        pdf.multi_cell(
            pdf.epw,
            4,
            "- O que são as trilhas neste relatório?",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(
            pdf.epw - indent,
            4,
            "    A trilha é a sequência ordenada, no tempo, de detecções atribuídas ao possível Veículo 1 e ao Veículo 2.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(
            pdf.epw - indent,
            4,
            "    Quando os dados permitem separar os registros em duas trilhas consistentes, isso sugere a presença de dois veículos distintos usando a mesma placa. Quando não é possível estabelecer duas trilhas coerentes, os registros permanecem em cinza, sinalizando suspeita que requer investigação adicional.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.add_page()

        return True

    def _render_static_text_manual(self, pdf: ReportPDF) -> bool:
        """
        Manually render the content of static_text.html using FPDF primitives.
        """
        # Content

        # --- Estrutura do Relatório ---
        self._set_h2(pdf)
        pdf.multi_cell(
            pdf.epw,
            6,
            "Estrutura do Relatório",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(2)

        self._set_p(pdf)

        pdf.chapter_body(
            "    Este relatório foi elaborado para aprofundar a análise de casos suspeitos de "
            "clonagem de placas identificados pelos radares da cidade. Em algumas situações, uma "
            "mesma placa aparece registrada em pontos diferentes com intervalos de tempo que não "
            "são compatíveis com o deslocamento real de um único veículo. Esses padrões exigem "
            "investigação, pois podem indicar que dois automóveis distintos estão circulando "
            "simultaneamente com a mesma placa.",
        )
        pdf.ln(2)

        pdf.chapter_body(
            "    A partir dessa necessidade, o foco deste relatório é separar as detecções em duas "
            "trilhas coerentes de circulação, cada qual atribuída a um veículo, identificados, aqui, como "
            "Veículo A e Veículo B. O objetivo central é reconstruir o trajeto provável de cada trilha, "
            "permitindo separar os trajetos de carros distintos e identificar padrões de deslocamento "
            "independentes.",
        )
        pdf.ln(2)

        pdf.chapter_body(
            "    Ao final, o relatório apresenta as rotas reconstruídas de cada trilha, oferecendo "
            "subsídios para a compreensão da dinâmica de circulação e para reforçar, ou descartar, a "
            "hipótese de clonagem da placa analisada. ",
        )
        pdf.ln(2)

        pdf.chapter_body("   O relatório é dividido em quatro processos:")
        pdf.ln(4)

        # Items 1-4
        items = [
            (
                "1. Recebimento da demanda",
                "Autoridade solicitante fornece a placa de veículo e período de busca para identificação de possíveis suspeitas de clonagem",
            ),
            (
                "2. Identificação de suspeita de clonagem",
                "Mapeamento de pares de detecções (duas passagens consecutivas) que apontem suspeita de clone no período",
            ),
            (
                "3. Geração de Mapa Geral da Análise",
                "Consolidação de todos os pares de detecções classificados como suspeitos ao longo do período analisado.",
            ),
            (
                "4. Geração de Mapas Diários: separação em trilhas",
                "Identificação de pontos de detecções atribuíveis a possíveis veículos distintos (Veículo 1 e Veículo 2) diariamente.",
            ),
        ]

        for title, text in items:
            self._set_h3(pdf)
            pdf.multi_cell(
                pdf.epw, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )

            self._set_p(pdf)
            pdf.set_x(pdf.l_margin + 5)
            pdf.multi_cell(
                pdf.epw - 5, 4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )
            pdf.ln(3)

        pdf.ln(2)

        # --- Parâmetros de Busca ---
        self._set_h2(pdf)
        pdf.multi_cell(
            pdf.epw,
            6,
            "Parâmetros de Busca",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(2)

        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            "Abaixo estão os parâmetros utilizados para a geração do relatório. Eles são definidos pelo solicitante.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(4)

        param_items = [
            (
                "1. Placa Demandada",
                "Placa de veículo fornecida pela autoridade de segurança.",
            ),
            (
                "2. Data Inicial e Final",
                "Intervalo de tempo para a busca suspeita de placa clonada.",
            ),
        ]

        for title, text in param_items:
            self._set_h3(pdf)
            pdf.multi_cell(
                pdf.epw, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )
            self._set_p(pdf)
            pdf.multi_cell(
                pdf.epw, 4, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )
            pdf.ln(3)

        pdf.ln(2)

        # --- Apontamento da Suspeita de Clonagem ---
        self._set_h2(pdf)
        pdf.multi_cell(
            pdf.epw,
            6,
            "Apontamento da Suspeita de Clonagem",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(2)

        ul_items = [
            "A suspeita de clone é sinalizada quando o intervalo de tempo e a distância entre duas detecções sucessivas de uma mesma placa são incompatíveis com um deslocamento urbano normal. Por exemplo, um curto intervalo de tempo aliado a uma longa distância pode sugerir a presença de dois veículos com a mesma placa circulando simultaneamente.",
            "A classificação de suspeita ocorre quando a velocidade média estimada para percorrer a distância entre dois pontos excede 110 km/h, considerando uma linha reta entre os pontos e desconsiderando possíveis rotas reais.",
        ]

        for item in ul_items:
            self._set_p(pdf)
            pdf.multi_cell(
                pdf.epw, 4, f"- {item}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )
            pdf.ln(1)

        pdf.ln(2)

        self._set_p_bold(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            "Importante: este relatório não comprova a existência de clonagem de placa. Ele apenas indica situações que requerem verificação adicional.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(4)

        # --- Limitações do Relatório ---
        self._set_h2(pdf)
        pdf.multi_cell(
            pdf.epw,
            6,
            "Limitações do Relatório",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(2)

        # Item 1
        self._set_h3(pdf)
        pdf.multi_cell(
            pdf.epw,
            5,
            "1. Período de disponibilidade dos dados",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            "Os dados de detecções estão disponíveis desde a data 01/06/2024 em diante. Não é possível consultar períodos anteriores.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(3)

        # Item 2
        self._set_h3(pdf)
        pdf.multi_cell(
            pdf.epw,
            5,
            "2. Ausência de Detecção",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            "A ausência de registro não implica necessariamente que o veículo não tenha passado pelo local. A leitura por OCR pode falhar devido a fatores como:",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        ul_items_2 = [
            "Falhas de OCR, obstruções, manutenção ou indisponibilidade do equipamento;",
            'Leitura equivocada de caracteres similares como "O/0" ou "B/8";',
            "Dependência da qualidade e integridade dos dados capturados pelos radares, sujeitos a variações técnicas ou climáticas.",
        ]
        for item in ul_items_2:
            pdf.multi_cell(
                pdf.epw, 4, f"- {item}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )
        pdf.ln(3)

        # Item 3
        self._set_h3(pdf)
        pdf.multi_cell(
            pdf.epw,
            5,
            "3. Apontamento de suspeita de clonagem",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            "A detecção de suspeitas de clonagem erroneamente pode ocorrer em razão de fatores como:",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        ul_items_3 = [
            "Erro de sincronização de relógio entre equipamentos;",
            "Erro de leitura de radar;",
            "Parâmetros fixos de velocidade que podem não contemplar situações excepcionais (ex.: deslocamentos de emergência).",
        ]
        for item in ul_items_3:
            pdf.multi_cell(
                pdf.epw, 4, f"- {item}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
            )
        pdf.ln(2)

        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            "Os dados deste relatório não são exaustivos: a falta de registro de uma placa não comprova a ausência de passagem, e detecções simultâneas incompatíveis com o deslocamento urbano não indicam, necessariamente, clonagem de placa.",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.ln(4)

        # --- Parâmetros Gerais ---
        # Variable substitution
        plate = getattr(self, "placa", "")
        start_date = getattr(self, "periodo_inicio", "")
        end_date = getattr(self, "periodo_fim", "")

        if isinstance(start_date, (datetime,)):
            start_date = start_date.strftime("%d/%m/%Y às %H:%M:%S")
        if isinstance(end_date, (datetime,)):
            end_date = end_date.strftime("%d/%m/%Y às %H:%M:%S")

        self._set_h3(pdf)
        pdf.multi_cell(
            pdf.epw,
            5,
            "Parâmetros Gerais",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        self._set_p(pdf)
        pdf.multi_cell(
            pdf.epw,
            4,
            f"Placa demandada: {plate}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )
        pdf.multi_cell(
            pdf.epw,
            4,
            f"Período analisado: de {start_date} até {end_date}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            align="L",
        )

        return True
