'''
Author: hibana2077 hibana2077@gmail.com
Date: 2024-05-06 21:09:40
LastEditors: hibana2077 hibana2077@gmaill.com
LastEditTime: 2024-06-13 15:49:11
FilePath: \src\backend\main.py
Description: Here is the main file for the FastAPI server.
'''
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import redis
import os
import time
import uvicorn
import requests
from fastapi.middleware.cors import CORSMiddleware

HOST = os.getenv("HOST", "127.0.0.1")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Initialize the counter
    pass

@app.get("/")
async def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=8081) # In docker need to change to 0.0.0.0