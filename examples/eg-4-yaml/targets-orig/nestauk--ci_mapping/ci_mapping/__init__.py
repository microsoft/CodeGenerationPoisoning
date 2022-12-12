import logging
import logging.config
import yaml
from pathlib import Path


# Define project base directory
project_dir = Path(__file__).resolve().parents[1]

# Define log output locations
info_out = str(project_dir / "info.log")
error_out = str(project_dir / "errors.log")

# Read log config file
with open(project_dir / "logging.yaml", "rt") as f:
    logging_config = yaml.safe_load(f.read())
logging.config.dictConfig(logging_config)

# Define module logger
logger = logging.getLogger(__name__)

# Model config
with open(project_dir / "model_config.yaml", "rt") as f:
    config = yaml.safe_load(f.read())
