# aws-cleanup

## Requirements
- [Python 3.8+](https://www.python.org/)
- Install required Python libs: `python3 -m pip install -r requirements.txt`

## Python Script
```
python3 main.py --help
usage: main.py [-h] [--config CONFIG] [--run-date RUN_DATE] [--dry-run] [--full] [--override-stop-date] [--debug]

AWS Cleanup Script

options:
  -h, --help            show this help message and exit
  --config CONFIG       Set YAML configuration file (default is `config/default_config.yaml`)
  --run-date RUN_DATE   Set run date (ISO format i.e., yyyy-mm-dd)
  --dry-run             Dry run, no tag changes of stop/terminate instances
  --full                Go through all AWS regions (if not set it will use YAML config `override.test_region_override`)
  --override-stop-date  Override stop date (Not implemented yet)
  --debug               Set logging as DEBUG (default is INFO)
  ```