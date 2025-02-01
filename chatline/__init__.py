from pkgutil import iter_modules
from importlib import import_module

__all__ = []
for m in [import_module(f'.{m.name}', __name__) for m in iter_modules(__path__) if not m.name.startswith('_')]:
    __all__.extend(getattr(m, '__all__', [n for n in dir(m) if not n.startswith('_')]))
    locals().update({n: getattr(m, n) for n in dir(m) if not n.startswith('_')})