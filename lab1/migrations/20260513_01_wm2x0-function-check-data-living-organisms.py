"""
function check_data living_organisms
"""

from yoyo import step

__depends__ = {'20260414_04_uYwfz-insert-living-organisms'}

steps = [
    step("""
        CREATE OR REPLACE FUNCTION check_data()
        RETURNS TABLE (
            total_rows BIGINT,          -- Общее количество записей
            is_count_valid BOOLEAN,     -- Проверка: записей >= 20
            min_child BIGINT,           -- Минимальное число потомков у узла
            max_child BIGINT,           -- Максимальное число потомков у узла
            is_children_valid BOOLEAN,  -- Проверка: от 2 до 5 потомков
            max_depth INTEGER,          -- Максимальная глубина дерева
            is_depth_valid BOOLEAN      -- Проверка: глубина >= 4
        )
        LANGUAGE plpgsql
        AS $$
        BEGIN 
            RETURN QUERY
            -- 1. Рекурсивное CTE для подсчета глубины дерева
            WITH RECURSIVE rec AS (
                -- Начальные данные: корни
                SELECT id, 0 AS level 
                FROM living_organisms 
                WHERE parent_id IS NULL
                
                UNION ALL
                
                -- Рекурсивный шаг: присоединяем потомков к родителям, увеличивая level
                SELECT lo.id, r.level + 1  
                FROM living_organisms lo
                INNER JOIN rec r ON lo.parent_id = r.id
            ),
            -- 2. CTE для подсчета количества детей у каждого родителя
            children_stats AS (
                SELECT COUNT(id) AS cnt 
                FROM living_organisms
                WHERE parent_id IS NOT NULL
                GROUP BY parent_id
            )
            
            -- Итоговая сборка данных
            SELECT 
                -- Условие 1: количество объектов (>= 20)
                (SELECT COUNT(*) FROM living_organisms) AS total_rows,
                (SELECT COUNT(*) >= 20 FROM living_organisms) AS is_count_valid,
                
                -- Условие 2: каждый нелистовой узел имеет от 2 до 5 потомков
                (SELECT MIN(cnt) FROM children_stats) AS min_child,
                (SELECT MAX(cnt) FROM children_stats) AS max_child,
                (SELECT COALESCE(MIN(cnt) >= 2 AND MAX(cnt) <= 5, false) FROM children_stats) AS is_children_valid,
                
                -- Условие 3: глубина дерева (>= 4)
                (SELECT MAX(level) FROM rec) AS max_depth,
                (SELECT COALESCE(MAX(level) >= 4, false) FROM rec) AS is_depth_valid;
        END;
        $$;
        """,
        "DROP FUNCTION IF EXISTS check_data();"
        )
]
