from fastapi import FastAPI, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import pymysql
import shutil
from pathlib import Path
import logging
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
import openai
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in the environment variables")

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

# 데이터베이스 오류 자세히 확인하기 위한 로깅 설정
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()



# CORS 설정
origins = ["*"]  # React 개발 서버 URL, * 표시하면 모두 허용

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # cookie 포함 여부를 설정한다. 기본은 False
    allow_methods=["*"],     # 허용할 method를 설정할 수 있으며, 기본값은 'GET'이다.
    allow_headers=["*"],     # 허용할 http header 목록을 설정할 수 있으며 Content-Type, Accept, Accept-Language, Content-Language은 항상 허용된다.
)

def db_conn():
    try:
        connection = pymysql.connect(
            host='10.10.0.100',
            port=3306,
            user='team13',
            password='1234',
            database='team13',
            charset='utf8',
            cursorclass=pymysql.cursors.DictCursor,
        )
        logging.info("Database connection successful")
        return connection
    except pymysql.MySQLError as e:
        logging.error(f"Error connecting to the database: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

@app.get("/")
def read_root():
    logging.info("Root endpoint called")
    return {"name": "1234"}

class SignUpData(BaseModel):
    id: str
    name: str
    password: str
    email: str

@app.post("/signup")
async def register(signup_data: SignUpData):

    # 데이터 베이스에 저장 작업
    db = db_conn()
    try:
        with db.cursor() as cursor:
            sql = '''
                INSERT INTO Member (id, name, password, email) 
                VALUES (%s, %s, UPPER(SHA1(UNHEX(SHA1(%s)))), %s)
            '''
            cursor.execute(sql, (
                signup_data.id,
                signup_data.name,
                signup_data.password,
                signup_data.email
            ))
            db.commit()

    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")
    finally:
        db.close()
    
    return {"success": "회원가입이 완료되었습니다."}


class TextData(BaseModel):
    text: str


@app.post("/text")
async def receive_text(data: TextData):
    logging.info("Received text: %s", data.text)
    try:
        response = openai.Completion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": f"{data.text} 라는 일기에 어울리는 이모지를 최대 4개까지 한줄에 출력해줘"}
            ],
            temperature=0.8,
        )
        received_text = data.text + " " + response.choices[0].message["content"]
        logging.info("Generated response: %s", received_text)
        return {"received_text": received_text}
    except openai.error.OpenAIError as e:
        logging.error("OpenAI API request failed: %s", e)
        raise HTTPException(status_code=500, detail=f"OpenAI API request failed: {e}")
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.get("/aitext")
async def get_text():
    return {"received_text": "default text"}



# @app.get("/config")
# def config_endpoint():
#     return os.environ.get("OPENAI_API_KEY")

# @app.get("/config")
# def config_endpoint():
#     openai_api_key = os.environ.get("OPENAI_API_KEY")
#     return {"OPENAI_API_KEY": openai.api_key}
