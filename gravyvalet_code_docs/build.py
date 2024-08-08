from pathlib import Path

import pdoc


_DOCUMENTED_MODULES = (
    "addon_toolkit",
    "addon_toolkit.interfaces.storage",
    "addon_imps",
    "addon_service",
)


def build_docs(
    output_directory: str = "addon_service/static/gravyvalet_code_docs/",
) -> None:
    pdoc.render.configure(
        # mermaid=True,
        template_directory=_custom_pdoc_template_dir(),
    )
    # include the top-level readme for the index page
    pdoc.render.env.globals["gravyvalet_readme"] = _gv_readme()
    pdoc.pdoc(*_DOCUMENTED_MODULES, output_directory=Path(output_directory))


def _this_directory() -> Path:
    return Path(__file__).resolve().parent


def _custom_pdoc_template_dir() -> Path:
    """where custom pdoc templates live

    see https://github.com/mitmproxy/pdoc/blob/main/examples/custom-template/README.md
    """
    return _this_directory() / "custom_pdoc_templates"


def _gv_readme() -> str:
    with open(_this_directory().parent / "README.md") as _readme:
        return _readme.read()


if __name__ == "__main__":
    import os

    import django  # type: ignore[import-untyped]

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
    django.setup()
    build_docs()
