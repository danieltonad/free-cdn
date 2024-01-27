from fastapi import FastAPI, UploadFile, File, HTTPException, status, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
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
from fastapi.middleware.cors import CORSMiddleware
import boto3

# disable the docs
# disable the redoc
app = FastAPI(
    MAX_FILE_SIZE= 50 * 1024 *1024
    # docs_url=None, 
    # redoc_url=None
    )
origins = [
    "https://conju.me",
    "http://localhost",
    "http://127.0.0.1:5500",
    "http://localhost:8000",
    "http://127.0.0.1:8080",
]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

templates = Jinja2Templates(directory="templates")
# app.config.MAX_UPLOAD_SIZE = 
# Directory to store uploaded images
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 1024 * 1024 * 1024 * 4  # = 4GB
MAX_REQUEST_BODY_SIZE = MAX_FILE_SIZE + 1024
CHUNK_SIZE = 1024 # 4 MB
s3 = boto3.client("s3", aws_access_key_id="", aws_secret_access_key="")
BUCKET = "conju-me-sliders"
FOLDER = "tmp/"

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

@app.get("/intialize_upload/{file_name}")
async def initialize_upload(file_name: str):
    return initiate_multipart_upload(file_name)

@app.post("/upload_chunk/{file_id}")
async def upload_chunk(file_id: str, chunk: UploadFile = File(...)):
    try:
        # Read the content of the received chunk
        chunk_content = await chunk.read()
        # await write_s3_chunck(chunk=chunk_content, file_name=file_id+'.mp4', part=part, upload_id=upload_id)
        write_stream_to_temp(chunk=chunk_content, temp_path=f'{file_id}.mp4')

        return JSONResponse(content={"message": "Chunk received successfully"}, status_code=200)

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get('/s3_upload/{file}')
async def s3_upload_file(file: str):
    file_path = Path('/tmp/' + file)
    await upload_file_temp_to_s3(file=file_path, file_name=file)
    return "Done init"

async def upload_file_temp_to_s3(file: Path, file_name: str):
    key = FOLDER + file_name
    response = s3.upload_file(
        file,
        Bucket=BUCKET,
        Key=key
    )
    print(response)
    return response
  
def initiate_multipart_upload(file_name):
    key = FOLDER + file_name
    response = s3.create_multipart_upload(
        Bucket=BUCKET,
        Key=key
    )
    return response['UploadId']


def write_stream_to_temp(chunk, temp_path):
    file_path = Path(f'/tmp/{temp_path}')
    if file_path.exists():
        with open(file_path, 'ab') as temp_file:
            print("Opened file directory:", os.path.dirname(os.path.abspath(temp_file.name)))
            temp_file.write(chunk)
            temp_file.close()
    else:
        os.makedirs('/tmp/', exist_ok=True)
        with open(file_path, 'wb') as temp_file:
            temp_file.write(chunk)
            temp_file.close()
        

@app.get("/fetch_file/{file_id}")
async def combine_chunks(file_id: str):
    video_path = f"/tmp/{file_id}"  # Replace with the actual path to your video file
    def generate():
        buffer_size = 1 * 1024 * 1024  # 4MB buffer size
        with open(video_path, "rb") as video_file:
            while True:
                chunk = video_file.read(buffer_size)
                if not chunk:
                    video_file.close()
                    break
                yield chunk
    try:
        return StreamingResponse(generate(), media_type="video/mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/delete_file/{file_id}")
async def delete_chunks(file_id: str):
    try:
        video_path = f"/tmp/{file_id}"  # Replace with the actual path to your video file
        return os.remove(video_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



def save_uploaded_file(file: UploadFile, save_path: Path):
    with open(save_path,"wb") as buffer:
        buffer.write(file.file.read())
        buffer.close()

@app.get('/')
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get('/test')
async def test_temp(request: Request):
    return templates.TemplateResponse("axios.html", {"request": request})

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
