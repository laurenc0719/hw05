# Power BI Guide — Loading Your Clean Tables and Building the Star Schema
### MIS3060 HW5, Part D | Power BI Desktop on the Apporto virtual desktop

This guide shows the **mechanics**. Which column is a primary key, which are foreign keys, and how each measure behaves is your analysis (HW5 Parts A to C). You load the clean tables **as they are**: no surrogate keys, no new tables.

## 0. Get your files onto the virtual desktop
Upload the `Wildcat Capital Clean` folder (the eight CSVs) to the Apporto drive. Power BI cannot read your laptop's folders directly.

- Save your `.pbix` to the **persistent** drive, not the desktop of the session, and keep a copy on your own computer
- The virtual desktop is shared and can be slow near the due date. Start early

## 1. Load the tables
1. **Home → Get data → Text/CSV** → select a file → **Transform Data** (not Load).
2. In Power Query, check every column type. Fix these every time:
   - **Keys** (`*_id`) → **Whole Number**. `fact_transactions[security_id]` is blank on cash rows; that is expected, keep it Whole Number
   - **Dates** (`date`, `txn_date`, `fee_date`, `snapshot_date`, `client_since`) → **Date** (not Date/Time)
   - **Amounts, AUM, prices, returns** → **Decimal Number** (or Fixed decimal)
   - **`dim_client[zip_code]`** → **Text**, or leading zeros are lost
   - **`is_active`** → **True/False**; the `is_*` flag columns → Whole Number
3. Repeat for all eight tables, then **Close & Apply**.

> Power BI guesses types from the first 200 rows. A wrong guess silently breaks a relationship later, so always check.

## 2. Build the relationships (Model view)
1. Open **Model view** (left rail, third icon). Power BI will auto-detect some relationships. **Delete any you did not design.**
2. Create each relationship by dragging the **foreign key** (many side) onto the **primary key** (one side).
3. For every relationship set:
   - **Cardinality:** *Many to one (\*:1)*, with the fact on the many side
   - **Cross-filter direction:** *Single* (the dimension filters the fact)
   - **Make this relationship active:** yes, unless it creates a second path to a dimension that is already reachable (see below)
4. Arrange the model with the dimensions around the facts so the picture looks like a star.

**Joining to the date table.** The facts store calendar dates, so join the fact's date column to `dim_date[date]`, not to `dim_date[date_id]`. The three date columns are `fact_transactions[txn_date]`, `fact_fees[fee_date]` and `fact_portfolio_snapshot[snapshot_date]`.

**Only one active path between two tables.** If a dimension can be reached two ways (for example `dim_advisor` directly from a fact and also through `dim_client`), Power BI keeps only one active and marks the other with a dashed line. Decide which one you want and be ready to explain it (HW5 Part E, question b).

**If Power BI refuses a relationship or shows a warning:** read it. "Many-to-many" means the key is not unique on the one side. A dashed line means the relationship is inactive.

## 3. Mark the date table
Select `dim_date` → **Table tools → Mark as date table** → pick the `date` column. Time-intelligence functions need this.

## 4. Check what the model shows
- **Row counts:** put a **card** visual on a report page for each table showing **Count** of its primary key (or a `COUNTROWS` measure, the one DAX measure allowed here), and compare with the row counts in the handout. If they differ, find out why before you build anything else
- **Blank members:** drag `dim_security[ticker]` onto a table visual with `fact_transactions` amount. A `(Blank)` row is the cash rows (deposits, withdrawals, advisory fees), which have no security. That is expected structure, not a broken relationship. Any other `(Blank)` means an orphan key
- **Slicers:** a slicer on `dim_advisor` should filter all three fact tables. If it filters none, check the relationship direction and the key types

## 5. Measures come next
Apart from the row counts, do not write DAX measures for this assignment. Save your model as `powerbi/hw05.pbix` and submit it; you will add measures to it in ICE 9, ICE 10 and Assignment 6 (see `Homework/Assignment 6/powerbi_dax_guide.md`).

## 6. Files to submit
- `powerbi/hw05.pbix` — the saved model (Brightspace upload if over 100 MB)
- `powerbi/model_view.png` — Model view, every table and relationship visible, no overlapping lines

## Troubleshooting
| Symptom | Likely cause |
|---|---|
| A slicer filters nothing | Relationship direction wrong, relationship inactive, or the key is Text on one side and Whole Number on the other |
| `(Blank)` row on a dimension | The fact has a key with no match in the dimension (an orphan), or a legitimately blank key such as `security_id` on cash rows |
| Totals are far too large | A balance (AUM) was summed across months, or a many-to-many join duplicated rows |
| Date slicer shows `(Blank)` | Fact date outside the date table's range, or the join used `date_id` instead of `date` |
| A relationship is dashed | It is inactive; usually a second path to the same dimension |
| Zip codes lost leading zeros | The column was loaded as a number; change it to Text in Power Query |

