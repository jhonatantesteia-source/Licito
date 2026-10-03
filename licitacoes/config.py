import yaml
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

# Define the project root once and for all
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class OllamaConfig(BaseModel):
    url: str
    model_extraction: str
    model_analysis: str
    temperature: float
    timeout: int

class CompanyConfig(BaseModel):
    razao_social: str
    cnpj: str
    endereco: str
    telefone: str
    email: str
    dados_bancarios: str
    porte: str

class PathsConfig(BaseModel):
    output_dir: str
    temp_dir: str

class Config(BaseModel):
    ollama: OllamaConfig
    paths: PathsConfig
    company: CompanyConfig

def load_config(config_path: str = "config.yaml") -> Config:
    # Use absolute path if relative
    path = Path(config_path)
    if not path.is_absolute():
        path = BASE_DIR / config_path

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config(**data)

# Global config instance
settings = load_config()
