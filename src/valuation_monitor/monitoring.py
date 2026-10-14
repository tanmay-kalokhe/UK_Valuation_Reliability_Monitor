"""Monthly reliability monitoring (Week 3).

Planned responsibilities:
- Replay past monthly releases in order and score each new month.
- Track prediction error, interval coverage and changes in the input data per area.
- Raise a retraining recommendation only when an area has enough sales and the
  confidence interval on coverage falls below the threshold in config/project_config.yaml.
- Produce the reliability indicator used by the dashboard: accept the automated
  valuation, or refer the property to a surveyor.
"""
