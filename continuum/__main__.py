"""Laboratory by default; historical demo/benchmark commands remain available."""
import sys
if len(sys.argv)>1 and sys.argv[1] in ('demo','benchmark'):
    from .cli import main
else:
    from .lab.__main__ import main
main()
