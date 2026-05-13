from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import psycopg
from psycopg import errors  # Для перехвата специфических ошибок базы данных
from pydantic import BaseModel
from typing import Optional, List
#uvicorn main:app --reload
app = FastAPI()

DB_DSN = 'postgresql://postgres:1234@localhost:5432/sem6_lab1'

# Функция для управления подключением
def get_db():
    with psycopg.connect(DB_DSN) as conn:
        yield conn

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ

def format_organisms_result(rows):
    # Преобразует строки из БД в структурированный словарь
    res = []
    for row in rows:
        organism = {
            'id': row[0], 'name': row[1], 'parent_id': row[2],
            'level': {'id': row[3], 'name': row[4], 'level': row[5]},
            'parent': None
        }
        if len(row) > 6 and row[6] is not None:
            organism['parent'] = {
                'id': row[6], 'name': row[7],
                'level': {'id': row[8], 'name': row[9], 'level': row[10]} if row[8] is not None else None
            }
        res.append(organism)
    return res

def build_tree_recursive(items, parent_id):
    # Рекурсивная сборка дерева из плоского списка
    tree = []
    for item in items:
        if item['parent_id'] == parent_id:
            node = item.copy()
            node['child'] = build_tree_recursive(items, node['id'])
            tree.append(node)
    return tree

# Базовый SQL запрос
BASE_SELECT_SQL = """
    SELECT 
        lo.id, lo.name, lo.parent_id,
        l.id, l.name, l.level,
        p.id, p.name,
        pl.id, pl.name, pl.level
    FROM living_organisms lo
    JOIN living_organism_levels l ON lo.level_id = l.id
    LEFT JOIN living_organisms p ON lo.parent_id = p.id
    LEFT JOIN living_organism_levels pl ON p.level_id = pl.id
"""

# GET ЭНДПОИНТЫ

# Получение всех деревьев
@app.get("/api/living_organisms/get/tree")
def get_living_organisms_tree(db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("""
            WITH RECURSIVE rec AS (
                SELECT lo1.* FROM living_organisms lo1
                LEFT JOIN living_organisms lo2 ON lo1.parent_id = lo2.id
                WHERE lo2.id IS NULL
                UNION ALL
                SELECT lo.* FROM living_organisms lo
                INNER JOIN rec r ON lo.parent_id = r.id
            )
            SELECT rec.id, rec.name, rec.parent_id, l.id, l.name, l.level
            FROM rec
            JOIN living_organism_levels l ON rec.level_id = l.id;
        """)
        rows = cursor.fetchall()
        
    if not rows:
        return [] # Вместо ошибки лучше вернуть пустой список, если дерево пустое

    flat_list = [
        {'id': r[0], 'name': r[1], 'parent_id': r[2], 
         'level': {'id': r[3], 'name': r[4], 'level': r[5]}} 
        for r in rows
    ]
    
    # Находим корень (у которого parent_id либо None, либо не входит в текущий список)
    root_parent = flat_list[0]['parent_id']
    tree = build_tree_recursive(flat_list, root_parent)
    return tree

# Получение объекта по id
@app.get("/api/living_organisms/get/search_for_id/{id}")
def get_by_id(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute(BASE_SELECT_SQL + " WHERE lo.id = %s", (id,))
        res = format_organisms_result(cursor.fetchall())
        if not res:
            # Обработка ошибки, если ID не существует
            raise HTTPException(status_code=404, detail=f"Organism with id {id} not found")
        return res[0]

# Получение объекта по имени
@app.get("/api/living_organisms/get/search_for_name/{name}")
def get_by_name(name: str, db = Depends(get_db)):
    with db.cursor() as cursor:
        query_name = f"%{name.strip()}%"
        cursor.execute(BASE_SELECT_SQL + " WHERE lo.name ILIKE %s", (query_name,))
        res = format_organisms_result(cursor.fetchall())
        if not res:
            # Обработка ошибки, если по имени ничего не найдено
            raise HTTPException(status_code=404, detail=f"No organisms found matching '{name}'")
        return res

# Получение всех потомков
@app.get("/api/living_organisms/get/all_child/{id}")
def get_all_descendants(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        # Проверяем существование узла
        cursor.execute("SELECT id FROM living_organisms WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Organism not found")

        cursor.execute("""
            WITH RECURSIVE rec AS (
                SELECT id, name, level_id, parent_id FROM living_organisms WHERE parent_id = %s
                UNION ALL
                SELECT lo.id, lo.name, lo.level_id, lo.parent_id 
                FROM living_organisms lo INNER JOIN rec r ON r.id = lo.parent_id
            )
            SELECT rec.id, rec.name, rec.parent_id, l.id, l.name, l.level,
                   p.id, p.name, pl.id, pl.name, pl.level
            FROM rec
            JOIN living_organism_levels l ON rec.level_id = l.id
            LEFT JOIN living_organisms p ON rec.parent_id = p.id
            LEFT JOIN living_organism_levels pl ON p.level_id = pl.id;
        """, (id,))
        return format_organisms_result(cursor.fetchall())

# Получение всех родителей
@app.get("/api/living_organisms/get/all_parent/{id}")
def get_all_parents(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        # Проверяем существование родителя
        cursor.execute("SELECT id FROM living_organisms WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Organism not found")

        cursor.execute("""
            WITH RECURSIVE rec AS (
                SELECT lo1.id, lo1.name, lo1.level_id, lo1.parent_id 
                FROM living_organisms lo1
                INNER JOIN living_organisms lo2
                ON lo1.id = lo2.parent_id
                WHERE lo2.id = %s
                UNION ALL
                SELECT lo.id, lo.name, lo.level_id, lo.parent_id 
                FROM living_organisms lo 
                INNER JOIN rec r ON r.parent_id = lo.id
            )
            SELECT rec.id, rec.name, rec.parent_id, l.id, l.name, l.level,
                   p.id, p.name, pl.id, pl.name, pl.level
            FROM rec
            JOIN living_organism_levels l ON rec.level_id = l.id
            LEFT JOIN living_organisms p ON rec.parent_id = p.id
            LEFT JOIN living_organism_levels pl ON p.level_id = pl.id;
        """, (id,))
        return format_organisms_result(cursor.fetchall())
    
# Получение прямого предка
@app.get("/api/living_organisms/get/parent/{id}")
def get_direct_parent(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        # Сначала проверяем, есть ли такой организм вообще
        cursor.execute("SELECT parent_id FROM living_organisms WHERE id = %s", (id,))
        res_check = cursor.fetchone()
        if not res_check:
            raise HTTPException(status_code=404, detail="Organism not found")
        
        parent_id = res_check[0]
        if parent_id is None:
            return {"message": "This is a root organism (has no parent)"}

        cursor.execute(BASE_SELECT_SQL + " WHERE lo.id = %s", (parent_id,))
        res = format_organisms_result(cursor.fetchall())
        return res[0]

# Получение прямых потомков
@app.get("/api/living_organisms/get/childs/{id}")
def get_direct_parent(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        # Сначала проверяем, есть ли такой организм вообще
        cursor.execute("SELECT id FROM living_organisms WHERE id = %s", (id,))
        res_check = cursor.fetchone()
        if not res_check:
            raise HTTPException(status_code=404, detail="Organism not found")

        cursor.execute(BASE_SELECT_SQL + " WHERE lo.parent_id = %s", (id,))
        res = format_organisms_result(cursor.fetchall())
        return res
    
# POST / DELETE ЭНДПОИНТЫ

class OrganismCreate(BaseModel):
    name: str
    level_id: int
    parent_id: Optional[int] = None

# Добавление листа
@app.post("/api/living_organisms/add/list")
def create_organism(data: OrganismCreate, db = Depends(get_db)):
    name = data.name.strip().capitalize()
    
    with db.cursor() as cursor:
        cursor.execute("SELECT id FROM living_organisms WHERE name ILIKE %s", (name,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Организм с именем '{name}' уже существует."
            )
        cursor.execute("SELECT id FROM living_organism_levels WHERE id = %s", (data.level_id,))
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Уровень с id={data.level_id} не найден в справочнике уровней."
            )
        if data.parent_id is not None:
            cursor.execute("SELECT id FROM living_organisms WHERE id = %s", (data.parent_id,))
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Родительский организм с id={data.parent_id} не найден."
                )
        try:
            cursor.execute(
                'INSERT INTO living_organisms(name, level_id, parent_id) VALUES (%s,%s,%s) RETURNING id', 
                (name, data.level_id, data.parent_id)
            )
            new_id = cursor.fetchone()[0]
            db.commit()
            cursor.execute(BASE_SELECT_SQL + " WHERE lo.id = %s", (new_id,))
            return format_organisms_result(cursor.fetchall())[0]
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при сохранении: {str(e)}")

# Удаление листа или узла
@app.delete("/api/living_organisms/delete/node/{id}")
def delete_node(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT parent_id FROM living_organisms WHERE id = %s", (id,))
        res = cursor.fetchone()
        if not res: 
            raise HTTPException(status_code=404, detail="Node not found")
        
        parent_id = res[0]
        try:
            # Перепривязка детей к родителю удаляемого узла
            cursor.execute("UPDATE living_organisms SET parent_id = %s WHERE parent_id = %s", (parent_id, id))
            cursor.execute("DELETE FROM living_organisms WHERE id = %s", (id,))
            db.commit()
            return {"message": "Node deleted, children reassigned successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

# Удаление поддерева
@app.delete("/api/living_organisms/delete/subtree/{id}")
def delete_living_organisms_subtree(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        try:
            cursor.execute("SELECT name FROM living_organisms WHERE id = %s", (id,))
            target = cursor.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail=f"Organism with id {id} not found")

            cursor.execute("""
                WITH RECURSIVE descendant_ids AS (
                    -- Базовый случай: сам узел
                    SELECT id FROM living_organisms WHERE id = %s
                    UNION ALL
                    -- Рекурсивный шаг: все дети узлов, найденных на предыдущем шаге
                    SELECT lo.id 
                    FROM living_organisms lo
                    JOIN descendant_ids d ON lo.parent_id = d.id
                )
                DELETE FROM living_organisms
                WHERE id IN (SELECT id FROM descendant_ids)
                RETURNING id;
            """, (id,))
            
            deleted_rows = cursor.fetchall()
            deleted_count = len(deleted_rows)

            db.commit()
            
            return {
                "message": "Subtree deleted successfully",
                "target_node": target[0],
                "deleted_count": deleted_count,
                "deleted_ids": [row[0] for row in deleted_rows]
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")