# ARYA Memory Design

This document explains ARYA's memory concepts, storage priorities, and retrieval philosophy.

## Long-term Memory
Purpose:
- Store durable facts, user history, completed goals, research artifacts, and policies.

Characteristics:
- Durable and versioned; optimized for recall over months and years.
- Includes provenance metadata (source, timestamp, consent status).
- Supports structured and semi-structured records (dossiers, knowledge nodes).

## Short-term Memory
Purpose:
- Maintain conversational context, transient state, and in-progress reasoning.

Characteristics:
- Ephemeral and session-scoped by default; can be promoted to long-term memory with user approval.
- Optimized for fast access and low-latency reasoning.

## User Preferences
Purpose:
- Store personal configuration, presentation preferences, privacy settings, and consent rules.

Guidelines:
- Preferences are first-class and consulted before actions and suggestions.
- Changes to critical preferences are recorded with confirmation and provenance.

## Goals
Purpose:
- Represent ambitions with structure, timeline, success criteria, and linked evidence.

Characteristics:
- Goals may reference knowledge nodes, tasks, and evidence artifacts in long-term memory.
- Goals carry metadata for priority, confidence, and review cadence.

## Knowledge Storage
Purpose:
- Store research artifacts, extracted facts, summaries, and citations.

Guidelines:
- Persist raw sources alongside synthesized notes to preserve traceability.
- Support tagging, linking, and topic-based aggregation for dossier creation.

## Memory Retrieval Philosophy
- Relevance-first: retrieve items that maximize support for the user's current intent.
- Explainable recall: every retrieved item should include why it was selected (query match, recency, importance).
- User-in-the-loop promotion: users control what transitions from short-term to long-term memory.
- Privacy-aware filtering: respect user consent, privacy labels, and selective redaction at retrieval time.

Security & Governance
- All memory access is audited; sensitive data is protected through encryption, access controls, and selective sync policies.
- Retention policies are configurable and transparent to the user.

This design emphasizes traceability, user control, and a retrieval strategy that prioritizes useful, explainable context for reasoning and action.