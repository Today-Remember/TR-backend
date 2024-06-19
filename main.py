from fastapi import FastAPI, Form, Query, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from typing import Optional
import pymysql
import shutil
from pathlib import Path
import logging
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
import os
from dotenv import load_dotenv
from openai import OpenAIError
import openai
from datetime import timedelta, datetime
from jose import jwt
import secrets

app = FastAPI()

# .env 파일 로드
dotenv_path = "app/.env"
load_dotenv(dotenv_path)

# API 키 가져오기
api_key = os.getenv("OPENAI_API_KEY")

# API 키 설정
openai.api_key = api_key


# 데이터베이스 오류 자세히 확인하기 위한 로깅 설정
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# CORS 설정
origins = ["*"]  # React 개발 서버 URL, * 표시하면 모두 허용

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 허용할 출처를 설정
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
            charset='utf8mb4',
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

class LoginData(BaseModel):
    id: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"

@app.post("/login")
async def login(login_data: LoginData):
    if not login_data.id or not login_data.password:
        raise HTTPException(status_code=400, detail="ID와 비밀번호를 모두 입력해주세요")

    db = db_conn()
    try:
        with db.cursor() as cursor:
            sql = '''
                SELECT * FROM Member 
                WHERE id = %s AND password = UPPER(SHA1(UNHEX(SHA1(%s))))
            '''
            cursor.execute(sql, (
                login_data.id,
                login_data.password
            ))
            result = cursor.fetchone()
            if result:
                data = {
                    "sub": login_data.id,
                    "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                }
                access_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM) # 토큰 생성
                return {
                    "user": login_data.id,
                    "success": "로그인 성공",
                    "token": access_token,
                    "token_type": "bearer"
                }
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
    except pymysql.MySQLError as e:
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")
    finally:
        db.close()


@app.post("/viewaitext")
async def generated_content(diary_content: str = Form(...)):

    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": f"{diary_content} 라는 일기에 어울리는 이모지를 최대 4개까지 한줄에 출력해줘"}
    ],
    temperature=0.8,
    )
    generated_content =f"{diary_content} "+completion.choices[0].message.content
    return generated_content


class DiaryEntry(BaseModel):
    text: str
    user_id: str

@app.post("/detail")
async def generated_content(entry: DiaryEntry):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"{entry.text} 라는 일기에 어울리는 이모지를 최대 4개까지 한 줄에 출력해줘. 이모지만 출력해야해."}
            ],
            temperature=0.8
        )
        received_text = entry.text + response.choices[0].message['content'].strip()
        
    except OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API 요청 실패: {e}")

    db = db_conn()

    try:
        with db.cursor() as cursor:
            sql = '''
                INSERT INTO Diary (member_id, detail) 
                VALUES (%s, %s)
            '''
            cursor.execute(sql, (entry.user_id, received_text))
            db.commit()
    except pymysql.MySQLError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")
    finally:
        db.close()

    return {"received_text": received_text}

class data(BaseModel):
    date: str
    member_id: str

@app.delete("/delete")
async def delete_diary(Data: data):
    db = db_conn()
    try:
        with db.cursor() as cursor:
            sql = '''DELETE FROM Diary WHERE member_id = %s AND DATE(date) = %s'''
            cursor.execute(sql, (Data.member_id, Data.date))
            db.commit()
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="해당 조건에 맞는 일기를 찾을 수 없습니다.")
    except pymysql.MySQLError as e:
        logging.error(f"Database operation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")
    finally:
        db.close()

    return {"success": "일기가 삭제되었습니다."}



@app.get("/detail")
async def get_details(date: str = Query(...), member_id: str = Query(...)):
    db = db_conn()
    try:
        with db.cursor() as cursor:
            sql = '''SELECT * FROM Diary WHERE DATE(date) = (%s) AND member_id = %s'''
            cursor.execute(sql, (date, member_id))
            results = cursor.fetchall()
            if results:
                return {"일기": results}
            else:
                raise HTTPException(status_code=404, detail="날짜에 해당하는 일기 찾기 실패")
    except pymysql.MySQLError as e:
        logging.error(f"Database operation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database operation failed: {e}")
    finally:
        db.close()


@app.get("/config")
def config_endpoint():
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    return {api_key}
    