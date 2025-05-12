# -*- coding: utf-8 -*-
import asyncio
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fpdf import FPDF
from pendulum import now

from app import config
from app.decorators import router_request
from app.dependencies import is_user
from app.models import ReportHistory, User
from app.pydantic_models import PdfReportCorrelatedPlatesIn, PdfReportMultipleCorrelatedPlatesIn
from app.services.pdf.multiple_correlated_plates import DataService, GraphService, PdfService
from app.utils import generate_report_id, generate_pdf_report_from_html_template

from loguru import logger

class CustomPDF(FPDF):
    def __init__(self, report_id: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._report_id = report_id

    def header(self):
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
                pdf.cell(
                    25, 7, text=detection.camera_numero, border=1, align="C", fill=fill
                )
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
    
    data_service = DataService()
    pdf_service = PdfService()
    graph_service = GraphService()

    await pdf_service.initialize(data=data)
    
    correlated_detections = await data_service.get_correlations(
        data=data,
    )

    if correlated_detections.empty:
        template_context = await pdf_service.get_template_context()
        
        template_context["no_detections"] = True
        template_context["search_parameters"] = {
            "plates": [p.plate for p in data.requested_plates_data],
            "start_time": min(p.start for p in data.requested_plates_data).strftime("%d/%m/%Y %H:%M:%S"),
            "end_time": max(p.end for p in data.requested_plates_data).strftime("%d/%m/%Y %H:%M:%S"),
            "n_minutes": data.n_minutes,
            "n_plates": data.n_plates
        }
        
        file_path = await generate_pdf_report_from_html_template(
            context=template_context,
            template_relative_path="pdf/multiple_correlated_plates_no_data.html",
        )
        
        def iterfile(path: str):
            logger.info(f"Streaming PDF file.")
            with open(path, mode="rb") as f:
                yield from f
                
            logger.info(f"PDF file streamed.")

        return StreamingResponse(
            iterfile(file_path),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={template_context['report_id']}.pdf"},
        )
        
    else:
        await asyncio.gather(
            graph_service.create_graph(dataframe=correlated_detections, limit_nodes=20),
            pdf_service.set_detections(correlated_detections=correlated_detections),
            pdf_service.set_detailed_detections(correlated_detections=correlated_detections)
        )
        await graph_service._save_graph(png_file_name="grafo_limited_nodes.png", html_file_name="grafo_limited_nodes.html")
        
        # generate graph without limiting nodes
        await graph_service.create_graph(dataframe=correlated_detections)
        html_path_full, png_path_full = await graph_service._save_graph(png_file_name="grafo.png", html_file_name="grafo.html")
        
        template_context = await pdf_service.get_template_context()
        
        pdf_path = await generate_pdf_report_from_html_template(
            context=template_context,
            template_relative_path="pdf/multiple_correlated_plates.html",
        )
        
        # Create ZIP file with both PDF and HTML
        import zipfile
        import io
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add PDF file
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
                zip_file.writestr(f"{template_context['report_id']}.pdf", pdf_data)
            
            # Add HTML file
            with open(html_path_full, 'rb') as f:
                html_data = f.read()
                zip_file.writestr(f"{template_context['report_id']}_grafo.html", html_data)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={template_context['report_id']}.zip"},
        )


@router_request(method="GET", router=router, path="/multiple-correlated-plates/history")
async def get_report_multiple_correlated_plates_history(
    request: Request,
    user: Annotated[User, Depends(is_user)],
    report_id: str,
) -> str:
    
    for route in router.routes:
        if route.endpoint == generate_report_multiple_correlated_plates:
            path = f"{route.path}"
            break
    else:
        path = "/pdf/multiple-correlated-plates"

    report_history = await ReportHistory.filter(
        path=path,
        id_report=report_id
    ).first()
    
    if not report_history:
        return JSONResponse(
            status_code=404,
            content={"status_code": 404, "detail": "Report not found"}
        )
    
    report_dict = {
        "id_report": report_history.id_report,
        "timestamp": report_history.timestamp.isoformat(),
        "query_params": report_history.query_params,
        "body": report_history.body
    }
    
    return JSONResponse(
        status_code=200,
        content={
            "status_code": 200,
            "detail": "Report found",
            "report_history": report_dict
        }
    )
    
    