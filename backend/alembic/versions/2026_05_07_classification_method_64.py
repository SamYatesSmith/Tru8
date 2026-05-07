"""Expand evidence.classification_method varchar(20) -> varchar(64).

Revision ID: classification_method_64
Revises: typed_entities_2026
Create Date: 2026-05-07

Bug fix on top of B3 (`dabec21`) and Bug D (`76e8c1d`): the
classification_method column was sized varchar(20) but recently-added
provenance values exceed it:
  - 'arxiv_unvetted_demotion'         (23 chars)  -- B3 / dabec21
  - 'infrastructure_subdomain_floor'  (30 chars)  -- B3 / dabec21
  - 'low_authority_firm_floor'        (24 chars)  -- B3 / dabec21
  - 'domain_concentration_cap'        (24 chars)  -- Bug D / 76e8c1d

Live test 2026-05-07 caught a StringDataRightTruncationError when Bug D
fired on the TRU-7C40 mammogram check; the same error class lurks for
any content that triggers the B3 floors. The descriptive names matter
for diagnostic clarity, so the fix is to expand the column rather than
abbreviate the values.

64 chars gives ample headroom for future provenance methods without
over-allocating; the longest current value is 30 chars.

Forward: ALTER COLUMN ... TYPE varchar(64). Postgres widens in place,
no data rewrite required.

Reverse: ALTER COLUMN ... TYPE varchar(20) USING substring(... for 20).
Lossy if any rows have values >20 chars; downgrade also needs to revert
the consuming commits before it can apply cleanly.
"""

from alembic import op


revision = "classification_method_64"
down_revision = "typed_entities_2026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE evidence ALTER COLUMN classification_method TYPE varchar(64)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE evidence "
        "ALTER COLUMN classification_method TYPE varchar(20) "
        "USING substring(classification_method FOR 20)"
    )
