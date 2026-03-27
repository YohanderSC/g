"""motivo_rechazo_referido

Revision ID: 582326ba0696
Revises: 0aa6b6d161e6
Create Date: 2026-03-29 03:06:59.612888+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de revisión usados por Alembic
revision: str = "582326ba0696"
down_revision: Union[str, None] = "0aa6b6d161e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplica los cambios de esta migración a la base de datos."""
    # Agregar columna motivo_rechazo a la tabla solicitudes_referido
    op.add_column(
        "solicitudes_referido",
        sa.Column("motivo_rechazo", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Revierte los cambios de esta migración (rollback)."""
    op.drop_column("solicitudes_referido", "motivo_rechazo")
