from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _load_all_models() -> None:
    import importlib
    import pkgutil
    from app import models as _models_pkg

    for m in pkgutil.iter_modules(_models_pkg.__path__):
        importlib.import_module(f"{_models_pkg.__name__}.{m.name}")


_load_all_models()