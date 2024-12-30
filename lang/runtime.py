from lang.parser import Parser
from lang.translator import Translator
import importlib
import importlib.util
import sys

def init():
    try:
        import fishhook
        def foreach(self, func):
            for i in self:
                func(i)
        def foreach_dict(self, func):
            for pair in self.items():
                func(*pair)
        
        fishhook.hook(list)(foreach)
        fishhook.hook(tuple)(foreach)
        fishhook.hook(set)(foreach)
        fishhook.hook(dict, name="foreach")(foreach_dict)
    except ImportError as e:
        if e.name != "fishhook":
            raise e from None
        import warnings
        warnings.warn(RuntimeWarning("Could not import fishhook. Some standard features will not be available."))

def import_module_from_radon_string(name: str, source: str, filename: str):
    try:
        parser = Parser(source)
        ast = parser.run()
    except AssertionError as e:
        raise SyntaxError(*e.args) from None

    pyast = Translator().run(ast)
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(pyast, filename, "exec"), module.__dict__)
    sys.modules[name] = module
    globals()[name] = module

    return module

def import_module_from_radon_file(names: list[str], as_name: str):
    if as_name is None:
        as_name = ".".join(names)
    filename = "/".join(names) + ".rad"
    return import_module_from_radon_string(as_name, open(filename).read(), filename)

def import_module_generic(names: list[str], as_name: str):
    if as_name is None:
        as_name = ".".join(names)
    try:
        return import_module_from_radon_file(names, as_name)
    except FileNotFoundError:
        return importlib.import_module(".".join(names), package=None)
    