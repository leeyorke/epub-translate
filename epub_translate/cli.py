from typer import Argument, Option, Typer
from typing_extensions import Annotated

from .config import set_config
from .translator import translate_epub

app = Typer()


@app.command()
def translate(
    file_path: Annotated[
        str, Argument(help="Path to the EPUB file to translate, e.g., 'book.epub'.")
    ],
    target_language: Annotated[
        str,
        Argument(help="Target language code for translation, e.g., 'pl' for Polish."),
    ],
    debug: Annotated[
        bool,
        Option(help="open debug mode.", show_default=False),
    ] = False,
) -> None:
    translate_epub(file_path, target_language, debug)


@app.command()
def configure(
    base_url: Annotated[
        str,
        Option(
            help="API base url to use for translation.",
            show_default=False,
        ),
    ],
    api_key: Annotated[
        str,
        Option(
            help="API key to use for translation.",
            show_default=False,
        ),
    ],
    model: Annotated[
        str,
        Option(
            help="model to use for translation.",
            show_default=False,
        ),
    ],
) -> None:
    set_config(base_url, api_key, model)
