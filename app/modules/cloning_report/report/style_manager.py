"""Styling and appearance management for PDF content."""

from app.modules.cloning_report.report.font_config import FontSize


class StyleManager:
    """Manages PDF styling and appearance."""

    def __init__(self, pdf_instance):
        self.pdf = pdf_instance

    def apply_table_header_style(self):
        """Apply table header styling"""
        self.pdf.set_fill_color(0, 82, 155)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.set_draw_color(200, 200, 200)
        self.pdf.set_font("Helvetica", "B", FontSize.TABLE_HEADER)

    def apply_table_data_style(self):
        """Apply table data styling"""
        self.pdf.set_fill_color(255, 255, 255)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.set_font("Helvetica", "", FontSize.TABLE_DATA)
        self.pdf.set_draw_color(210, 210, 210)

    def apply_chapter_title_style(self):
        """Apply chapter title styling"""
        self.pdf.set_font("Helvetica", "B", FontSize.CHAPTER_TITLE)

    def apply_sub_title_style(self):
        """Apply sub title styling"""
        self.pdf.set_font("Helvetica", "B", FontSize.SECTION_TITLE)

    def apply_body_text_style(self):
        """Apply body text styling"""
        self.pdf.set_font("Helvetica", "", FontSize.BODY_TEXT)

    def apply_italic_style(self):
        """Apply italic text styling"""
        self.pdf.set_font("Helvetica", "I", FontSize.ITALIC_TEXT)

    def apply_bold_style(self, size: int = None):
        """Apply bold text styling"""
        if size is None:
            size = FontSize.BOLD_TEXT
        self.pdf.set_font("Helvetica", "B", size)

    def reset_text_color(self):
        """Reset text color to black"""
        self.pdf.set_text_color(0, 0, 0)

    def set_warning_color(self):
        """Set warning text color (orange)"""
        self.pdf.set_text_color(255, 165, 0)

    def set_error_color(self):
        """Set error text color (red)"""
        self.pdf.set_text_color(255, 0, 0)
