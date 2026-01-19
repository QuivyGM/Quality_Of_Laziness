import os
import shutil

def collect_project_files(project_root, output_folder):
    """
    Recursively copy files from project_root to output_folder based on:
    - Allowed INCLUDE_EXTENSIONS
    - Blocked EXCLUDE_FILENAMES (exact matches like __init__.py)
    """

    # Configure what to include or exclude
    INCLUDE_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".md"}
    EXCLUDE_FILENAMES = {"__init__.py"}

    # 1. Clean output folder
    if os.path.exists(output_folder):
        for filename in os.listdir(output_folder):
            path = os.path.join(output_folder, filename)
            if os.path.isfile(path) or os.path.islink(path):
                os.unlink(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
    else:
        os.makedirs(output_folder, exist_ok=True)

    tree_file = os.path.join(output_folder, "project_tree.txt")

    # 2. Start tree file
    with open(tree_file, "w", encoding="utf-8") as f:
        f.write(f"PROJECT_ROOT: {project_root}\n\n")

        # Walk through project and collect files
        for dirpath, _, filenames in os.walk(project_root):
            rel_dir = os.path.relpath(dirpath, project_root)
            copied_files = []

            for file in filenames:
                # Check exclusion first
                if file in EXCLUDE_FILENAMES:
                    continue

                # Check extension
                ext = os.path.splitext(file)[1].lower()
                if ext not in INCLUDE_EXTENSIONS:
                    continue

                src = os.path.join(dirpath, file)
                dst = os.path.join(output_folder, file)

                # Avoid overwriting duplicates
                if os.path.exists(dst):
                    name, ext = os.path.splitext(file)
                    i = 1
                    while os.path.exists(os.path.join(output_folder, f"{name}_{i}{ext}")):
                        i += 1
                    dst = os.path.join(output_folder, f"{name}_{i}{ext}")

                shutil.copy2(src, dst)
                copied_files.append(os.path.basename(dst))
                print(f"Copied: {src} → {dst}")

            # Write tree summary for dirs that had copied files
            if copied_files:
                f.write(f"{rel_dir if rel_dir != '.' else os.path.basename(project_root)}:\n")
                for file in copied_files:
                    f.write(f"  - {file}\n")

    print(f"\nProject tree saved to: {tree_file}")


# Example usage
project_root = r"C:\Users\path"
output_folder = r"C:\Users\path"

collect_project_files(project_root, output_folder)
