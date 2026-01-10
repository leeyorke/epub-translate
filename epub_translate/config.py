from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    base_url: str = ""
    api_key: str = ""
    model: str = ""


def get_config() -> Config:
    config_path = Path.home() / ".epub_translate_config"
    config = ConfigParser()
    if config_path.exists():
        config.read(config_path)
    else:
        raise RuntimeError("You need to configure model first.")

    return Config(
        base_url=config.get("OpenAI", "base_url", fallback=""),
        api_key=config.get("OpenAI", "api_key", fallback=""),
        model=config.get("OpenAI", "model", fallback=""),
    )


def set_config(base_url: str, api_key: str, model: str) -> None:
    config_path = Path.home() / ".epub_translate_config"
    config = ConfigParser()
    if config_path.exists():
        config.read(config_path)
    config["OpenAI"]["base_url"] = base_url
    config["OpenAI"]["api_key"] = api_key
    config["OpenAI"]["model"] = model

    with config_path.open("w") as config_file:
        config.write(config_file)
    print("The AI model configure succeseul!")
