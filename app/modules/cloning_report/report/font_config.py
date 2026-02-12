"""Centralized font configuration for PDF reports."""

from enum import IntEnum


class FontSize(IntEnum):
    """Centralized font size configuration for PDF reports."""

    # Main titles
    MAIN_TITLE = 15
    CHAPTER_TITLE = 17
    SECTION_TITLE = 12
    SUBSECTION_TITLE = 11

    # Body text
    BODY_TEXT = 9
    BODY_TEXT_LARGE = 10

    # Headers and footers
    HEADER_TITLE = 13
    HEADER_ID = 9
    FOOTER_TEXT = 8

    # Tables
    TABLE_HEADER = 9
    TABLE_DATA = 9
    TABLE_TITLE = 12

    # KPIs and special elements
    KPI_TITLE = 10
    KPI_VALUE = 11
    KPI_VALUE_LARGE = 12
    KPI_VALUE_SMALL = 9
    KPI_SECTION_TITLE = 22

    # Special formatting
    ITALIC_TEXT = 9
    BOLD_TEXT = 9

    # Instructions
    INSTRUCTIONS_TITLE = 12
    INSTRUCTIONS_BODY = 9
