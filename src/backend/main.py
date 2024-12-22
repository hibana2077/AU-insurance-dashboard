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
import os
import time
import pandas as pd
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

@app.get("/data")
async def get_data():
    xlsx_url = "https://www.apra.gov.au/sites/default/files/2024-08/%5B20240820%5D%20Quarterly%20general%20insurance%20institution-level%20statistics%20database%20%28historical%20data%29%20from%20September%202017%20to%20June%202023.xlsx"
    df_table_1a = pd.read_excel(xlsx_url, sheet_name="Table 1a")

    df_cleaned = df_table_1a.iloc[2:]
    df_cleaned.columns = df_table_1a.iloc[2]
    df_cleaned = df_cleaned.iloc[1:]
    return JSONResponse(content=df_cleaned.to_json())

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=8081) # In docker need to change to 0.0.0.0