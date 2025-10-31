#!/usr/bin/env python3
import os
import sys
import subprocess


def resolve_repo_root() -> str:
    """Return absolute path to the repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__)))


def main() -> None:
    repo_root = resolve_repo_root()
    sys.path.insert(0, repo_root)

    import config  # noqa: E402

    device_name = config.DEVICE_NAME
    svd_file = config.SVD_FILE

    # Find run number for the current device in config.user_contexts
    run_number = None
    for ctx in getattr(config, "user_contexts", []):
        if getattr(ctx, "device_name", None) == device_name:
            run_number = str(getattr(ctx, "run"))
            break
    if run_number is None:
        raise RuntimeError(f"Run number not found for device '{device_name}' in config.user_contexts")

    # Build absolute paths
    svd_path = os.path.join(repo_root, "devices", device_name, f"{svd_file}.svd")
    agent_output_folder = os.path.join(repo_root, config.OUTPUT_DIR, device_name, run_number)
    results_directory = os.path.join(repo_root, config.RESULTS_DIR, device_name, run_number, svd_file, f"Generator{config.GENERATOR_ITER}")

    # # 1) compare_agent_output_with_svd.py
    # compare_script = os.path.join(repo_root, "scripts", "compare_agent_output_with_svd.py")
    # subprocess.run([sys.executable, compare_script, svd_path, agent_output_folder, results_directory], check=True)

    # # 2) analyzer.py (uses config internally)
    # analyzer_script = os.path.join(repo_root, "analyzer.py")
    # subprocess.run([sys.executable, analyzer_script], check=True)

    # # 3) generate_analyzer_csv_file.py
    # ids_json_path = os.path.join(repo_root, config.OUTPUT_DIR, device_name, run_number, "analyzer_iteration", svd_file)
    # input_csv_path = os.path.join(results_directory, "register_diff.csv")
    # gen_csv_script = os.path.join(repo_root, "scripts", "generate_analyzer_csv_file.py")
    # subprocess.run([sys.executable, gen_csv_script, ids_json_path, input_csv_path], check=True)

    # # 4) generate_diff_table.py
    # diff_table_script = os.path.join(repo_root, "scripts", "generate_diff_table.py")
    # subprocess.run([sys.executable, diff_table_script, results_directory], check=True)

    # 5) compare_diff_with_verified_output.py
    verified_csv_path = os.path.join(repo_root, "verified_datasheet", f"{device_name}_{svd_file}.csv")
    diff_csv_path = os.path.join(results_directory, "register_diff.csv")
    out_csv_path = os.path.join(results_directory, "register_diff_with_verified_output.csv")
    compare_script = os.path.join(repo_root, "scripts", "compare_diff_with_verified_output.py")
    subprocess.run([sys.executable, compare_script, diff_csv_path, verified_csv_path, out_csv_path], check=True)
    # Additionally, run compare_diff_with_verified_output.py with 'field_diff.csv' instead of 'register_diff.csv'
    field_diff_csv_path = os.path.join(results_directory, "field_diff.csv")
    out_field_csv_path = os.path.join(results_directory, "field_diff_with_verified_output.csv")
    subprocess.run([sys.executable, compare_script, field_diff_csv_path, verified_csv_path, out_field_csv_path], check=True)


if __name__ == "__main__":
    main()


