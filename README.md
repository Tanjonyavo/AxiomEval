# AxiomGuard

AxiomGuard is an AI security testing and assurance platform designed to evaluate AI agents and AI-enabled systems through reproducible security scenarios, evidence collection, findings, policies, and release gates.

## Status

Early development — Week 1: architecture and vertical slice.

## Initial goal

The first AxiomGuard vertical slice will implement the following pipeline:

```text
Target
  ↓
Scenario
  ↓
Run
  ↓
Evidence
  ↓
Finding
  ↓
Policy
  ↓
PASS / BLOCK
  ↓
HTML Report
```

## Repository structure

```text
AxiomGuard/
├── configs/
├── docs/
├── labs/
├── reports/
├── src/
│   └── axiomguard/
├── tests/
├── .gitignore
└── README.md
```

## Development principles

- Reproducible experiments
- Evidence-based security findings
- Deterministic testing where possible
- Modular Python architecture
- Local-first and open-source tooling
- Zero mandatory software or cloud cost

## Development status

AxiomGuard is currently under active development and is not production-ready.