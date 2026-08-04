from .user import User, Subscription
from .check import Check, Claim, Evidence, RawEvidence
from .unknown_source import UnknownSource
from .claim_map import (
    ClaimMap,
    ClaimType,
    ElementState,
    EvidenceRelationship,
    ClaimElement,
    ClaimMapMetadata,
    EvidenceRef,
)
from .video_recommendation import VideoRecommendation
from .api_key import APIKey
from .webhook import Webhook
from .agent_transaction import AgentTransaction
from .usage_event import UsageEvent
from .claim_consensus import ClaimConsensus

# EVERY table-backed model MUST be imported here, not merely defined.
# entrypoint.sh bootstraps a fresh database with `from app.models import *`
# then SQLModel.metadata.create_all(), and finally `alembic stamp head`.
# A model missing from this file is therefore never created AND is stamped
# past its own migration, so it can never be created later either.
#
# ClaimConsensus was missing, which is exactly what happened: the
# claim_consensus table did not exist, every /agent quick|full request
# raised UndefinedTableError, and a swallowed exception then poisoned the
# session so the credit debit died with InFailedSQLTransactionError -- a
# 500 whose Sentry trace pointed at billing. See OPEN_WORK 2026-08-04.

__all__ = [
    "User",
    "Subscription",
    "Check",
    "Claim",
    "Evidence",
    "RawEvidence",
    "UnknownSource",
    "ClaimMap",
    "ClaimType",
    "ElementState",
    "EvidenceRelationship",
    "ClaimElement",
    "ClaimMapMetadata",
    "EvidenceRef",
    "VideoRecommendation",
    "APIKey",
    "Webhook",
    "AgentTransaction",
    "UsageEvent",
    "ClaimConsensus",
]
