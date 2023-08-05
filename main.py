from fastapi import FastAPI, UploadFile, File
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.templating import Jinja2Templates

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Directory to store uploaded images
UPLOAD_DIR = "uploads"


def save_uploaded_file(file: UploadFile, save_path: Path):
    with save_path.open("wb") as buffer:
        buffer.write(file.file.read())


@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    # Create the uploads directory if it doesn't exist
    save_dir = Path(UPLOAD_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded image
    file_path = save_dir / file.filename
    save_uploaded_file(file, file_path)

    # Return the link to the uploaded image
    return {"file_link": f"/{UPLOAD_DIR}/{file.filename}"}
