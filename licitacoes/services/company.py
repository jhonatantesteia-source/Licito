import yaml
from pathlib import Path
from licitacoes.config import settings, Config

class CompanyService:
    """Service to manage company configuration."""

    @staticmethod
    def update_company_data(data: dict):
        # Update config.yaml
        current_config = load_config()
        current_config.company = Config.CompanyConfig(**data)

        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(current_config.model_dump(), f, default_flow_style=False)

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return Config(**yaml.safe_load(f))
