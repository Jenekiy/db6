"""
Create path_living_organisms
"""

from yoyo import step

__depends__ = {'20260414_04_q9NBa-insert-living-organisms'}

steps = [
    step("""
        CREATE TABLE path_living_organisms(
            id BIGINT PRIMARY KEY REFERENCES living_organisms(id) ON DELETE CASCADE,
            path BIGINT[] NOT NULL
        );  
        """,
        """
        DROP TABLE IF EXISTS path_living_organisms CASCADE;
        """
    )
]
