"""HW05 Part A: prove PK uniqueness and FK referential integrity for the Wildcat star."""
import pandas as pd

TABLES = ["dim_advisor", "dim_benchmark", "dim_client", "dim_date", "dim_security",
          "fact_fees", "fact_portfolio_snapshot", "fact_transactions"]
t = {n: pd.read_csv(f"{n}.csv", dtype=str, keep_default_na=False, na_values=[""]) for n in TABLES}

PKS = {"dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id", "dim_client": "client_id",
       "dim_date": "date_id", "dim_security": "security_id", "fact_fees": "fee_id",
       "fact_portfolio_snapshot": "snapshot_id", "fact_transactions": "txn_id"}

FKS = [  # (table, column, target table, target column)
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]

print("PRIMARY KEYS")
for n, k in PKS.items():
    s = t[n][k]
    print(f"  {n}.{k}: rows={len(s):,} unique={s.is_unique} nulls={s.isna().sum()}")
    assert s.is_unique and s.notna().all()
# dim_date[date] is the column the facts join on, so it must be unique too
assert t["dim_date"]["date"].is_unique

print("FOREIGN KEYS")
for f, c, d, dc in FKS:
    s = t[f][c]
    orphans = (~s.dropna().isin(set(t[d][dc]))).sum()
    print(f"  {f}.{c} -> {d}[{dc}]: nulls={s.isna().sum():,} orphans={orphans}")
    assert orphans == 0

# The only nullable FK: security_id on cash-movement transactions
ft = t["fact_transactions"]
print("txn_type where security_id is blank:\n", ft[ft.security_id.isna()].txn_type.value_counts())
print("txn_type where security_id is filled:\n", ft[ft.security_id.notna()].txn_type.value_counts())

# Part B: grain checks
print("GRAIN")
snap, fees = t["fact_portfolio_snapshot"], t["fact_fees"]
assert not snap.duplicated(["client_id", "snapshot_date"]).any()
print("  fact_portfolio_snapshot: (client_id, snapshot_date) unique -> one row per client per month")
assert not fees.duplicated(["client_id", "fee_date"]).any()
print("  fact_fees: (client_id, fee_date) unique -> one fee charge per client per month")
dups = ft.duplicated(["client_id", "txn_date", "txn_type", "security_id"]).sum()
print(f"  fact_transactions: (client, date, type, security) still has {dups} repeats -> grain is the single event, keyed only by txn_id")
assert ft.txn_id.is_unique
print("ALL KEY AND GRAIN CHECKS PASSED")
