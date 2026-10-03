import pytest
from pathlib import Path
from licitacoes.config import BASE_DIR, DATA_DIR

def test_base_dir_integrity():
    """Garante que BASE_DIR é a raiz correta e contém arquivos essenciais."""
    assert (BASE_DIR / "licitacoes").is_dir(), f"BASE_DIR {BASE_DIR} deve conter a pasta 'licitacoes'"
    assert (BASE_DIR / "INICIAR.bat").exists(), f"BASE_DIR {BASE_DIR} deve conter 'INICIAR.bat'"

def test_data_dir_location():
    """Garante que a pasta de dados está dentro da raiz."""
    assert DATA_DIR.is_absolute()
    assert DATA_DIR.parent == BASE_DIR

def test_config_path_consistency():
    """Verifica se o config.yaml é resolvido para a raiz independente do CWD."""
    import os
    from licitacoes.config import load_config

    # Simula execução de outra pasta
    original_cwd = os.getcwd()
    try:
        # Tenta mudar para uma pasta temporária ou qualquer outra
        os.chdir(Path(os.environ.get('TEMP', '/tmp')))
        config = load_config("config.yaml")
        assert config is not None
    finally:
        os.chdir(original_cwd)
