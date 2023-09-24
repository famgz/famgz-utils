from rich.console import Console
_console = Console(highlight=False, soft_wrap=True)

print = _console.print
rule = _console.rule
input = _console.input

_void = lambda *args, **kwargs: None
disable_print = _void
enable_print = print
