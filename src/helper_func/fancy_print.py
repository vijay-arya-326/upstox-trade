from rich import print, panel, print_json

def fancy_print(msg, boder_weight="bold", border_color="green"):
    print(panel.Panel(msg, border_style=f"{border_color} {boder_weight}"))