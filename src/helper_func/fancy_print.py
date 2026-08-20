from rich import print, panel, print_json

def fancy_print(msg, boder_weight="bold", border_color="green", title="Info"):
    if title.lower() =="info" and border_color == "red":
        title = "Error"
    elif title.lower() =="info" and  border_color in ["yellow", "bright_yellow"]:
        title = "Warning"

    print(panel.Panel(msg, border_style=f"{border_color} {boder_weight}",title=title))