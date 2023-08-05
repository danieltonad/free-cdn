from fastapi import FastAPI, UploadFile, File
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.templating import Jinja2Templates
import uuid, os

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory="templates")

# Directory to store uploaded images
UPLOAD_DIR = "uploads"


def save_uploaded_file(file: UploadFile, save_path: Path):
    with open(save_path,"wb") as buffer:
        buffer.write(file.file.read())
        buffer.close()

@app.get('/')
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    # Create the uploads directory if it doesn't exist
    save_dir = Path(UPLOAD_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded image
    ext = file_extension = os.path.splitext(file.filename)[1]
    file_path = f'{save_dir}/{uuid.uuid1()}{ext}'
    print(file_path)
    save_uploaded_file(file, file_path)
    base = Request.base_url
    # Return the link to the uploaded image
    return {"file_link": f"{base}{UPLOAD_DIR}/{file.filename}"}
