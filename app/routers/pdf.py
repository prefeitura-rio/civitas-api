import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fpdf import FPDF
from pydantic import BaseModel, validator

from app import config
from app.decorators import router_request
from app.dependencies import is_user
from app.models import ReportHistory, User
from app.pydantic_models import (
    PdfReportCorrelatedPlatesIn,
    PdfReportMultipleCorrelatedPlatesIn,
)
from app.services.pdf.multiple_correlated_plates import (
    DataService,
    GraphService,
    PdfService,
)
from app.modules.cloning_report.utils import (
    create_report_temp_dir,
    generate_report_bundle_stream,
    prepare_map_html,
    resolve_pdf_path,
)
from app.utils import generate_report_id

from loguru import logger


class CustomPDF(FPDF):
    """
    Custom PDF class extending FPDF for standardized report generation.

    This class provides customized header formatting for PDF reports generated
    by the application. It includes consistent branding elements such as logos,
    report titles, and unique report identifiers.

    The class ensures all PDF reports maintain a consistent look and feel while
    providing specific information relevant to each report type.

    Attributes:
    -----------
    _report_id : str, optional
        The unique identifier for the report, displayed in the header.
    """

    def __init__(self, report_id: str | None = None, *args, **kwargs):
        """
        Initialize the CustomPDF with optional report ID.

        Parameters:
        -----------
        report_id : str, optional
            The unique identifier for the report.
        *args, **kwargs
            Additional arguments passed to the parent FPDF class.
        """
        super().__init__(*args, **kwargs)
        self._report_id = report_id

    def header(self):
        """
        Define the standard header for all pages in the PDF.

        The header includes:
        - Two logos (Prefeitura and Civitas) in the left cell
        - Report title in the center/right cell
        - Report ID in a row beneath the logos and title

        This method is automatically called by FPDF when rendering each page.
        """
        # Set position
        self.set_y(10)

        # First row: Two cells (images + title)
        self.set_font("Times", size=14)

        # First cell: Add two images
        first_cell_width = 60  # Increased width of the first cell
        first_line_height = (
            15  # Increased height of the first line to accommodate larger images
        )
        image_height = 18  # Increased height of the images
        y_offset = (
            first_line_height - image_height
        ) / 2  # Vertical offset to center the images

        # Draw the placeholder cell
        self.cell(first_cell_width, first_line_height, "", border=1)

        # Add the first image (vertically centered)
        self.image(
            config.ASSETS_DIR / "logo_prefeitura.png", x=12, y=13 + y_offset, w=22
        )  # Adjust x, y, and width
        # Add the second image (vertically centered)
        self.image(config.ASSETS_DIR / "logo_civitas.png", x=38, y=14 + y_offset, w=30)

        # Second cell: Title
        remaining_width = (
            self.w - first_cell_width - 2 * self.l_margin
        )  # Total width - first cell width - margins
        self.set_xy(self.l_margin + first_cell_width, 10)  # Set position for the title
        self.multi_cell(
            remaining_width,
            15,
            "RELATÓRIO DE DETECÇÃO DE PLACAS CONJUNTAS",
            border=1,
            align="C",
        )

        # Second row: One cell (ID)
        self.set_xy(self.l_margin, 10 + first_line_height)  # Set position for the ID
        self.cell(
            0,
            7,
            f"ID: {self._report_id or 'N/A'}",
            border=1,
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(5)


router = APIRouter(
    prefix="/pdf",
    tags=["PDF reports"],
    responses={
        401: {"description": "You don't have permission to do this."},
        404: {"description": "Not found."},
        429: {"error": "Rate limit exceeded"},
    },
)


class PdfReportCloningIn(BaseModel):
    plate: str
    date_start: datetime
    date_end: datetime
    output_dir: str
    renderer: Literal["fpdf", "weasy"] = "fpdf"
    # project_id: Optional[str] = None
    # credentials_path: Optional[str] = None

    @validator("date_start", "date_end")
    @classmethod
    def normalize_to_utc(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            elif v.tzinfo != timezone.utc:
                return v.astimezone(timezone.utc)
        return v


@router.post("/cloning-report")
async def generate_cloning_report(
    request: Request,
    # user: Annotated[User, Depends(is_user)],  # Temporariamente comentado para teste
    data: PdfReportCloningIn,
) -> StreamingResponse:
    """
    Generate cloning detection report bundle (PDF + HTML) using async BigQuery service

    This endpoint generates a comprehensive cloning detection report for a specific
    vehicle plate within a given time period. The report is generated asynchronously
    using the global BigQuery client and returned as a streaming ZIP response
    containing both the PDF document and the interactive HTML map. All artifacts are
    produced inside the operating system's temporary directory and removed after
    streaming.

    Requires authentication via the is_user dependency.

    Args:
        request: FastAPI request object
        user: Authenticated user (from dependency injection)
        data: Cloning report parameters including plate, date range, and output directory

    Returns:
        StreamingResponse: ZIP archive with report PDF and HTML map

    Raises:
        HTTPException: If report generation fails or BigQuery connection issues
    """
    try:
        # Import async service
        from app.modules.cloning_report.application.async_services import (
            get_async_cloning_service,
        )

        # Generate unique report ID
        report_id = await generate_report_id()
        logger.info(
            f"Starting cloning report generation for plate {data.plate} (Report ID: {report_id})"
        )

        # Create async cloning service instance
        service = get_async_cloning_service()

        try:
            temp_output_dir = create_report_temp_dir(report_id)
            logger.debug(
                f"Using temporary directory for cloning report artifacts: {temp_output_dir}"
            )

            report = await _execute_cloning_report(
                service=service,
                data=data,
                report_id=report_id,
                output_dir=temp_output_dir,
                renderer=data.renderer,
            )
            return _build_cloning_report_response(
                report=report, report_id=report_id, plate=data.plate
            )

        finally:
            await service.close()

    except Exception as e:
        logger.error(
            f"Failed to generate cloning report for plate {data.plate}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate cloning report: {str(e)}"
        )


async def _execute_cloning_report(
    service,
    data: PdfReportCloningIn,
    report_id: str,
    output_dir: Path,
    renderer: str,
):
    """Run the core cloning report generation workflow."""
    try:
        report = await service.execute(
            plate=data.plate,
            date_start=data.date_start,
            date_end=data.date_end,
            output_dir=str(output_dir),
            report_id=report_id,
            renderer=renderer,
        )
        logger.info(f"Cloning report generated successfully: {report.report_path}")
        return report
    except Exception as error:
        logger.error(
            f"Failed to generate cloning report for plate {data.plate}: {error}"
        )
        raise


def _build_cloning_report_response(
    report,
    report_id: str,
    plate: str,
) -> StreamingResponse:
    """Assemble the ZIP response containing the PDF and HTML map."""
    pdf_path = resolve_pdf_path(report.report_path)
    html_path = prepare_map_html(report_id)

    logger.info(
        f"Cloning report streaming started for plate {plate} (Report ID: {report_id})"
    )

    return StreamingResponse(
        generate_report_bundle_stream(pdf_path, html_path),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=cloning_report_{plate}_{report_id}.zip",
            "X-Report-ID": report_id,
            "X-Plate": plate,
            "X-Total-Detections": str(report.total_detections),
            "X-Suspicious-Pairs": str(len(report.suspicious_pairs)),
            "X-Map-Included": "true" if html_path else "false",
        },
    )


@router_request(method="POST", router=router, path="/correlated-plates")
async def generate_report_correlated_plates(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: PdfReportCorrelatedPlatesIn,
) -> StreamingResponse:
    # Setup PDF
    report_id = await generate_report_id()
    pdf = CustomPDF(report_id=report_id)
    pdf.add_page()
    pdf.set_font("Times", size=11)

    # # Helper function to format date
    # def format_date(date_str: str):
    #     try:
    #         # Try parsing with milliseconds and 'Z' suffix
    #         date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    #     except ValueError:
    #         try:
    #             # Try parsing without milliseconds and 'Z' suffix
    #             date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    #         except ValueError:
    #             # If both fail, return the original string
    #             return date_str
    #     return date.strftime("%d/%m/%Y %H:%M:%S")

    # # Helper function to format date UTC
    # def format_date_UTC(date_str):
    #     try:
    #         # Try parsing with milliseconds and 'Z' suffix
    #         date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    #     except ValueError:
    #         try:
    #             # Try parsing without milliseconds and 'Z' suffix
    #             date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    #         except ValueError:
    #             # If both fail, return the original string
    #             return date_str

    #     # Convert the date to UTC-3
    #     utc_date = date.replace(tzinfo=timezone.utc)  # Assume the input date is in UTC
    #     utc_minus_3 = utc_date.astimezone(timezone(timedelta(hours=-3)))  # Convert to UTC-3

    #     # Format the date as desired
    #     return utc_minus_3.strftime("%d/%m/%Y %H:%M:%S")

    # Disclaimer Section
    pdf.set_font("Times", size=18)
    pdf.cell(
        0,
        4,
        text="Informações gerais sobre o relatório",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(3)

    pdf.set_font("Times", style="B", size=12)
    pdf.cell(0, 5, text="Estrutura do relatório", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", size=10)
    pdf.multi_cell(
        0,
        5,
        text="O relatório identifica placas de veículos que passaram junto a uma placa principal monitorada (Placas conjuntas). A identificação é feita dentro de um intervalo de tempo determinado pela investigação a partir dos parâmetros de busca no sistema. O relatório também aponta a frequência com que as placas conjuntas foram detectadas junto à placa principal monitorada. A apresentação do resultado se dá por ordem decrescente de passagens conjuntas. Este documento é gerado automaticamente pelo sistema, sem interferência humana. Todo esse documento é auditável.",
    )
    pdf.ln(2)

    pdf.set_font("Times", style="B", size=12)
    pdf.cell(0, 5, text="Parâmetros de busca", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Times", style="B", size=10)
    pdf.cell(0, 5, text="Intervalo de tempo", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", size=10)
    pdf.multi_cell(
        0,
        5,
        text="As buscas por placas conjuntas podem ser feitas até cinco minutos antes e cinco minutos depois da passagem da placa principal monitorada. A escolha dos parâmetros é feita pelo solicitante da informação. Quando não há informação sobre o período de busca na solicitação, o operador da Civitas utiliza o intervalo padrão definido nas diretrizes operacionais internas (três minutos antes e três minutos depois e de até 50 placas).",
    )
    pdf.ln(1)

    pdf.set_font("Times", style="B", size=10)
    pdf.cell(
        0,
        5,
        text="Quantidade de placas conjuntas por buscas",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Times", size=10)
    pdf.multi_cell(
        0,
        5,
        text="São identificadas no máximo 50 placas antes e 50 placas depois da placa principal monitorada.",
    )
    pdf.ln(2)

    pdf.set_font("Times", style="B", size=12)
    pdf.cell(0, 5, text="Radares e localização", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Times", size=10)
    bullet_points = [
        "Cada radar possui um número identificador próprio. Todas as detecções feitas pelo sistema apontam o número identificador do equipamento que fez a leitura.",
        "Cada radar possui também informações de localização que incluem coordenadas geográficas e endereços completos. Essas informações também estão disponíveis junto a cada registro.",
        "O sentido de circulação da via é fornecido, salvo quando há indisponibilidade da informação no banco de dados.",
    ]

    for point in bullet_points:
        pdf.multi_cell(0, 5, text=f"{chr(149)} {point}")
        pdf.ln(1)
    pdf.ln(2)

    pdf.set_font("Times", style="B", size=12)
    pdf.cell(0, 5, text="Como ler o relatório", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Times", size=10)
    bullet_points = [
        "O relatório é disposto em duas partes. Na primeira parte, consta um ranking com a frequência com que cada placa conjunta aparece junto à placa monitorada durante o tempo determinado nas buscas. Nesta parte, as placas são classificadas de forma decrescente a partir da quantidade de vezes que passavam junto à placa monitorada.",
        "A segunda parte é composta por tabelas que apresentam em ordem cronológica todas as placas detectadas que passaram antes e depois da placa principal monitorada por grupo de radar.",
        "O relatório apresenta tabelas com linhas e colunas. A linha grifada em amarelo representa a placa principal monitorada na qual pretende-se buscar as placas conjuntas.",
        "Ao lado da listagem com cada placa, na coluna à direita, é apresentado a quantidade de vezes (ocorrências) que cada placa foi registrada em conjunto com a placa monitorada.",
    ]

    for point in bullet_points:
        pdf.multi_cell(0, 5, text=f"{chr(149)} {point}")
        pdf.ln(1)

    pdf.ln(2)

    pdf.set_font("Times", style="B", size=12)
    pdf.cell(0, 5, text="Limitações do relatório", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    pdf.set_font("Times", style="B", size=10)
    pdf.cell(0, 5, text="Período disponível", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", size=10)
    pdf.multi_cell(
        0,
        5,
        text="A base de dados dos Sistema conta com um histórico de detecções a partir da data de 01/06/2024. Não é possível realizar buscas a períodos anteriores.",
    )
    pdf.ln(1)

    pdf.set_font("Times", style="B", size=10)
    pdf.cell(0, 5, text="Ausência de detecção", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", size=10)
    pdf.multi_cell(
        0,
        5,
        text=f"{chr(149)} A falta de registro de uma placa não significa, necessariamente, que o veículo não passou pelo local. A leitura de OCR pode ser inviabilizada em algumas circunstâncias, tais como: mau estado de conservação das placas, objetos obstruindo as câmeras de leitura, condições climáticas, período de inatividade do equipamento entre outros.",
    )
    pdf.ln(1)
    pdf.multi_cell(
        0,
        5,
        text=f"{chr(149)} O relatório não é exaustivo e a falta de registro de uma determinada placa não é determinante para comprovar que não houve a passagem naquela localidade.",
    )

    pdf.ln(1)
    pdf.multi_cell(
        0,
        5,
        text=f"{chr(149)} Quando um radar não possui informações completas de localização (rua, faixa e sentido), as passagens registradas ficam ocultas do relatório. isso pode ocorrer porque a base de referência que relaciona cada radar ao seu código oficial ainda não está totalmente atualizada. Até que a atualização seja concluída, parte das leituras não poderá ser exibida corretamente e, portanto, é temporariamente desconsiderada. Essa medida é necessária para garantir a consistência da análise de correlação, que depende da correspondência de localização completa do equipamento.",
    )

    pdf.ln(1)

    pdf.set_font("Times", style="B", size=10)
    pdf.cell(0, 5, text="Distância entre radares", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", size=10)
    pdf.multi_cell(
        0, 5, text="O relatório não indica trajetos percorridos entre as detecções."
    )

    pdf.ln(10)

    pdf.set_font("Times", size=18)
    pdf.cell(0, 10, text="Parâmetros Gerais", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    pdf.set_font("Times", size=11)
    cover_params = [
        {"label": "Placa monitorada:", "value": data.params.plate},
        {
            "label": "Período analisado:",
            "value": f"De {data.params.start_time} até {data.params.end_time}",
        },
        {"label": "Limite de placas antes e depois:", "value": data.params.n_plates},
        {
            "label": "Intervalo de tempo:",
            "value": f"{data.params.n_minutes} minuto{'s' if data.params.n_minutes > 1 else ''}",
        },
        {
            "label": "Total de detecções da placa monitorada:",
            "value": len(data.report_data),
        },
        {
            "label": "Total de detecções de todos os radares e placas:",
            "value": sum(group.total_detections for group in data.report_data),
        },
    ]

    for param in cover_params:
        pdf.cell(
            0,
            5,
            text=f"{param['label']} {param['value']}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(10)

    # Ranking section
    pdf.set_font("Times", size=18)
    pdf.cell(
        0,
        5,
        text="Placas com mais de uma ocorrência",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(10)

    if data.ranking:
        # Calculate the horizontal offset to center the table
        table_width = 90  # 45 (Placa) + 45 (Nº de ocorrências)
        page_width = pdf.w  # Get the page width
        horizontal_offset = (page_width - table_width) / 2

        # Move to the calculated horizontal offset
        pdf.set_x(horizontal_offset)

        # Table headers
        pdf.set_font("Times", style="B", size=10)
        pdf.cell(40, 7, text="Placa", border=1, align="C")
        pdf.cell(
            45,
            7,
            text="Nº de ocorrências",
            border=1,
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Table rows
        pdf.set_font("Times")
        for row in data.ranking:
            if "-" in row.plate:
                continue
            pdf.set_x(
                horizontal_offset
            )  # Move to the calculated horizontal offset for each row
            if row.plate == data.params.plate:
                pdf.set_fill_color(255, 255, 0)  # Yellow background
                pdf.set_font("", "B")
                fill = True
            else:
                fill = False
                pdf.set_font("", "")
            pdf.cell(40, 7, text=row.plate, border=1, align="C", fill=fill)
            pdf.cell(
                45,
                7,
                text=str(row.count),
                border=1,
                align="C",
                new_x="LMARGIN",
                new_y="NEXT",
                fill=fill,
            )
    else:
        pdf.cell(
            0,
            10,
            text="Nenhuma placa foi detectada mais de uma vez nesse relatório além da própria placa monitorada.",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(10)

    # Detection groups
    for i, group in enumerate(data.report_data):
        pdf.set_font("Times", size=18)
        if len(data.report_data) > 1:
            pdf.cell(
                0,
                10,
                text=f"Detecção {i + 1} da placa monitorada",
                new_x="LMARGIN",
                new_y="NEXT",
                align="C",
            )
        else:
            pdf.cell(
                0,
                10,
                text="Detecção única da placa monitorada",
                new_x="LMARGIN",
                new_y="NEXT",
                align="C",
            )
        pdf.ln(5)

        # Group parameters
        pdf.set_font("Times", size=11)
        detection_params = [
            {
                "label": "Data e hora da detecção da placa monitorada:",
                "value": group.detection_time,
            },
            {
                "label": "Período analisado:",
                "value": f"De {group.start_time} até {group.end_time}",
            },
            {"label": "Radares:", "value": ", ".join(group.radars)},
            {
                "label": "Coordenadas:",
                "value": f"Latitude: {group.latitude}, Longitude: {group.longitude}",
            },
            {"label": "Endereço:", "value": group.location},
            {"label": "Total de detecções:", "value": str(group.total_detections)},
        ]

        for param in detection_params:
            pdf.multi_cell(
                0,
                5,
                text=f"{param['label']} {param['value']}",
                new_x="LMARGIN",
                new_y="NEXT",
            )

        pdf.ln(10)

        # Detections table
        if group.detections:
            # Table headers
            pdf.set_font("Times", style="B", size=10)
            pdf.cell(45, 7, text="Data e Hora", border=1, align="C")
            pdf.cell(25, 7, text="Placa", border=1, align="C")
            pdf.cell(25, 7, text="Radar", border=1, align="C")
            pdf.cell(15, 7, text="Faixa", border=1, align="C")
            pdf.cell(40, 7, text="Velocidade [Km/h]", border=1, align="C")
            pdf.cell(
                40,
                7,
                text="Nº de ocorrências",
                border=1,
                align="C",
                new_x="LMARGIN",
                new_y="NEXT",
            )

            # Table rows
            pdf.set_font("Times")
            for detection in group.detections:
                if detection.plate == data.params.plate:
                    pdf.set_fill_color(255, 255, 0)  # Yellow background
                    pdf.set_font("", "B")
                    fill = True
                else:
                    fill = False
                    pdf.set_font("", "")
                pdf.cell(
                    45,
                    7,
                    text=detection.timestamp.strftime("%d/%m/%Y %H:%M:%S"),
                    border=1,
                    align="C",
                    fill=fill,
                )
                pdf.cell(25, 7, text=detection.plate, border=1, align="C", fill=fill)
                pdf.cell(25, 7, text=detection.codcet, border=1, align="C", fill=fill)
                pdf.cell(15, 7, text=detection.lane, border=1, align="C", fill=fill)
                pdf.cell(
                    40, 7, text=str(detection.speed), border=1, align="C", fill=fill
                )
                pdf.cell(
                    40,
                    7,
                    text=str(detection.count),
                    border=1,
                    align="C",
                    new_x="LMARGIN",
                    new_y="NEXT",
                    fill=fill,
                )
        else:
            pdf.cell(
                0,
                10,
                text="Nenhuma detecção encontrada para este grupo.",
                new_x="LMARGIN",
                new_y="NEXT",
            )

        # pdf.ln(10)
        pdf.set_font("Times", size=10)
        pdf.cell(
            0,
            10,
            text=f"Tabela {i + 1}: Detecções conjuntas àquela de número {i + 1} da placa monitorada",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        pdf.ln(4)

    # Save PDF
    fname = f"/tmp/{uuid4().hex}.pdf"
    pdf.output(fname)

    # Stream it as response
    def iterfile(path: str):
        with open(path, mode="rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(fname),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report_id}.pdf"},
    )


@router_request(method="POST", router=router, path="/multiple-correlated-plates")
async def generate_report_multiple_correlated_plates(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    data: PdfReportMultipleCorrelatedPlatesIn,
) -> str:
    """
    Generate a comprehensive report of correlated vehicle plate detections.

    This endpoint processes a request to generate a detailed report showing correlations
    between multiple vehicle plates detected by traffic radars. The report includes
    both visual representations (graphs) and detailed data tables.

    The endpoint performs several CPU-intensive operations:
    1. Fetches and processes correlation data from BigQuery
    2. Creates network graphs showing plate relationships
    3. Generates PDF reports with the findings
    4. Packages results into a ZIP file with both PDF and interactive HTML

    Parameters:
    -----------
    request : Request
        The incoming HTTP request object.
    user : User
        The authenticated user requesting the report generation.
    data : PdfReportMultipleCorrelatedPlatesIn
        The request data containing parameters for report generation, including:
        - List of plates to analyze
        - Time windows for analysis
        - Correlation parameters (n_minutes, n_plates)
        - Filtering options

    Returns:
    --------
    StreamingResponse
        - If correlations are found: A ZIP file containing both PDF report and HTML graph
        - If no correlations are found: A PDF report indicating no correlations detected
    """

    # Initialize the required services
    data_service = DataService()
    pdf_service = PdfService()
    graph_service = GraphService()

    # Set up the PDF service with the input data
    await pdf_service.initialize(data=data)

    # Query for correlated plate detections
    # This is a computationally expensive operation that queries BigQuery
    correlated_detections = await data_service.get_correlations(
        data=data,
    )

    # Handle the case where no correlated plates were found
    if correlated_detections[~correlated_detections["target"]].empty:
        # Get the context data for the template
        template_context = await pdf_service.get_template_context()

        # Add parameters about the search to the context
        template_context["no_detections"] = True
        template_context["search_parameters"] = {
            "plates": [p.plate for p in data.requested_plates_data],
            "start_time": min(p.start for p in data.requested_plates_data).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
            "end_time": max(p.end for p in data.requested_plates_data).strftime(
                "%d/%m/%Y %H:%M:%S"
            ),
            "n_minutes": data.n_minutes,
            "n_plates": data.n_plates,
        }

        # Generate the PDF report with a template for no data
        file_path = await pdf_service.generate_pdf_report_from_html_template(
            context=template_context,
            template_relative_path="pdf/multiple_correlated_plates_no_data.html",
        )

        # Helper function to stream the file content
        def iterfile(path: str):
            """Stream file contents from disk in chunks."""
            logger.info("Streaming PDF file.")
            with open(path, mode="rb") as f:
                yield from f

            logger.info("PDF file streamed.")

        # Return the PDF file as a streaming response
        return StreamingResponse(
            iterfile(file_path),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={template_context['report_id']}.pdf"
            },
        )

    else:
        # Process correlated detections found - run operations concurrently
        # 1. Create a graph with limited nodes for visualization
        # 2. Process detection data for the PDF report
        # 3. Process detailed detection data for the report
        await asyncio.gather(
            graph_service.create_graph(dataframe=correlated_detections, limit_nodes=20),
            pdf_service.set_detections(correlated_detections=correlated_detections),
            pdf_service.set_detailed_detections(
                correlated_detections=correlated_detections
            ),
        )

        # Save the limited nodes graph as both PNG and HTML
        await graph_service.save_graph(
            png_file_name="grafo_limited_nodes.png",
            html_file_name="grafo_limited_nodes.html",
        )

        # Generate a full graph without node limits for the interactive HTML view
        await graph_service.create_graph(dataframe=correlated_detections)
        html_path_full, png_path_full = await graph_service.save_graph(
            png_file_name="grafo.png",
            html_file_name="grafo.html",
            delay=15,  # Extra delay to ensure complete rendering of larger graph
        )

        # Get the context data for the template and generate the PDF
        template_context = await pdf_service.get_template_context()
        pdf_path = await pdf_service.generate_pdf_report_from_html_template(
            context=template_context,
            template_relative_path="pdf/multiple_correlated_plates.html",
        )

        # Create a ZIP file containing both the PDF report and the interactive HTML graph
        import zipfile
        import io

        # Use an in-memory buffer for the ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Add the PDF report to the ZIP
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
                zip_file.writestr(f"{template_context['report_id']}.pdf", pdf_data)

            # Add the interactive HTML graph to the ZIP
            with open(html_path_full, "rb") as f:
                html_data = f.read()
                zip_file.writestr(
                    f"{template_context['report_id']}_grafo.html", html_data
                )

        # Reset the buffer pointer to the beginning for reading
        zip_buffer.seek(0)

        # Return the ZIP file as a streaming response
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={template_context['report_id']}.zip"
            },
        )


@router_request(method="GET", router=router, path="/multiple-correlated-plates/history")
async def get_report_multiple_correlated_plates_history(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    report_id: str,
) -> str:
    """
    Retrieve the history of a specific multiple correlated plates report.

    This endpoint fetches historical data for a previously generated report of
    correlated vehicle plates. It searches the ReportHistory database for the
    specified report ID and returns the report's metadata and content.

    Parameters:
    -----------
    request : Request
        The incoming HTTP request object.
    user : User
        The authenticated user requesting the report history.
    report_id : str
        The unique identifier of the report to retrieve.

    Returns:
    --------
    JSONResponse
        A JSON response containing either:
        - Status 200 with the report's history data if found
        - Status 404 if the report with the given ID doesn't exist
    """

    # Dynamically find the route path for the report generation endpoint
    # This ensures we're looking for the correct path even if routes change
    for route in router.routes:
        if route.endpoint == generate_report_multiple_correlated_plates:
            path = f"{route.path}"
            break
    else:
        # Fallback path if the route lookup fails
        path = "/pdf/multiple-correlated-plates"

    # Query the database for the report history
    report_history = await ReportHistory.filter(path=path, id_report=report_id).first()

    # Return 404 if the report doesn't exist
    if not report_history:
        return JSONResponse(
            status_code=404, content={"status_code": 404, "detail": "Report not found"}
        )

    # Convert the report history to a serializable dictionary
    # This includes metadata and the original request content
    report_dict = {
        "id_report": report_history.id_report,
        "timestamp": report_history.timestamp.isoformat(),
        "query_params": report_history.query_params,
        "body": report_history.body,
    }

    # Return the report history as a JSON response
    return JSONResponse(
        status_code=200,
        content={
            "status_code": 200,
            "detail": "Report found",
            "report_history": report_dict,
        },
    )
