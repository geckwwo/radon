import sys
import io
import ast as pythonast
import traceback
from lang.parser import Parser
from lang.translator import Translator

VER = (0, 1)
SVER = ".".join(map(str, VER))

def format_syntaxerr(source, parser, filename, e):
    lines = source.split('\n')
    line = parser.tok.line if parser.tok.line != -1 else len(lines)
    coloffset = parser.tok.offset if parser.tok.line != -1 else len(lines[-1])
    n = ""
    n += (f"  File {repr(filename)}, line {line}\n")
    n += (f"    {lines[line - 1]}\n")
    n += (f"    {' ' * (coloffset-1)}^\n")
    n += f"SyntaxError: " + ", ".join(map(repr, e.args))
    return n

import lang.runtime
lang.runtime.init()

globals()["_global_radon_se_import"] = lang.runtime.import_module_generic

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            source = (open(sys.argv[1]).read())
            parser = Parser(source)
            ast = parser.run()
        except AssertionError as e:
            sys.stderr.write(format_syntaxerr(source, parser, sys.argv[1], e))
            sys.stderr.write("\n")
            sys.stderr.flush()
            exit(1)

        pyast = Translator().run(ast)
        if "--debug-radon-unparse" not in sys.argv:
            try:
                exec(compile(pyast, sys.argv[1], "exec"))
            except:
                # this omits the bottom stack frame
                # otherwise it looks something like this:
                
                #   Traceback (most recent call last):
                # >  File "/home/geckwwo/projects/radon/radon.py", line 12, in <module>
                # >   exec(compile(pyast, sys.argv[1], "exec"))
                #    File "examples/hello.rad", line 2, in <module>
                #      1/0;
                #     
                #   ZeroDivisionError: division by zero

                # TODO: temporarily disabled because it's not working correctly sometimes
                #x = io.StringIO()
                #traceback.print_exc(file=x)
                #sys.stderr.write("\n".join(x.getvalue().split("\n")[:1] + x.getvalue().split("\n")[3:]))
                #sys.stderr.flush()
                traceback.print_exc()
                exit(1)
        else:
            print(pythonast.unparse(pyast))
    else:
        print(f"Radon Interactive Shell v{SVER}")
        while True:
            try:
                src = input(">>> ")
            except (KeyboardInterrupt, EOFError):
                print()
                exit(0)
            
            try:
                parser = Parser(src)
                ast = parser.run()
            except AssertionError as e:
                print(format_syntaxerr(src, parser, "<stdin>", e))
                continue
            pyast = Translator().run(ast)
            try:
                if len(pyast.body) > 1:
                    exec(compile(pyast, "<stdin>", "exec"))
                else:
                    if isinstance(pyast.body[0], pythonast.Expr):
                        if (rv := eval(compile(pythonast.Expression(pyast.body[0].value), "<stdin>", "eval"))) is not None:
                            print(repr(rv))
                    else:
                        exec(compile(pyast, "<stdin>", "exec"))
            except:
                # TODO: same thing over there
                #x = io.StringIO()
                #traceback.print_exc(file=x)
                #data = "\n".join(x.getvalue().split("\n")[:1] + x.getvalue().split("\n")[3:])
                #sys.stderr.write(data)
                #sys.stderr.flush()
                traceback.print_exc()