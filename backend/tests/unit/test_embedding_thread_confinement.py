"""Embedding calls are confined to ONE thread (2026-09-30 API crash).

Each thread that calls torch gets its own libgomp team sized to the visible
CPUs (48 on Railway). ~20 concurrent page encodes on the default executor
exhausted the container's pids.max of 1000, libgomp failed thread creation
and the process segfaulted mid-retrieve. Record:
audit/2026-09-30_api_crash_brief.md.
"""

import asyncio
import threading

import numpy as np

from app.services import embeddings as emb


class _RecordingModel:
    def __init__(self):
        self.threads = set()
        self.active = 0
        self.max_active = 0
        self._guard = threading.Lock()

    def encode(self, texts, normalize_embeddings=True):
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.threads.add(threading.current_thread().name)
        threading.Event().wait(0.01)
        with self._guard:
            self.active -= 1
        if isinstance(texts, str):
            return np.ones(emb.EmbeddingService().dimension)
        return [np.ones(384) for _ in texts]


def _service(model):
    svc = emb.EmbeddingService()
    svc.model = model
    svc.redis_client = object()

    async def _miss(_key):
        return None

    async def _store(_key, _value):
        return None

    svc._get_cached_embedding = _miss
    svc._cache_embedding = _store
    return svc


def test_concurrent_encodes_from_many_loops_share_one_thread():
    model = _RecordingModel()
    svc = _service(model)

    async def one_pipeline(i):
        # Mirrors evidence._extract_semantic_snippet fanned out over pages.
        await asyncio.gather(
            *[svc.embed_text(f"claim {i} {j}") for j in range(10)],
            *[svc.embed_batch([f"s{i}{j}a", f"s{i}{j}b"]) for j in range(10)],
        )

    # Pipelines run under asyncio.run in separate threads (runner._executor).
    workers = [
        threading.Thread(target=asyncio.run, args=(one_pipeline(i),)) for i in range(4)
    ]
    for w in workers:
        w.start()
    for w in workers:
        w.join()

    assert model.max_active == 1
    assert len(model.threads) == 1
    assert next(iter(model.threads)).startswith("embed")


def test_torch_thread_cap_is_small():
    # A team per caller of this size, times one caller, stays far below 1000.
    assert 1 <= emb.EMBEDDING_TORCH_THREADS <= 8
    assert emb._ENCODE_EXECUTOR._max_workers == 1
