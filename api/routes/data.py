# HEMA - Home Energy Management Assistant
# Copyright (C) 2024-2026 Wooyoung Jung, HUBS Lab, University of Arizona
# Licensed under GPL-3.0. See LICENSE file for details.
# api/routes/data.py
"""Data management endpoints for the energy analysis API."""
import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from pydantic import BaseModel

from api.dependencies import get_graph_runner
from agents.graph.builder import HEMAGraphRunner
from utils.logger import setup_logger

logger = setup_logger()
router = APIRouter(prefix="/data", tags=["data"])

# Data directories
DATA_DIR = "data"
ENERGY_DATA_DIR = os.path.join(DATA_DIR, "home_power")
RATE_DATA_DIR = os.path.join(DATA_DIR, "utility_rate")


class FileInfo(BaseModel):
    """Information about a data file."""
    filename: str
    path: str
    size_bytes: int
    file_type: str  # "energy" or "rate"


class FileListResponse(BaseModel):
    """Response for listing available files."""
    energy_files: List[FileInfo]
    rate_files: List[FileInfo]


class UploadResponse(BaseModel):
    """Response for file upload."""
    success: bool
    filename: str
    path: str
    message: str


def _get_file_info(filepath: str, file_type: str) -> FileInfo:
    """Get info about a file."""
    return FileInfo(
        filename=os.path.basename(filepath),
        path=filepath,
        size_bytes=os.path.getsize(filepath),
        file_type=file_type
    )


@router.get("/files", response_model=FileListResponse)
async def list_data_files() -> FileListResponse:
    """
    List all available data files.

    Returns:
        FileListResponse with lists of energy and rate files
    """
    logger.info("Listing data files")

    energy_files = []
    rate_files = []

    # List energy data files
    if os.path.exists(ENERGY_DATA_DIR):
        for filename in os.listdir(ENERGY_DATA_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(ENERGY_DATA_DIR, filename)
                energy_files.append(_get_file_info(filepath, "energy"))

    # List rate data files
    if os.path.exists(RATE_DATA_DIR):
        for filename in os.listdir(RATE_DATA_DIR):
            if filename.endswith(".csv"):
                filepath = os.path.join(RATE_DATA_DIR, filename)
                rate_files.append(_get_file_info(filepath, "rate"))

    return FileListResponse(energy_files=energy_files, rate_files=rate_files)


@router.post("/upload/energy", response_model=UploadResponse)
async def upload_energy_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload an energy consumption CSV file.

    Args:
        file: CSV file to upload

    Returns:
        UploadResponse with upload result
    """
    logger.info(f"Uploading energy file: {file.filename}")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Ensure directory exists
    os.makedirs(ENERGY_DATA_DIR, exist_ok=True)

    # Save the file
    filepath = os.path.join(ENERGY_DATA_DIR, file.filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return UploadResponse(
            success=True,
            filename=file.filename,
            path=filepath,
            message=f"Energy file '{file.filename}' uploaded successfully"
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.post("/upload/rate", response_model=UploadResponse)
async def upload_rate_file(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a utility rate CSV file.

    Args:
        file: CSV file to upload

    Returns:
        UploadResponse with upload result
    """
    logger.info(f"Uploading rate file: {file.filename}")

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    # Ensure directory exists
    os.makedirs(RATE_DATA_DIR, exist_ok=True)

    # Save the file
    filepath = os.path.join(RATE_DATA_DIR, file.filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return UploadResponse(
            success=True,
            filename=file.filename,
            path=filepath,
            message=f"Rate file '{file.filename}' uploaded successfully"
        )
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.delete("/files/{file_type}/{filename}")
async def delete_file(file_type: str, filename: str) -> dict:
    """
    Delete a data file.

    Args:
        file_type: Type of file ("energy" or "rate")
        filename: Name of the file to delete

    Returns:
        Success message
    """
    logger.info(f"Deleting {file_type} file: {filename}")

    if file_type == "energy":
        filepath = os.path.join(ENERGY_DATA_DIR, filename)
    elif file_type == "rate":
        filepath = os.path.join(RATE_DATA_DIR, filename)
    else:
        raise HTTPException(status_code=400, detail="file_type must be 'energy' or 'rate'")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")

    try:
        os.remove(filepath)
        return {"success": True, "message": f"File '{filename}' deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")
