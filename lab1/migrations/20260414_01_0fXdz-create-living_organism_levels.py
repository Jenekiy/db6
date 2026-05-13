"""
Create living_organism_levels
"""

from yoyo import step

__depends__ = {}

steps = [
    step("""
         Create table living_organism_levels(
            id serial primary key,
            name varchar(255) unique not null CHECK (length(trim(name)) > 0),
            level int not null check(level > 0)
        );
        """,
        """
        DROP TABLE IF EXISTS living_organism_levels CASCADE;
        """
    )
]
