"""
Create living_organisms
"""

from yoyo import step

__depends__ = {'20260414_02_Z4NZg-insert-living-organism-levels'}

steps = [
    step("""
        Create table living_organisms(
            id bigserial primary key,
            name varchar(255) unique not null CHECK (length(trim(name)) > 0),
            level_id int references living_organism_levels(id) not null,
            parent_id int references living_organisms(id)
        );
        """,
        """
        DROP TABLE IF EXISTS living_organisms;
        """)
]
