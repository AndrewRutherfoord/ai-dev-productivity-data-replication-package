import yaml
import json
from datetime import datetime

from common.models.driller_config import DrillConfig


class DateTimeEncoder(json.JSONEncoder):
    date_format = "%Y-%m-%d %H:%M:%S"

    def default(self, obj):
        if isinstance(obj, datetime):
            # Convert datetime object to a string
            return obj.strftime(self.date_format)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def load_yaml(path):
    with open(path, "r") as ymlfile:
        content = yaml.load(ymlfile, Loader=yaml.FullLoader)
    return content


def parse_config(config: dict) -> DrillConfig:
    return DrillConfig.validate_model(config)
