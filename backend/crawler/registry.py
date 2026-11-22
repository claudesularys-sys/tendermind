import importlib
from pathlib import Path
from .base import BaseCrawler

_registry: dict[str, BaseCrawler] = {}


def _discover():
    sources_dir = Path(__file__).parent / "sources"
    for region_dir in sorted(sources_dir.iterdir()):
        if not region_dir.is_dir():
            continue
        for py_file in sorted(region_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_path = f"crawler.sources.{region_dir.name}.{py_file.stem}"
            try:
                mod = importlib.import_module(module_path)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseCrawler)
                        and attr is not BaseCrawler
                        and getattr(attr, "source_id", "")
                    ):
                        instance = attr()
                        _registry[instance.source_id] = instance
            except Exception as e:
                print(f"[registry] Failed to load {module_path}: {e}")


def get_all_crawlers() -> dict[str, BaseCrawler]:
    if not _registry:
        _discover()
    return _registry


def get_crawler(source_id: str) -> BaseCrawler | None:
    return get_all_crawlers().get(source_id)
