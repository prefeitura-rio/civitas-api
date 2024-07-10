# -*- coding: utf-8 -*-
import concurrent.futures
import re
from os import getenv
from pathlib import Path
from typing import List

import pandas as pd
import requests
from loguru import logger
from pydantic import BaseModel, Field, validator

for env in ["CIVITAS_API_BASE_URL", "CIVITAS_API_USERNAME", "CIVITAS_API_PASSWORD"]:
    if not getenv(env):
        raise ValueError(f"Environment variable {env} is required")

CIVITAS_API_BASE_URL = getenv("CIVITAS_API_BASE_URL")
CIVITAS_API_USERNAME = getenv("CIVITAS_API_USERNAME")
CIVITAS_API_PASSWORD = getenv("CIVITAS_API_PASSWORD")


class Plate(BaseModel):
    plate: str = Field(...)

    @validator("plate")
    def validate_plate(cls, value: str):
        # Ensure the plate is upper case
        value = value.upper()

        # Ensure the plate has the correct format
        pattern = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")
        if not pattern.match(value):
            raise ValueError(
                "plate must have exactly 7 characters: "
                "first 3 letters, 4th digit, 5th letter or digit, last 2 digits."
                f'Got: "{value}"'
            )

        return value


def authenticate_with_civitas_api() -> str:
    response = requests.post(
        f"{CIVITAS_API_BASE_URL}/auth/token",
        headers={
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "username": CIVITAS_API_USERNAME,
            "password": CIVITAS_API_PASSWORD,
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["access_token"]


def load_csv(file_path: Path | str) -> List[Plate]:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    try:
        df = pd.read_csv(file_path)
    except Exception as exc:
        raise ValueError(f"Failed to read file: {file_path}") from exc
    if "placa" not in df.columns:
        raise ValueError("Column 'placa' not found in file")
    plates = df["placa"].unique().tolist()
    return [Plate(plate=plate) for plate in plates]


def add_single_plate(placa: str, token: str, additional_info: dict = None):
    additional_info = additional_info or {}
    try:
        response = requests.post(
            f"{CIVITAS_API_BASE_URL}/cars/monitored",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json={
                "plate": placa,
                "additional_info": additional_info,
            },
        )
        if response.status_code == 409:
            logger.info(f"Placa {placa} já está sendo monitorada.")
        else:
            response.raise_for_status()
            logger.info(f"Placa {placa} adicionada com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao adicionar a placa {placa}: {e}")


def add_plates(file_path: Path | str, additional_info: dict = None):
    plates = load_csv(file_path)
    token = authenticate_with_civitas_api()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for plate in plates:
            executor.submit(add_single_plate, plate.plate, token, additional_info)
    logger.info(f"{len(plates)} placas adicionadas.")


def remove_single_plate(placa: str, token: str):
    try:
        response = requests.delete(
            f"{CIVITAS_API_BASE_URL}/cars/monitored/{placa}",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        if response.status_code == 404:
            logger.info(f"Placa {placa} não está sendo monitorada.")
        else:
            response.raise_for_status()
            logger.info(f"Placa {placa} removida com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao remover a placa {placa}: {e}")


def remove_plates(file_path: Path | str):
    plates = load_csv(file_path)
    token = authenticate_with_civitas_api()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for plate in plates:
            executor.submit(remove_single_plate, plate.plate, token)
    logger.info(f"{len(plates)} placas removidas.")


def get_all_monitored_plates(token: str = None, page_size: int = 50):
    token = token or authenticate_with_civitas_api()
    current_page = 1
    last_page = float("inf")
    monitored_plates = []
    while current_page <= last_page:
        response = requests.get(
            f"{CIVITAS_API_BASE_URL}/cars/monitored?page={current_page}&size={page_size}",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )
        response.raise_for_status()
        data = response.json()
        last_page = data["pages"]
        monitored_plates.extend(data["items"])
        current_page += 1
    return monitored_plates


def update_single_plate(placa: str, token: str, body: dict):
    try:
        response = requests.put(
            f"{CIVITAS_API_BASE_URL}/cars/monitored/{placa}",
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json=body,
        )
        if response.status_code == 404:
            logger.info(f"Placa {placa} não está sendo monitorada.")
        else:
            response.raise_for_status()
            logger.info(f"Placa {placa} atualizada com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao atualizar a placa {placa}: {e}")
