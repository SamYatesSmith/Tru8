"""Add email notification preference fields to User table

Revision ID: 3b1a54dd6aa1
Revises: b7c8d9e0f1a2
Create Date: 2025-12-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '3b1a54dd6aa1'
down_revision = 'b7c8d9e0f1a2'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    # Add email notification preference fields to User table
    # Default to True for check completion/failure (users expect notifications)
    # Default to False for digest/marketing (opt-in)

    if not column_exists('user', 'email_notifications_enabled'):
        op.add_column('user', sa.Column(
            'email_notifications_enabled',
            sa.Boolean(),
            nullable=False,
            server_default='true'
        ))

    if not column_exists('user', 'email_check_completion'):
        op.add_column('user', sa.Column(
            'email_check_completion',
            sa.Boolean(),
            nullable=False,
            server_default='true'
        ))

    if not column_exists('user', 'email_check_failure'):
        op.add_column('user', sa.Column(
            'email_check_failure',
            sa.Boolean(),
            nullable=False,
            server_default='true'
        ))

    if not column_exists('user', 'email_weekly_digest'):
        op.add_column('user', sa.Column(
            'email_weekly_digest',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        ))

    if not column_exists('user', 'email_marketing'):
        op.add_column('user', sa.Column(
            'email_marketing',
            sa.Boolean(),
            nullable=False,
            server_default='false'
        ))


def downgrade():
    op.drop_column('user', 'email_notifications_enabled')
    op.drop_column('user', 'email_check_completion')
    op.drop_column('user', 'email_check_failure')
    op.drop_column('user', 'email_weekly_digest')
    op.drop_column('user', 'email_marketing')
