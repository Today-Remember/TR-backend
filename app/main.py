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
from openai import OpenAI
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))




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

# @app.get("/")
# def read_root():
#     logging.info("Root endpoint called")
#     return {"name": "1234"}

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




@app.post("/detail")
async def generated_content(diary_content: str = Form(...)):
 
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": f"{diary_content} 라는 일기에 어울리는 이모지를 최대 4개까지 한줄에 출력해줘"}
    ],
    temperature=0.8,
    )
    generated_content =f"{diary_content} "+completion.choices[0].message.content

    response_html = f"<html><body><p>{generated_content}</p></body></html>"
    return HTMLResponse(content=response_html)


@app.get("/config")
def config_endpoint():
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    return {"OPENAI_API_KEY": openai.api_key}
    

@app.get("/")
async def main():
    content = """<body><form action="/detail" method="post">
                <h1>일기 입력하기</h1>
                <input type="text" name="diary_content">
                <button type="submit">일기 작성 완료</button>
                </form></body>"""
    return HTMLResponse(content=content)

