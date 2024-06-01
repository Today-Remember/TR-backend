#init TR-backend repository
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse


app = FastAPI()

origins = [
    "http://localhost:3000",  # React 개발 서버 주소
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextData(BaseModel):
    text: str

@app.post("/text")
async def receive_text(data: TextData):
    global received_text
    received_text = data.text
    return {"received_text": received_text}

rtext = "test sentence!!! fastapi에서 전송한 문장"

@app.get("/text", response_class=JSONResponse)  #프론트로 전송
async def get_text():
    return {"received_text": rtext}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return f"""
    <html>
        <head>
            <title>Received Text</title>
        </head>
        <body>
            <h1>Received Text</h1>
            <p>{received_text}</p>
        </body>
    </html>
    """