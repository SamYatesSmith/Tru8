"""Every table-backed model must be exported from `app.models`.

WHY THIS EXISTS
---------------
`entrypoint.sh` bootstraps a fresh database like this:

    from app.models import *          # only what __init__.py exports
    SQLModel.metadata.create_all      # so: only the exported models
    alembic stamp head                # "everything is already applied"

A model that is defined but not exported is therefore never created by
create_all, AND the stamp tells Alembic its migration has already run. The
table can then never be created by either route. A correct migration, sitting
in the chain, silently skipped forever.

That is not hypothetical. `ClaimConsensus` was missing from the exports, so
`claim_consensus` did not exist. Every /agent request at quick or full tier
called session.get(ClaimConsensus, ...), hit UndefinedTableError, and the
handler swallowed it without rolling back — leaving the session aborted so the
NEXT statement, the credit debit, failed with InFailedSQLTransactionError. The
500 that reached Sentry pointed at billing code that had done nothing wrong.
Found 2026-08-04 while smoke-testing the remote MCP endpoint, which uses that
exact path.

This test is cheap and general: it catches the whole class, for every model
added from here on, at the moment someone forgets the export.
"""

import importlib
import pkgutil

from sqlmodel import SQLModel

import app.models


def _table_models_in_package():
    """Every table=True SQLModel defined under app/models, by module."""
    found = {}
    for mod in pkgutil.iter_modules(app.models.__path__):
        if mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"app.models.{mod.name}")
        for name in dir(module):
            obj = getattr(module, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, SQLModel)
                and obj is not SQLModel
                and getattr(obj, "__tablename__", None)
                and obj.__module__ == module.__name__
            ):
                found[name] = (mod.name, obj.__tablename__)
    return found


def test_every_table_model_is_exported_from_app_models():
    """A model missing here is a table that will never exist on a fresh deploy."""
    defined = _table_models_in_package()
    assert defined, "no table-backed models discovered — the scan is broken"

    missing = {
        name: where for name, where in defined.items() if not hasattr(app.models, name)
    }
    assert not missing, (
        "These table-backed models are not imported in app/models/__init__.py:\n"
        + "\n".join(
            f"  {name}  (app/models/{mod}.py -> table '{table}')"
            for name, (mod, table) in sorted(missing.items())
        )
        + "\n\nentrypoint.sh creates a fresh database from the EXPORTED models and "
        "then stamps Alembic to head, so an unexported model is never created "
        "and its migration is permanently skipped. Add the import."
    )


def test_exported_models_are_in_sqlmodel_metadata():
    """Exported is not enough — the table must reach create_all's metadata."""
    defined = _table_models_in_package()
    tables = set(SQLModel.metadata.tables)
    missing = {
        name: table
        for name, (_mod, table) in defined.items()
        if hasattr(app.models, name) and table not in tables
    }
    assert not missing, f"models exported but absent from metadata: {missing}"


def test_claim_consensus_specifically():
    """Regression pin for the model whose absence caused the 2026-08-04 500s."""
    assert hasattr(app.models, "ClaimConsensus")
    assert "claim_consensus" in SQLModel.metadata.tables
