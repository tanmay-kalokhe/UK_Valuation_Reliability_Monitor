"""Baseline valuation (Week 2).

The baseline is the median price of comparable sales (same postcode district within the local
authority, same property type, the 12 months before the information cut-off), each indexed to
the cut-off with the local-authority UK HPI for its type. With fewer than the configured
minimum of comparables, the local-authority median for the type is used instead.

It is computed in SQL (sql/03_features/03_feat_baseline.sql) because it is a windowed median
over earlier sales; this module only reads it. Machine-learning models must beat it to justify
themselves (decision D-004). Because it uses only public sales before the cut-off, the same
baseline applies to the time split and to the local-authority holdout.
"""

import numpy as np
import pandas as pd


def baseline_estimate(model_input: pd.DataFrame) -> np.ndarray:
    """The baseline estimate (£) for each row of model_input."""
    return model_input["baseline_estimate"].to_numpy(dtype=float)
