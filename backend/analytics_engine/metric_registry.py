import yaml
from pathlib import Path
from utils.logger import get_logger

logger = get_logger("metric_registry")

class MetricRegistry:
    def __init__(self, path="config/metric_definitions.yaml"):
        self.metrics = {}
        try:
            if Path(path).exists():
                with open(path) as f:
                    config = yaml.safe_load(f)
                    if config and "metrics" in config:
                        self.metrics = config["metrics"]
        except Exception as e:
            # Gracefully handle missing or invalid metric files
            logger.warning("Could not load metrics: %s", e)
            self.metrics = {}

    def is_valid_metric(self, metric_name: str) -> bool:
        return metric_name in self.metrics

    def get_metric(self, metric_name: str) -> dict:
        if not self.is_valid_metric(metric_name):
            raise ValueError(f"Metric '{metric_name}' is not registered")
        return self.metrics[metric_name]

    def list_metrics(self):
        return list(self.metrics.keys())
