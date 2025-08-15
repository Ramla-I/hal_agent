from defs import UserContext

def update_user_contexts(user_contexts: list[UserContext], device_name: str):
    """
    Update the user_contexts list in config.py with the new list provided.

    Args:
        user_contexts (list[UserContext]): The updated list of UserContext objects.

    This function will overwrite the user_contexts variable in config.py with the new list.
    """

    config_path = "config.py"

    # Prepare the string to write
    lines = []
    lines.append("from defs import UserContext, Manufacturer\n")
    lines.append(f"DEVICE_NAME = {repr(device_name)}\n")
    lines.append("user_contexts = [\n")
    for ctx in user_contexts:
        # Format manufacturer as Manufacturer.INTEL or Manufacturer.STM
        manufacturer_str = f"Manufacturer.{ctx.manufacturer.name}"
        # Format svd_path as a list of repr strings
        svd_path_str = "[" + ", ".join(repr(p) for p in ctx.svd_path) + "]"
        # Format run as int or str
        run_str = repr(ctx.run)
        # Compose the UserContext line
        lines.append(
            f"    UserContext(device_name={repr(ctx.device_name)}, "
            f"peripheral_name={repr(ctx.peripheral_name)}, "
            f"manufacturer={manufacturer_str}, "
            f"driver_path={repr(ctx.driver_path)}, "
            f"datasheet_path={repr(ctx.datasheet_path)}, "
            f"datasheet_sections_directory={repr(ctx.datasheet_sections_directory)}, "
            f"svd_path={svd_path_str}, "
            f"run={run_str}, "
            f"file_id={repr(ctx.file_id)}, "
            f"vs_id={repr(ctx.vs_id)}),\n"
        )
    lines.append("]\n")

    # Write to config.py
    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
