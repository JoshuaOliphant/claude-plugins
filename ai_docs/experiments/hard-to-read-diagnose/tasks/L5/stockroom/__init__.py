"""stockroom: a small multi-warehouse inventory and order desk.

The package is organised in layers:

* ``domain``   - plain dataclasses, errors and unit-of-measure rules
* ``db``       - connection handling, transactions and schema migrations
* ``repo``     - SQL for one table (or view) per module
* ``services`` - business operations that combine repositories
* ``adapters`` - file formats going in (CSV receipts) and out (exports)
* ``utils``    - dates, money and text formatting helpers
"""

__version__ = "2.4.1"
