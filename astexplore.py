import ast
import traceback
import sys

if len(sys.argv) > 1:
    with open(sys.argv[1]) as f:
        print(ast.dump(ast.parse(f.read())))
else:
    while True:
        try:
            print(ast.dump(ast.parse(input(">>> "))))
        except (EOFError, KeyboardInterrupt):
            print()
            break
        except:
            traceback.print_exc()