"""
Create living_organisms
"""

from yoyo import step

__depends__ = {'20260414_02_Qoxlj-insert-living-organism-levels'}

steps = [
    step("""
        CREATE TABLE living_organisms(
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            level_id INT REFERENCES living_organism_levels(id) NOT NULL
        );
        """,
        """
        DROP TABLE IF EXISTS living_organisms CASCADE;
        """
    )
]
