# Merkle Root Generation

This repository contains scripts for generating merkle data for RSUP allocations.

## Directory Structure

```
data/
├── sources/        # Source data for allocations
│   ├── team_splits.json       # Team allocation percentages (in basis points)
│   └── victim_data.json       # Victim data including known hack losses and reimbursements to date
│
├── merkle/         # Generated merkle data including proofs
│
└── cache/          # Cache files for optimizing script runtime
```

## Scripts

`scripts/generate_merkle_roots.py`

Main script for generating merkle data

## Usage

To generate merkle roots:

```bash
brownie run generate_merkle_roots
```

This will:

1. Read source data from `data/sources`
2. Generate merkle trees for each allocation
3. Save proof and claim data to `data/merkle`
