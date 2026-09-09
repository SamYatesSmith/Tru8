import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    "factorial",
    Path(__file__).resolve().parents[2] / "scripts/run_passage_evaluation.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    pack, extraction = tmp_path / "pack", tmp_path / "extraction"
    (pack / "prepared").mkdir(parents=True)
    extraction.mkdir()
    raw = "<main>Saved source</main>"
    (pack / "source.html").write_text(raw)
    module.dump(
        pack / "manifest.json",
        {
            "sources": [
                {
                    "id": "s",
                    "status": "captured",
                    "file": "source.html",
                    "sha256": module.sha(raw),
                    "url": "https://example.invalid",
                    "title": "Source",
                }
            ]
        },
    )
    module.dump(
        pack / "spec.json",
        {
            "cases": [
                {
                    "id": "c",
                    "claim": "Claim",
                    "elements": [],
                    "source_ids": ["s"],
                    "review_guidance": "Never send this answer",
                }
            ]
        },
    )
    module.dump(pack / "prepared/synthetic_inputs.json", {"cases": []})
    for arm in ("legacy", "structured"):
        (extraction / f"s-{arm}.txt").write_text(arm)
    module.dump(
        extraction / "report.json",
        {
            "sources": [
                {
                    "id": "s",
                    "source_sha256": module.sha(raw),
                    "arms": {
                        arm: {"sha256": module.sha(arm)}
                        for arm in ("legacy", "structured")
                    },
                }
            ]
        },
    )
    return pack, extraction


def test_source_and_extraction_hashes_are_checked(tmp_path):
    pack, extraction = fixture(tmp_path)
    cases = module.prepare(pack, extraction)
    assert cases[0]["sources"][0]["legacy"] == "legacy"
    assert cases[0]["sources"][0]["structured"] == "structured"
    assert "Never send this answer" not in json.dumps(cases)
    (extraction / "s-structured.txt").write_text("changed")
    with pytest.raises(ValueError, match="Extraction hash mismatch"):
        module.prepare(pack, extraction)


@pytest.mark.asyncio
async def test_dry_run_cannot_make_model_requests(tmp_path, monkeypatch):
    pack, extraction = fixture(tmp_path)

    async def forbidden(*args, **kwargs):
        raise AssertionError("Network access in dry run")

    monkeypatch.setattr("httpx.AsyncClient.post", forbidden)
    args = SimpleNamespace(
        pack=pack,
        extraction=extraction,
        output=tmp_path / "out",
        cases=None,
        max_requests=2,
        max_characters=10000,
        execute=False,
        classifications=None,
    )
    await module.evaluate(args)
    plan = json.loads((args.output / "plan.json").read_text())
    assert plan["status"] == "prepared" and plan["requests"] == 0


@pytest.mark.asyncio
async def test_budget_stops_before_network_and_restores_settings(tmp_path, monkeypatch):
    pack, extraction = fixture(tmp_path)
    import httpx

    async def classifier_request(self, items):
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://generativelanguage.googleapis.com/test",
                json={"prompt": "test"},
            )

    monkeypatch.setattr(module.EvidenceClassifier, "classify_batch", classifier_request)

    async def forbidden(*args, **kwargs):
        raise AssertionError("Request budget exceeded")

    monkeypatch.setattr(httpx.AsyncClient, "post", forbidden)
    before = (
        module.settings.ENABLE_PASSAGE_MAPPING,
        module.settings.ENABLE_STRUCTURED_EXTRACTION,
        module.settings.SENTRY_DSN,
    )
    args = SimpleNamespace(
        pack=pack,
        extraction=extraction,
        output=tmp_path / "out",
        cases=None,
        max_requests=0,
        max_characters=10000,
        execute=True,
        classifications=None,
    )
    await module.evaluate(args)
    plan = json.loads((args.output / "plan.json").read_text())
    assert plan["status"] == "stopped" and plan["requests"] == 0
    assert (
        module.settings.ENABLE_PASSAGE_MAPPING,
        module.settings.ENABLE_STRUCTURED_EXTRACTION,
        module.settings.SENTRY_DSN,
    ) == before


def test_importing_the_script_leaves_logging_enabled():
    """Importing the evaluation module must not switch logging off for the
    whole process. It once did (logging.disable at module level), which made
    every test after it blind — the Sentry behavioural tests failed only in a
    whole-suite run. The switch belongs in main()."""
    import logging

    assert logging.root.manager.disable == logging.NOTSET
    assert logging.getLogger("app").isEnabledFor(logging.CRITICAL)
