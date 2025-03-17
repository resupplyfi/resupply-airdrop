# Merkle Root Generation

This repository contains scripts to generate merkle data for RSUP allocations. All final source and output data can be found in the data directory.

## Data directory Structure

```
data/
├── sources/        # Source data for allocations
│   ├── team_splits.json       # Team allocation percentages (in basis points)
│   └── victim_data.json       # Victim data including known hack losses and reimbursements to date
│   └── penalty_data.json      # Total penalties for each user who broke a lock
│
├── merkle/         # Generated merkle data including proofs
│
└── cache/          # Cache files for optimizing script runtime
```

## Usage

To refresh, and save new supply data:

```bash
brownie run compute_supply
```

To refresh, and save new penalty data:

```bash
brownie run compute_lock_breaks
```

To generate merkle roots:

```bash
brownie run generate_merkle_roots
```

This will:

1. Read source data from `data/sources`
2. Generate merkle trees for each allocation
3. Save proof and claim data to `data/merkle`
