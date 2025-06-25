from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..dependencies import gettempdir

router = APIRouter(
    prefix="/api/image",
    tags=["image"],
)

def get_image_files(tempdir: Path = Depends(gettempdir)):
    image_dir = tempdir / "images"
    if not image_dir.is_dir():
        return []
    # Sort files to ensure consistent order
    files = sorted([f for f in image_dir.iterdir() if f.is_file()])
    return files

@router.get("/number")
async def get_image_number(image_files: list[Path] = Depends(get_image_files)):
    """
    Get the total number of images.
    """
    return {"number": len(image_files)}

@router.get("")
async def get_image(id: int, image_files: list[Path] = Depends(get_image_files)):
    """
    Get an image by its ID (1-based index).
    """
    if not image_files or not 1 <= id <= len(image_files):
        raise HTTPException(status_code=404, detail="Image not found")
    
    image_path = image_files[id - 1]
    return FileResponse(image_path)