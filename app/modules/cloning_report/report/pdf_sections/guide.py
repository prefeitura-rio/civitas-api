from __future__ import annotations

from .base import BaseSectionRenderer


class HowToReadRenderer(BaseSectionRenderer):
    """Renders the 'how to read this report' section."""

    def render(self) -> None:
        self._add_introduction_section()
        self._add_visual_examples_section()

    def _add_introduction_section(self) -> None:
        self._add_introduction_header()
        self._add_introduction_content()

    def _add_introduction_header(self) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.chapter_title("1. Introdução: como ler este relatório")

    def _add_introduction_content(self) -> None:
        pdf = self.pdf
        pdf.chapter_html(
            "&nbsp;&nbsp;&nbsp;&nbsp;"
            "Esta seção tem como finalidade orientar a interpretação das informações apresentadas. "
            "É importante destacar que este relatório <b>não comprova a existência de clonagem de placa</b>. "
            "Ele reúne <b>indícios e suspeitas</b> baseados em padrões de deslocamento considerados improváveis "
            "para um único veículo, a partir dos registros capturados pelos radares da cidade."
        )
        self._add_introduction_explanations()

    def _add_introduction_explanations(self) -> None:
        self._add_dashed_lines_explanation()
        self._add_color_interpretation()
        self._add_trails_explanation()
        self._add_trail_criteria()
        self._add_conclusion()

    def _add_dashed_lines_explanation(self) -> None:
        pdf = self.pdf
        pdf.sub_title("Linhas tracejadas conectando pontos nos mapas")
        pdf.chapter_html(
            "- Representam pares de detecções consecutivas que sugerem um deslocamento improvável para um único veículo, "
            "em função da distância e do tempo entre registros.<br>"
            "- Indicam velocidades médias calculadas que superam limites plausíveis em área urbana.<br>"
            "- Funcionam como <b>sinalizadores de inconsistências</b>."
        )

    def _add_color_interpretation(self) -> None:
        pdf = self.pdf
        pdf.sub_title("Interpretação das cores nos mapas")
        pdf.chapter_html(
            "<b>Cinza</b>: pares suspeitos onde não foi possível separar os registros em duas trilhas distintas. "
            "O deslocamento parece improvável, mas os dados não permitem identificar com clareza dois veículos diferentes.<br><br>"
            "<b>Azul claro</b> e <b>azul escuro</b>: usados quando os registros foram agrupados em "
            "<b>duas trilhas consistentes</b>, sugerindo a possibilidade de dois veículos distintos utilizando a mesma placa. "
            "Cada cor corresponde a uma trilha independente."
        )

    def _add_trails_explanation(self) -> None:
        pdf = self.pdf
        pdf.sub_title("O que são as trilhas neste relatório?")
        pdf.chapter_html(
            "&nbsp;&nbsp;&nbsp;&nbsp;"
            "A trilha é a sequência ordenada, no tempo, de detecções atribuídas a um mesmo veículo hipotético. "
            "Ela representa o percurso plausível que esse veículo poderia ter realizado."
        )

    def _add_trail_criteria(self) -> None:
        pdf = self.pdf
        pdf.chapter_html(
            "Critérios adotados para a construção das trilhas:<br><br>"
            "- <b>Ordenação temporal</b>: registros organizados conforme data e hora.<br>"
            "- <b>Coerência espacial</b>: pontos sucessivos devem compor trajetos viáveis, sem deslocamentos impossíveis.<br>"
            "- <b>Velocidade plausível</b>: as médias calculadas precisam estar dentro de limites compatíveis com a mobilidade urbana."
        )

    def _add_conclusion(self) -> None:
        pdf = self.pdf
        pdf.chapter_html(
            "&nbsp;&nbsp;&nbsp;&nbsp;"
            "Quando os dados permitem separar os registros em duas trilhas consistentes, isso sugere a presença "
            "de dois veículos distintos usando a mesma placa. Quando não é possível estabelecer duas trilhas coerentes, os registros "
            "permanecem em <b>cinza</b>, sinalizando suspeita que requer investigação adicional."
        )

    def _add_visual_examples_section(self) -> None:
        pdf = self.pdf
        pdf.add_page()
        pdf.sub_title("Exemplos de pares suspeitos")
        pdf.chapter_body(
            "Os exemplos abaixo ilustram como os indícios de clonagem são apresentados nos mapas. "
            "Eles mostram cenários onde as detecções foram ou não separadas em trilhas distintas, ajudando a entender os padrões identificados."
        )
        self._add_separable_example()
        self._add_non_separable_example()

    def _add_separable_example(self) -> None:
        pdf = self.pdf
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

    def _add_non_separable_example(self) -> None:
        pdf = self.pdf
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
