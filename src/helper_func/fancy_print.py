from rich import print, panel, print_json

def fancy_print(msg, border_weight="bold", border_color="green", title="Info", bg_color:str=None, title_color:str="black"):
    if title.lower() =="info" and border_color == "red":
        title = "Error"
    elif title.lower() =="info" and  border_color in ["yellow", "bright_yellow"]:
        title = "Warning"
    panel_kwargs = {
        "border_style": f"{border_color} {border_weight}",
        "title": title,
    }

    if bg_color:
        panel_kwargs["style"] = f"on {bg_color}"
    else:
        panel_kwargs["style"] = f"on {border_color}"

    print(panel.Panel(msg, **panel_kwargs))