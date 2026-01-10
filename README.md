<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/SpaceShaman/epub-translate/refs/heads/master/assets/logo-light.png" width="100" alt="epub-translate">
    <img src="https://raw.githubusercontent.com/SpaceShaman/epub-translate/refs/heads/master/assets/logo-dark.png" width="100" alt="epub-translate">
  </picture>
  <p><strong>epub-translate:</strong> a simple cli tool for translating ebooks in EPUB format into any language</p>
</div>

----

## Introduction

Translating a book takes about 10 minutes.

## develop

Use UV to develop this project.

### create a venv

```bash
uv venv
```

### editable mode

```bash
uv pip install -e .
```

### Usage
```bash
(epub-translate) ~$ epub-translate --help
[*^_^*] EbookLib patch applied successfully - head tags will now be preserved!

 Usage: epub-translate [OPTIONS] COMMAND [ARGS]...

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                                                                  │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.                                           │
│ --help                        Show this message and exit.                                                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ translate                                                                                                                                                │
│ configure                                                                                                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Reference
Forked from https://github.com/SpaceShaman/epub-translate