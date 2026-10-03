import yaml
from licitacoes.config import BASE_DIR, Config, CompanyConfig

CONFIG_PATH = BASE_DIR / "config.yaml"
EXAMPLE_PATH = BASE_DIR / "config.example.yaml"


def load_config() -> Config:
    """Lê o config.yaml; na primeira execução, usa o modelo de exemplo."""
    path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_PATH
    with open(path, "r", encoding="utf-8") as f:
        return Config(**(yaml.safe_load(f) or {}))


def save_config(cfg: Config) -> None:
    """Grava de forma segura (arquivo temporário + troca), com acentos legíveis."""
    tmp = CONFIG_PATH.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg.model_dump(mode="json"), f,
                       allow_unicode=True, default_flow_style=False, sort_keys=False)
    tmp.replace(CONFIG_PATH)


class CompanyService:
    """Gerencia os dados da empresa (config.yaml na raiz do projeto)."""

    @staticmethod
    def get_company_data() -> CompanyConfig:
        return load_config().company

    @staticmethod
    def update_company_data(data: dict) -> None:
        cfg = load_config()
        cfg.company = CompanyConfig(**data)   # valida pelo pydantic
        save_config(cfg)