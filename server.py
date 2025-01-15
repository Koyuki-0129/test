from fastapi import FastAPI, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse

from pydantic import BaseModel

from typing import Optional, List

import sqlite3

import uvicorn

# FastAPIアプリケーションのインスタンスを作成

app = FastAPI()

# CORSを有効化（開発環境用設定）

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],

)

# データベース初期化処理

def init_db():

    """データベースの初期化"""

    with sqlite3.connect("app.db") as conn:

        conn.execute(

            """

            CREATE TABLE IF NOT EXISTS todos (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                title TEXT NOT NULL,

                completed BOOLEAN DEFAULT FALSE,

                number INTEGER  DEFAULT 0

            )

            """

        )

# アプリケーション起動時にデータベースを初期化

init_db()

# リクエストデータの定義

class Item(BaseModel):

    title: str

    completed: Optional[bool] = False

    number: int = 0

class ItemResponse(Item):

    id: int

# HTMLクライアントの提供

@app.get("/", response_class=HTMLResponse)

def read_root():

    """トップページにHTMLクライアントを提供"""

    with open("client.html", "r", encoding="utf-8") as f:

        return f.read()

# データベース操作のヘルパー関数

def execute_query(query: str, params: tuple = (), fetchone: bool = False, db_name: str = "app.db"):

    """

    データベース操作用の汎用関数

    :param query: 実行するSQLクエリ

    :param params: クエリに渡すパラメータ

    :param fetchone: 単一行取得フラグ

    :param db_name: データベース名

    """

    with sqlite3.connect(db_name) as conn:

        cursor = conn.execute(query, params)

        if query.strip().upper().startswith("SELECT"):

            if fetchone:

                return cursor.fetchone()

            return cursor.fetchall()

        conn.commit()

        return cursor.lastrowid if "INSERT" in query.upper() else cursor.rowcount

# 共通のCRUDエンドポイント群

def create_endpoints(entity_name: str):

    """

    CRUDエンドポイントを生成

    :param entity_name: エンティティ名（todosやnumbersなど）

    """

    table_name = entity_name

    @app.post(f"/{table_name}s", response_model=ItemResponse)

    def create_item(item: Item):

        """新しいエンティティを作成"""

        item_id = execute_query(

            f"INSERT INTO {table_name}s (title, completed) VALUES (?, ?)",

            (item.title, item.completed),

        )

        return {"id": item_id, "title": item.title, "completed": item.completed}

    @app.get(f"/{table_name}s", response_model=List[ItemResponse])

    def get_items():

        """すべてのエンティティを取得"""

        items = execute_query(f"SELECT * FROM {table_name}s")

        return [{"id": t[0], "title": t[1], "completed": bool(t[2])} for t in items]

    @app.get(f"/{table_name}s/{{item_id}}", response_model=ItemResponse)

    def get_item(item_id: int):

        """特定のエンティティを取得"""

        item = execute_query(f"SELECT * FROM {table_name}s WHERE id = ?", (item_id,), fetchone=True)

        if not item:

            raise HTTPException(status_code=404, detail=f"{entity_name.capitalize()} not found")

        return {"id": item[0], "title": item[1], "completed": bool(item[2])}

    @app.put(f"/{table_name}s/{{item_id}}", response_model=ItemResponse)

    def update_item(item_id: int, item: Item):

        """特定のエンティティを更新"""

        rows = execute_query(

            f"UPDATE {table_name}s SET title = ?, completed = ? WHERE id = ?",

            (item.title, item.completed, item_id),

        )

        if rows == 0:

            raise HTTPException(status_code=404, detail=f"{entity_name.capitalize()} not found")

        return {"id": item_id, "title": item.title, "completed": item.completed}

    @app.delete(f"/{table_name}s/{{item_id}}")

    def delete_item(item_id: int):

        """特定のエンティティを削除"""

        rows = execute_query(f"DELETE FROM {table_name}s WHERE id = ?", (item_id,))

        if rows == 0:

            raise HTTPException(status_code=404, detail=f"{entity_name.capitalize()} not found")

        return {"message": f"{entity_name.capitalize()} deleted"}

# 特定のエンドポイントを作成

create_endpoints("todo")

create_endpoints("number")

# TODOとNumberを同時に投稿するエンドポイント

@app.post("/combined")

def create_combined(todo: Item, number: Item):

    """TODOとNumberを同時に作成"""

    todo_id = execute_query(

        "INSERT INTO todos (title, completed) VALUES (?, ?)",

        (todo.title, todo.completed),

    )

    number_id = execute_query(

        "INSERT INTO numbers (title, completed) VALUES (?, ?)",

        (number.title, number.completed),

    )

    return {

        "todo": {"id": todo_id, "title": todo.title, "completed": todo.completed},

        "number": {"id": number_id, "title": number.title, "completed": number.completed},

    }

# アプリケーションを起動

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000) 