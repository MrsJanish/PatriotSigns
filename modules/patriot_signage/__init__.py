# -*- coding: utf-8 -*-
from . import models


def _create_sign_part_table(env):
    """
    Pre-init hook to create ps_sign_part table if it doesn't exist.
    
    This is needed because the model was added but the original deployment
    failed before the table could be created. Odoo 19 raises an error if
    a model exists without a corresponding table.
    """
    env.cr.execute("""
        CREATE TABLE IF NOT EXISTS ps_sign_part (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL DEFAULT 'Main Body',
            instance_id INTEGER NOT NULL,
            sign_type_id INTEGER,
            project_id INTEGER,
            sequence INTEGER DEFAULT 10,
            material VARCHAR,
            process_route VARCHAR DEFAULT 'router',
            finish_color VARCHAR,
            width DOUBLE PRECISION,
            height DOUBLE PRECISION,
            thickness DOUBLE PRECISION,
            state VARCHAR DEFAULT 'draft',
            production_notes TEXT,
            create_uid INTEGER,
            create_date TIMESTAMP,
            write_uid INTEGER,
            write_date TIMESTAMP,
            message_main_attachment_id INTEGER
        )
    """)
