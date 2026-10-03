# Data guide

Shift Signal reads two kinds of CSV file. Both downloads in the app's **Data guide** page are complete, fictional starting points: a portfolio template and a full launch panel.

All CSV files must be UTF-8 (a byte-order mark is fine), have a header row, use a comma or semicolon delimiter and use decimal points. The upload limit is 1000 MB and 5,000,000 rows. Blank numbers are rejected rather than treated as zero.

## Launch planner: one row per incumbent item

| item | units | price | unit_cost | overlap |
|---|---|---|---|---|
| Classic burger | 1400 | 169 | 60 | 0.90 |
| House salad | 650 | 149 | 48 | 0.10 |

- `item`: unique, nonblank name. At most 100 incumbent items in one comparable choice set.
- `units`: baseline volume in the declared planning period (for example four weeks).
- `price`: net selling price per comparable unit.
- `unit_cost`: all variable costs per comparable unit (food or goods cost, preparation, fulfilment, channel fees you can attribute per unit).
- `overlap`: your relative substitution weight from 0 to 1. `0` excludes an item from giving up volume; `1` gives it the strongest weight. It is an assumption, not a probability or a fitted elasticity.

All numbers must be finite and nonnegative. The launch item itself (name, expected units, price, variable cost, cannibalization share, total incremental launch cost) is entered in the app, not in the CSV. Its name must differ from every incumbent. You can also edit the table directly in the app.

**Keep units comparable.** In menu mode, compare substitutes within one meal occasion, such as mains. A burger and a side can be complements, which this planner does not model. In product mode, convert pack sizes into equivalent units before upload, or read revenue and contribution instead of unit rates.

## Launch evidence: one row per date × location × item

| date | location | group | item | units | price | unit_cost |
|---|---|---|---|---|---|---|
| 2026-04-27 | test-01 | test | Smoky mushroom burger | 42 | 189 | 72 |
| 2026-04-27 | control-01 | control | Smoky mushroom burger | 0 | 189 | 72 |

- `date`: `YYYY-MM-DD`, without a time. One complete daily or weekly calendar with equally spaced dates.
- `location`: a stable identifier for an independent restaurant, store or other assignment unit.
- `group`: exactly `test` or `control`, and constant for each location throughout the study.
- `item`: the launch item and between 1 and 99 incumbent items.
- `units`: finite, nonnegative sales volume. Use explicit zeros only for verified zero sales.
- `price`, `unit_cost`: average realised price and variable cost per unit for that row, unit-weighted when you aggregate transactions. Zero-sales rows still need a finite price and cost.

The panel is rejected, with a message saying why, when:

- a date/location/item combination is missing or duplicated (missing periods are not zeros);
- the calendar is not daily or weekly, or has gaps;
- the launch date is not a period start present in the data;
- there are fewer than 4 pre-launch or 4 post-launch periods;
- either group has fewer than 4 locations (10 or more is preferable);
- a location switches group;
- the launch item has sales before launch or in a control location, or no post-launch sales at all.

The app also caps the analysis at 5,000,000 rows; aggregate daily data to weeks or drop unrelated items if a panel is larger. Every step aggregates to location level before the bootstrap, so large panels stay fast. It does not remove outliers or impute missing values.

## Before you upload

1. Define one comparable choice set and convert pack sizes to equivalent units.
2. Choose independent test and control locations with comparable trends. Randomise where practical.
3. Use one common launch date and at least four periods on either side. Longer comparable windows are better.
4. Review price changes, promotions, holidays, distribution changes, stockouts, spillovers between nearby locations and kitchen or shelf capacity. Any of them can invalidate the comparison.

Staggered launches, changing assortments, basket effects and a single location with ordinary sales history need a different study design. The planner still works for those cases; the historical comparison does not.
