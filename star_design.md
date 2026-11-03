# HW5 Star Design — Wildcat Capital

## Part A — Keys

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_advisor | Dimension | advisor_id | — |
| dim_benchmark | Dimension | benchmark_id | — |
| dim_client | Dimension | client_id | advisor_id → dim_advisor[advisor_id] |
| dim_date | Dimension | date_id | — |
| dim_security | Dimension | security_id | benchmark_id → dim_benchmark[benchmark_id] |
| fact_fees | Fact | fee_id | client_id → dim_client[client_id]<br>advisor_id → dim_advisor[advisor_id]<br>fee_date → dim_date[date] |
| fact_portfolio_snapshot | Fact | snapshot_id | client_id → dim_client[client_id]<br>advisor_id → dim_advisor[advisor_id]<br>benchmark_id → dim_benchmark[benchmark_id]<br>snapshot_date → dim_date[date] |
| fact_transactions | Fact | txn_id | client_id → dim_client[client_id]<br>advisor_id → dim_advisor[advisor_id]<br>security_id → dim_security[security_id] *(nullable)*<br>txn_date → dim_date[date] |

**Notes**
- **Date joins:** all three fact date columns (fee_date, snapshot_date, txn_date) store calendar dates (YYYY-MM-DD), so they match dim_date[date], not the integer surrogate dim_date[date_id]. dim_date[date] is unique (1,827 rows, 2020-01-01 to 2024-12-31), so it can serve as the "one" side of the relationship.
- **Dimension-to-dimension FKs:** dim_client.advisor_id → dim_advisor and dim_security.benchmark_id → dim_benchmark are snowflake links between dimensions.
- **Key that can legitimately be blank:** fact_transactions.security_id is blank on 101,528 rows. Every blank row is a cash movement with no security involved (Deposit 35,956 · Advisory Fee 35,742 · Withdrawal 29,830), and every Buy, Sell and Dividend row has one. That's expected, not a data defect. No other key column has blanks.
- **Integrity proven in code:** check_keys.py confirms every PK is unique and non-null and every FK has **0 orphans** (every non-blank value exists in the target column).

## Part B — Grain

- **fact_portfolio_snapshot:** One row represents one client's account at the start of one month — basically a monthly check-in on how much money they have, how they're doing YTD, and how that stacks up against their benchmark. No client ever shows up twice in the same month.
- **fact_fees:** One row represents the single fee Wildcat charged one client in one month, and the client gets exactly one bill per month. Fee_type just tells you what kind of fee it was.
- **fact_transactions:** One row represents one individual thing that happened in a client's account such as a buy, a sell, a dividend, a deposit, a withdrawal, or an advisory fee coming out. Txn_id is the only thing that makes each row unique, since the same client can do the exact same kind of trade in the same security on the same day more than once.

## Part C — Measures

The question I kept asking: if I add this up across clients, across months, or across both, does the total actually mean anything?

### fact_fees

| Column | Type | What that means for summing/averaging |
|---|---|---|
| amount | Additive | It's real money billed, so you can sum it across clients, months, fee types, etc. Total fees is total fees. |
| aum_basis | Semi-additive | It's a balance on a date (it matches the snapshot aum exactly), so you can sum it across clients for one month, but adding January + February just counts the same money twice — use the month-end value or an average over time instead. |
| bps_charged | Non-additive | It's a rate, so adding 65 bps + 70 bps means nothing. If you want the firm's fee rate, take total amount ÷ total aum_basis (an aum-weighted average), not a plain average. |

### fact_portfolio_snapshot

| Column | Type | What that means for summing/averaging |
|---|---|---|
| aum | Semi-additive | Sum it across clients or advisors to get total AUM for a single month, but never across months. 12 snapshots of the same account isn't 12x the money, so use the latest month (or average it over time). |
| return_ytd | Non-additive | A percentage that's also cumulative for the year, so you can't sum it across clients or months. Use the December/latest value for one client, and an aum-weighted average across clients. |
| benchmark_return_ytd | Non-additive | Same deal as return_ytd. It's a YTD percent, so take the latest value in the year and average it (never add it). |
| active_alpha_ytd | Non-additive | It's just return_ytd minus benchmark_return_ytd, so it can't be summed either. Compare weighted-average return to weighted-average benchmark instead of averaging the alphas. |
| cash_pct | Non-additive | A share of the account, so adding 2% + 5% wouldn't make sense. Use an aum-weighted average (cash dollars ÷ total aum) across clients, and don't sum it over months. |

### fact_transactions

| Column | Type | What that means for summing/averaging |
|---|---|---|
| amount | Additive (within a txn_type) | Every amount is positive no matter which direction the money moves, so you can sum it across clients and months for one type (total deposits, total dividends), but summing all types together mixes buys, sells, deposits and withdrawals. Net flow = deposits − withdrawals, not a straight sum. |
| shares | Additive (within a security and txn_type) | Shares bought of one security add up fine across clients and dates, but adding shares of different stocks together, or buys plus sells, gives a number that doesn't mean anything. |
| price | Non-additive | It's a per-share price, so summing it means nothing. If you need an average, weight it by shares (amount ÷ shares), not a plain average. |

### Numeric columns that are NOT measures

- **Keys:** fee_id, snapshot_id, txn_id, client_id, advisor_id, benchmark_id, security_id
- **Date parts:** year, month in fact_portfolio_snapshot
- **Flags:** is_return_suspect (snapshot) and is_post_departure_txn (transactions) 
- **Sneaky one:** account_type looks numeric because one of its values is "529," but it's a category (529 / IRA / Taxable), so it should stay text.

### Numeric attributes in the dimension tables that should never be summed

- **dim_client:** age (total age of all clients means nothing — average it instead), initial_aum (each client's starting AUM is from a different date, so adding them mixes points in time), zip_code (a code, not a number eo keep it as text so the leading zeros don't disappear)
- **dim_advisor:** years_experience (average it, don't add it), aum_target_mm (each advisor's goal — once it's joined to a fact table it repeats on every row and gets added way too many times).
- **dim_security:** expense_ratio_bps (a rate, so average it, weighted by holdings if possible — and it's blank for regular stocks since only ETFs have one).
- **dim_date:** year, quarter, month, week_of_year, plus the flags is_month_end, is_quarter_end, is_year_end, is_trading_day — all for filtering and grouping, never adding.
- **dim_client / dim_security flags:** is_active, is_etf — true/false, so count them, don't sum them.

## Part E — Relationships and design questions

**My model:** 13 relationships, all Many to one (*:1) with Single cross-filter direction, every fact on the many side. 12 are active; the only inactive (dashed) one is dim_client[advisor_id] → dim_advisor[advisor_id]. dim_date is marked as the date table on its date column.

**(a) Why do some transactions have no security_id — and is that a defect?**
Not a defect at all. 101,528 transaction rows have a blank security_id, and every single one of them is a Deposit, a Withdrawal, or an Advisory Fee, which are cash moving in or out of the account with no stock or ETF involved. Meanwhile, every Buy, Sell, and Dividend has a security_id, so the blanks show up exactly where they should and nowhere else. In Power BI those rows show up as a (Blank) security, which is expected structure, not an orphan key — the 0-orphan check in check_keys.py proves every security_id that IS filled in actually exists in dim_security. 

**(b) Which advisor_id relationship(s) did I keep active, and why?**
I kept the three direct ones active (fact_fees, fact_portfolio_snapshot, and fact_transactions straight to dim_advisor) and left dim_client to dim_advisor inactive. Power BI only allows one active path between two tables, and once each fact is connected to both dim_client and dim_advisor, going through dim_client would be a second route to the same place. The direct path is the better one because the advisor_id on a fact row records who was the advisor when that fee, snapshot, or trade actually happened, while dim_client only knows a client's current advisor. Right now they match on every row, but the 2,410 is_post_departure_txn rows show advisors do leave — and if a client ever got reassigned, routing through dim_client would hand all of their old history to the new advisor. Keeping the direct paths active also means one dim_advisor slicer filters all three fact tables, and the inactive one is still there if I ever need it with USERELATIONSHIP in DAX.

**(c) Which date column did I join on, and why?**
I joined all three fact dates (fee_date, snapshot_date, txn_date) to dim_date[date], not dim_date[date_id]. The facts store actual calendar dates like 2020-01-01, not the 1, 2, 3 surrogate numbers, so date_id has nothing to match on. Joining to it would give either an error or a slicer full of (Blank). dim_date[date] is unique so it works fine as the "one" side, and every fact date falls inside that range (0 orphans). It also has to be the date column for Mark as date table, which time-intelligence functions in HW6 will need.

**(d) Star or snowflake — and did I keep it?**
Technically it's a snowflake, because two dimensions point at other dimensions: dim_client to dim_advisor and dim_security to dim_benchmark. I kept both, but in different ways. dim_security to dim_benchmark stays active, since fact_transactions has no benchmark_id of its own. That link is the only way to see trades by the benchmark a security is measured against, and it doesn't create a second path to anything. dim_client to dim_advisor stays in the model but inactive (see b), because the facts already connect to dim_advisor directly. So it's a star at heart with a little snowflake on the security side. Since the assignment says no flattening or new columns, keeping the links as relationships was the way to go.

## Part F — Reflection

**1. fact_fees: "Which advisors made us the most money in fees in 2024, and from what kinds of fees?"**
This one only needs one visual and no DAX. Fee amount is just money, so it adds up no matter how you look at it. Put advisor last_name on the axis, fee_type in the legend, sum the amount, filter the year to 2024, and that's it.

**2. fact_transactions: "How much new money actually came in each month — deposits minus withdrawals?"**
Can't do this one without DAX. Every amount in fact_transactions is positive, even withdrawals, so the only way to tell if money came in or went out is the txn_type label. If you just sum amount, deposits and withdrawals get added together instead of canceling out, which is the opposite of what you want. You'd need a CALCULATE measure to subtract them. The fix would be a tiny dim_transaction_type table with a direction column (+1 for money in, −1 for money out), or just storing withdrawals as negative numbers in the first place. Then net flow is a normal sum and nobody has to write DAX for it.

**3. fact_portfolio_snapshot: "How much has our AUM grown each year, and are clients actually beating their benchmarks?"**
Also can't do this in one visual. AUM is a balance, so if you put year on the axis and sum it, Power BI adds up all 12 monthly snapshots and makes the firm look like it has 12x the money it really does. The returns are even worse: return_ytd and alpha are YTD percentages, so you can't add them, and a plain average treats a $1,000 account the same as an $80 million one. There is also a few outliers. The snapshots are all dated the 1st of the month, but dim_date only flags the last day of the month as month-end, so you can't even use that flag to grab the latest snapshot. To fix it, I'd add an is_period_end flag right on the snapshot table so you can just filter to the last one of each year, and add dollar columns like gain_ytd (aum x return_ytd) so a weighted return becomes simple division. Filtering out is_return_suspect = 1 takes care of the crazy outliers.

**Bottom line:** the model is great at anything that's a flow of money (fees, trades, activity by advisor), but as soon as you ask about balances or performance, you need DAX or a couple of extra columns.