from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
import psycopg
from psycopg import errors  # Для перехвата специфических ошибок базы данных
from pydantic import BaseModel
from typing import Optional, List
#uvicorn main:app --reload
app = FastAPI()

DB_DSN = 'postgresql://postgres:1234@localhost:5432/sem6_lab2'

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
            'id': row[0], 
            'name': row[1],
            'level': {
                'id': row[2], 
                'name': row[3], 
                'level': row[4]
            }
        }
        res.append(organism)
    return res

def build_tree_recursive(items, parent_id):
    # Рекурсивная сборка дерева из плоского списка
    tree = []
    for item in items:
        if item['parent_id'] == parent_id:
            node = item.copy()
            node['children'] = build_tree_recursive(items, node['id'])
            tree.append(node)
    return tree

# GET ЭНДПОИНТЫ

# Получение всех деревьев
@app.get("/api/living_organisms/get/tree")
def get_living_organisms_tree(db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("""
            WITH RECURSIVE path_lo AS (
                SELECT 
                    plo.id,
                    lo.name,  
                    plo.path[array_upper(plo.path, 1) - 1] AS parent_id,
                    lo.level_id 
                FROM path_living_organisms plo
                INNER JOIN living_organisms lo
                    ON plo.id = lo.id
            ),
            rec AS (
                SELECT lo1.* FROM path_lo lo1
                LEFT JOIN path_lo lo2 ON lo1.parent_id = lo2.id
                WHERE lo2.id IS NULL
                UNION ALL
                SELECT lo.* FROM path_lo lo
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

# Получение всех потомков
@app.get("/api/living_organisms/get/all_child/{id}")
def get_all_descendants(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        # Проверяем существование узла
        cursor.execute("SELECT id FROM living_organisms WHERE id = %s", (id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Organism not found")

        cursor.execute("""
            SELECT 
                lo.id, 
                lo.name, 
                l.id, 
                l.name,
                l.level
            FROM path_living_organisms AS plo
            JOIN living_organisms lo ON plo.id = lo.id
            JOIN living_organism_levels l ON lo.level_id = l.id
            WHERE %s = ANY(plo.path) AND %s != lo.id
        """, (id, id, ))
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
            WITH parents AS (
                SELECT unnest(path) as id FROM path_living_organisms
                WHERE id = %s
            )
            SELECT 
                lo.id, 
                lo.name, 
                l.id, 
                l.name,
                l.level
            FROM parents AS p
            JOIN living_organisms lo ON p.id = lo.id
            JOIN living_organism_levels l ON lo.level_id = l.id
            WHERE %s != lo.id
        """, (id, id, ))
        return format_organisms_result(cursor.fetchall())
    
# Получение прямого предка
@app.get("/api/living_organisms/get/parent/{id}")
def get_direct_parent(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        # Сначала проверяем, есть ли такой организм вообще
        cursor.execute("""
            SELECT path[array_upper(path, 1) - 1] AS parent_id
            FROM path_living_organisms WHERE id = %s
        """, (id,))
        res_check = cursor.fetchone()
        if not res_check:
            raise HTTPException(status_code=404, detail="Organism not found")
        
        parent_id = res_check[0]
        if parent_id is None:
            return {"message": "This is a root organism (has no parent)"}

        cursor.execute("""
            SELECT 
                lo.id, 
                lo.name, 
                l.id, 
                l.name,
                l.level         
            FROM living_organisms lo
            JOIN living_organism_levels l ON lo.level_id = l.id WHERE lo.id = %s
        """, (parent_id,))
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

        cursor.execute("""
            SELECT 
                lo.id, 
                lo.name, 
                l.id, 
                l.name,
                l.level
            FROM path_living_organisms AS plo
            JOIN living_organisms lo ON plo.id = lo.id
            JOIN living_organism_levels l ON lo.level_id = l.id      
            WHERE plo.path[array_upper(plo.path, 1) - 1] = %s""", (id,))
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
                'INSERT INTO living_organisms(name, level_id) VALUES (%s,%s) RETURNING id', 
                (name, data.level_id)
            )
            new_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO path_living_organisms(id, path)
                SELECT %s, path || %s FROM path_living_organisms
                WHERE id = %s
            """, (new_id, new_id, data.parent_id))
            db.commit()
            cursor.execute("""
                SELECT 
                    lo.id, 
                    lo.name, 
                    l.id, 
                    l.name,
                    l.level
                FROM living_organisms lo
                JOIN living_organism_levels l ON lo.level_id = l.id      
                WHERE lo.id = %s
            """, (new_id,))
            return format_organisms_result(cursor.fetchall())[0]
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при сохранении: {str(e)}")

# Удаление листа или узла
@app.delete("/api/living_organisms/delete/node/{id}")
def delete_node(id: int, db = Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT 1 FROM living_organisms WHERE id = %s", (id,))
        res = cursor.fetchone()
        if not res: 
            raise HTTPException(status_code=404, detail="Node not found")

        try:
            # Перепривязка детей к родителю удаляемого узла
            cursor.execute("""
                UPDATE path_living_organisms 
                SET path = array_remove(path, %s)
                WHERE %s = ANY(path)
            """, (id, id))
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
            cursor.execute("SELECT 1 FROM living_organisms WHERE id = %s", (id,))
            target = cursor.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail=f"Organism with id {id} not found")

            cursor.execute("""
                DELETE FROM living_organisms
                WHERE id IN (SELECT id FROM path_living_organisms WHERE %s = ANY(path))
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