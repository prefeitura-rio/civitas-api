"""KPI box rendering functionality."""

import os


class KPIRenderer:
    """Handles KPI box rendering in PDF."""

    def __init__(self, pdf_instance):
        self.pdf = pdf_instance

    def render_kpi_box(
        self,
        title,
        value,
        x,
        y,
        w=40,
        h=47,
        num_suspeitos=0,
        pad_x=5,
        pad_top=6,
        pad_bottom=6,
    ):
        """Render KPI box with title, value and icon"""
        self._draw_kpi_background(x, y, w, h)
        layout = self._calculate_kpi_layout(
            x, y, w, h, pad_x, pad_top, pad_bottom, title
        )
        icon_path = self._get_kpi_icon(title, value, num_suspeitos)
        self._draw_kpi_icon(icon_path, layout)
        self._draw_kpi_title(title, layout)
        self._draw_kpi_value(title, value, num_suspeitos, layout)

    def _draw_kpi_background(self, x, y, w, h):
        """Draw KPI box background and border"""
        self.pdf.set_fill_color(240, 240, 240)
        self.pdf.set_draw_color(0, 0, 0)
        try:
            self.pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=5)
        except TypeError:
            self.pdf.rect(x, y, w, h, style="DF")

    def _calculate_kpi_layout(self, x, y, w, h, pad_x, pad_top, pad_bottom, title):
        """Calculate KPI box layout dimensions"""
        if title == "Detecções Suspeitas de Clonagem":
            pad_top = 4
            pad_bottom = 4

        return {
            "inner_x": x + pad_x,
            "inner_w": w - 2 * pad_x,
            "cur_y": y + pad_top,
            "bottom_limit": y + h - pad_bottom,
        }

    def _get_kpi_icon(self, title, value, num_suspeitos):
        """Get icon path based on KPI title"""
        icon_map = self._get_icon_mapping()
        return self._determine_icon_type(title, value, num_suspeitos, icon_map)

    def _get_icon_mapping(self):
        """Get icon mapping dictionary"""
        return {
            "Numero": "app/assets/cloning_report/warning.png",
            "Dia": "app/assets/cloning_report/calendar.png",
            "Turno": "app/assets/cloning_report/clock.png",
            "Radar": "app/assets/cloning_report/radar.png",
            "Par": "app/assets/cloning_report/crescer.png",
            "Veloc": "app/assets/cloning_report/car-speed.png",
            "OK": "app/assets/cloning_report/ok.png",
            "Caution": "app/assets/cloning_report/caution.png",
            "Warn": "app/assets/cloning_report/warning.png",
            "Camera": "app/assets/cloning_report/camera.png",
        }

    def _determine_icon_type(self, title, value, num_suspeitos, icon_map):
        """Determine which icon to use based on title"""
        t = title.lower()
        if "número total de registros" in t or "numero total de registros" in t:
            return icon_map["Radar"]
        elif (
            "número de registros suspeitos" in t or "numero de registros suspeitos" in t
        ):
            return icon_map["Numero"]
        elif t.startswith("dia com mais"):
            return icon_map["Dia"]
        elif t.startswith("turno com mais"):
            return icon_map["Turno"]
        elif t.startswith("radar com mais"):
            return icon_map["Radar"]
        elif t.startswith("par suspeito"):
            return icon_map["Par"]
        elif t.startswith("velocidade suspeita máxima"):
            return icon_map["Veloc"]
        elif title == "Detecções Suspeitas de Clonagem":
            if isinstance(value, str) and "REGISTROS SUSPEITOS" in value:
                return (
                    icon_map["Caution"] if 1 <= num_suspeitos <= 2 else icon_map["Warn"]
                )
            else:
                return icon_map["OK"]
        return None

    def _draw_kpi_icon(self, icon_path, layout):
        """Draw KPI icon if it exists"""
        if icon_path and os.path.exists(icon_path):
            icon_w = icon_h = 12
            self.pdf.image(
                icon_path,
                x=layout["inner_x"] + (layout["inner_w"] - icon_w) / 2,
                y=layout["cur_y"],
                w=icon_w,
                h=icon_h,
            )
            layout["cur_y"] += icon_h + 3

    def _draw_kpi_title(self, title, layout):
        """Draw KPI title"""
        self.pdf.set_font("Helvetica", "", 10)
        self.pdf.set_xy(layout["inner_x"], layout["cur_y"])
        self.pdf.multi_cell(
            layout["inner_w"], 5, title, border=0, align="C", max_line_height=5
        )
        layout["cur_y"] = self.pdf.get_y() + 2

    def _draw_kpi_value(self, title, value, num_suspeitos, layout):
        """Draw KPI value with special handling for suspicious detections"""
        if (
            title == "Detecções Suspeitas de Clonagem"
            and isinstance(value, str)
            and "REGISTROS SUSPEITOS" in value
        ):
            self._draw_suspicious_value(value, num_suspeitos, layout)
        else:
            self._draw_normal_value(value, layout)

    def _draw_suspicious_value(self, value, num_suspeitos, layout):
        """Draw suspicious detection value with color coding"""
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_font("Helvetica", "B", 9)
        self.pdf.set_xy(layout["inner_x"], layout["cur_y"])
        self.pdf.multi_cell(
            layout["inner_w"], 5, str(value), border=0, align="C", max_line_height=5
        )
        layout["cur_y"] = self.pdf.get_y() + 2

        label_h = 6
        layout["cur_y"] = min(layout["cur_y"], layout["bottom_limit"] - label_h)
        self._set_suspicious_color(num_suspeitos)
        self.pdf.set_font("Helvetica", "B", 11)
        self.pdf.set_xy(layout["inner_x"], layout["cur_y"])
        self.pdf.multi_cell(
            layout["inner_w"],
            label_h,
            "SUSPEITO DE CLONAGEM",
            border=0,
            align="C",
            max_line_height=label_h,
        )
        self.pdf.set_text_color(0, 0, 0)

    def _set_suspicious_color(self, num_suspeitos):
        """Set color based on number of suspicious detections"""
        if num_suspeitos >= 3:
            self.pdf.set_text_color(255, 0, 0)
        else:
            self.pdf.set_text_color(255, 165, 0)

    def _draw_normal_value(self, value, layout):
        """Draw normal KPI value"""
        self.pdf.set_font("Helvetica", "B", 12)
        self.pdf.set_xy(layout["inner_x"], layout["cur_y"])
        self.pdf.multi_cell(
            layout["inner_w"], 6, str(value), border=0, align="C", max_line_height=6
        )
