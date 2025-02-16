from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

import requests
import json
from db_control import crud, mymodels_MySQL
from typing import List
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

# MySQLのテーブル作成
from db_control.create_tables_MySQL import init_db

# # アプリケーション初期化時にテーブルを作成
init_db()

class Item(BaseModel):
    trd_id: int
    prd_id: int
    prd_code: str
    prd_name: str
    prd_price: int
    tax_cd: str

class TotalAmountUpdate(BaseModel):
    trd_id: int
    total_amt: int
    ttl_amt_ex_tax: int

class TaxSchema(BaseModel):
    id: int
    code: str
    name: str
    percent: float

    @field_validator("percent", mode="before")
    @classmethod
    def convert_decimal(cls, value):
        if isinstance(value, Decimal):
            return float(value)  # Decimal を float に変換
        return value

app = FastAPI()

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def index():
    return {"message": "FastAPI top page!"}


@app.get("/search")
def search_one_item(code: str = Query(...)):
    result = crud.myselect(mymodels_MySQL.Master, code)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    result_obj = json.loads(result)
    return result_obj[0] if result_obj else None


@app.post("/purchases")
def insert_trade():
    now = datetime.now(ZoneInfo("Asia/Tokyo"))

    trade_data = {
        "emp_cd": "9999999999",
        "store_cd": "30",
        "pos_no": "90",
        "total_amt": 0,
        "datetime": now,
        "ttl_amt_ex_tax": 0
    }

    new_trd_id = crud.mytrade(mymodels_MySQL.Purchases, trade_data)

    # 挿入に失敗した場合は None が返る想定なので、その場合はエラーにする
    if new_trd_id is None:
        raise HTTPException(status_code=400, detail="Failed to insert purchase record")

    # 挿入成功したら trd_id だけを返却
    return {"trd_id": new_trd_id}


@app.post("/purchase_details")
def insert_item(items: List[Item]):
    values_list = [item.model_dump() for item in items]
    for values in values_list:
        crud.myinsert(mymodels_MySQL.PurchaseDetails, values)

    return {
        "message": "Success",
    }

@app.put("/purchases")
def update_total_amt(data: TotalAmountUpdate):
    values = data.model_dump()

    # データ更新
    update_result = crud.myupdate(mymodels_MySQL.Purchases, values)

    if update_result == "error":
        raise HTTPException(status_code=400, detail="Total Amount update failed")
    return {
        "message": "Success",
    }

@app.get("/taxes")
def search_tax_info():
    result = crud.mytaxSelect(mymodels_MySQL.TaxMaster)
    if not result:
        raise HTTPException(status_code=404, detail="Tax not found")
    
    # id = 1 のデータを取得
    tax_item = next((item for item in result if item["id"] == 1), None)
    
    if tax_item is None:
        raise HTTPException(status_code=404, detail="Tax with ID 1 not found")

    # percent と code を取得
    percent_value = float(tax_item["percent"]) if isinstance(tax_item["percent"], Decimal) else tax_item["percent"]
    code_value = tax_item["code"]

    # 辞書型で返す
    return {"tax_code": code_value, "percent": percent_value}