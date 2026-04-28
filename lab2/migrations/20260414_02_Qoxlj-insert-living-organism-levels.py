"""
Insert living_organism_levels
"""

from yoyo import step

__depends__ = {'20260414_01_evj9D-create-living-organisms-levels'}

steps = [
    step("""
        INSERT INTO living_organism_levels (name, level) VALUES
        ('Домен', 1),
        ('Царство', 2),
        ('Тип', 3),
        ('Отдел', 3),
        ('Класс', 4),
        ('Отряд', 5),
        ( 'Порядок', 5),
        ( 'Семейство', 6),
        ( 'Род', 7),
        ( 'Вид', 8);
        """,
        """
        TRUNCATE TABLE living_organism_levels CASCADE;
        """
    )
]

