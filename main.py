from fastapi import FastAPI, UploadFile, File, HTTPException, status, Form
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.templating import Jinja2Templates
import uuid, os, streaming_form_data, aiofiles
from streaming_form_data import StreamingFormDataParser
from streaming_form_data.targets import FileTarget, ValueTarget
from streaming_form_data.validators import MaxSizeValidator
from starlette.requests import ClientDisconnect

# disable the docs
# disable the redoc
app = FastAPI(
    MAX_FILE_SIZE= 50 * 1024 *1024
    # docs_url=None, 
    # redoc_url=None
    )

templates = Jinja2Templates(directory="templates")
# app.config.MAX_UPLOAD_SIZE = 
# Directory to store uploaded images
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 1024 * 1024 * 1024 * 4  # = 4GB
MAX_REQUEST_BODY_SIZE = MAX_FILE_SIZE + 1024
CHUNK_SIZE = 1024 # 4 MB

# chuck
class MaxBodySizeException(Exception):
    def __init__(self, body_len: str):
        self.body_len = body_len

class MaxBodySizeValidator:
    def __init__(self, max_size: int):
        self.body_len = 0
        self.max_size = max_size

    def __call__(self, chunk: bytes):
        self.body_len += len(chunk)
        if self.body_len > self.max_size:
            raise MaxBodySizeException(body_len=self.body_len)
        
@app.post("/upload")
async def upload_file(request: Request):
    try:
        # Set chunk size limit to 5MB
        chunk_size_limit = 5 * 1024 * 1024

        # Initialize total size counter
        total_size = 0

        # Process request body in chunks
        # async for chunk in request.stream().iter_any(chunk_size_limit):
        #     # Perform processing on each chunk
        #     # Replace this with your own logic
        #     print(f"Processing chunk with size: {len(chunk)} bytes")

        #     # Update total size counter
        #     total_size += len(chunk)

        #     # Check if total size exceeds limit
        #     if total_size > chunk_size_limit:
        #         raise HTTPException(status_code=400, detail="File size exceeds chunk limit")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "File upload successful"}

 
@app.post('/chuxk-upload')
async def upload(request: Request):
    body_validator = MaxBodySizeValidator(MAX_REQUEST_BODY_SIZE)
    filename = request.headers.get('Filename')
    
    if not filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail='Filename header is missing')
    try:
        filepath = os.path.join('./', os.path.basename(filename)) 
        file_ = FileTarget(filepath, validator=MaxSizeValidator(MAX_FILE_SIZE))
        data = ValueTarget()
        parser = StreamingFormDataParser(headers=request.headers)
        parser.register('file', file_)
        parser.register('data', data)
        
        async for chunk in request.stream():
            body_validator(chunk)
            parser.data_received(chunk)
    except ClientDisconnect:
        print("Client Disconnected")
    except MaxBodySizeException as e:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
           detail=f'Maximum request body size limit ({MAX_REQUEST_BODY_SIZE} bytes) exceeded ({e.body_len} bytes read)')
    except streaming_form_data.validators.ValidationError:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
            detail=f'Maximum file size limit ({MAX_FILE_SIZE} bytes) exceeded') 
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail='There was an error uploading the file') 
   
    if not file_.multipart_filename:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail='File is missing')

    print(data.value.decode())
    print(file_.multipart_filename)
        
    return {"message": f"Successfuly uploaded {filename}"}


def save_uploaded_file(file: UploadFile, save_path: Path):
    with open(save_path,"wb") as buffer:
        buffer.write(file.file.read())
        buffer.close()

@app.get('/')
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/image/{img}")
async def get_image(img: str):
    dirname = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
    # Return the image as a FileResponse
    return FileResponse(f"{dirname}\{UPLOAD_DIR}\{img}")

@app.post("/upload/")
async def upload_image(request :Request,file: UploadFile = File(...)):
    # Create the uploads directory if it doesn't exist
    save_dir = Path(UPLOAD_DIR)
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save the uploaded image
    ext = file_extension = os.path.splitext(file.filename)[1]
    file_path = f'{save_dir}/{uuid.uuid1()}{ext}'
    save_uploaded_file(file, file_path)
    base = request.base_url
    # Return the link to the uploaded image
    return {"file_link": f"{base}image/{uuid.uuid1()}{ext}"}
