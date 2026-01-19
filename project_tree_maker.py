import os
import sys

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

# 1. Set your project root folder here
# NOTE: Replace "path to root" with a valid directory path (e.g., r"/home/user/my_project")
TARGET_ROOT = r"/home/user/my_project"

# 2. Set markdown output file name
OUTPUT_MD = "project_tree.md"

# 3. Ignored folders and file patterns (case-insensitive)
IGNORE_FOLDERS = {
    ".idea", "__pycache__", ".vscode", ".git", ".venv", "node_modules"
}

IGNORE_FILES = {
    ".DS_Store", "thumbs.db", OUTPUT_MD.lower()
}
# ---------------------------------------------------------

# ASCII Art Constants
BRANCH      = "├─ "
LAST_BRANCH = "└─ "
VERTICAL    = "│"
INDENT_SPACE= "   " # Three spaces for horizontal indentation
PIPE_SPACE  = "│  " # Vertical line followed by two spaces


def is_ignored(name):
    """Checks if a file or folder name should be ignored."""
    lower = name.lower()
    return lower in IGNORE_FOLDERS or lower in IGNORE_FILES or lower.startswith('.')


def scan_and_print_tree(path, prefix, lines):
    """
    Recursively scans the directory and populates the lines list with the tree structure.
    
    The entries are sorted alphabetically with files listed before directories.
    Vertical spacing lines are added between files/folders and after folder subtrees.

    :param path: The current directory path being scanned.
    :param prefix: The string prefix indicating the tree structure depth (e.g., '│  │  ').
    :param lines: The list to append the formatted tree lines to.
    """
    try:
        # 1. Get all non-ignored entries
        all_entries = [e for e in os.listdir(path) if not is_ignored(e)]
    except PermissionError:
        lines.append(f"{prefix}└─ [Permission Denied]")
        return
    except FileNotFoundError:
        return

    files = []
    directories = []

    # 2. Separate entries into files and directories
    for entry in all_entries:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            directories.append(entry)
        else:
            files.append(entry)
    
    # 3. Sort both lists alphabetically
    files.sort()
    directories.sort()

    # 4. Combine: Files first, then directories
    entries = files + directories
    total = len(entries)
    num_files = len(files)

    for i, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        is_last_child = (i == total - 1)
        is_dir = os.path.isdir(full_path) # Check if it's a directory

        connector = LAST_BRANCH if is_last_child else BRANCH
        
        # Append '/' to directory names
        display_name = entry + ("/" if is_dir else "")
        lines.append(prefix + connector + display_name)

        if is_dir:
            # Calculate the prefix for the next level
            # If the current directory is the last sibling, use blank spaces (INDENT_SPACE)
            # otherwise, continue the vertical line (PIPE_SPACE)
            new_prefix = prefix + (INDENT_SPACE if is_last_child else PIPE_SPACE)

            # Recurse into the subdirectory
            scan_and_print_tree(full_path, new_prefix, lines)

            # Logic 2: Spacing after directory subtree:
            # If this directory is not the last sibling, add a vertical line
            # to separate its subtree from the next sibling.
            if not is_last_child:
                lines.append(prefix + VERTICAL)
            
        else: # It's a file
            # Logic 1: Spacing between file block and directory block
            # Check if this file is the last file in the file group AND there are directories to follow.
            # i == num_files - 1 identifies the last file index.
            if i == num_files - 1 and directories:
                # Add an empty line with the current prefix's verticality
                lines.append(prefix + VERTICAL)


def main():
    """Main function to initiate the tree scan and file output."""
    root = TARGET_ROOT

    if root == r"path to root":
        print("ERROR: TARGET_ROOT is set to the placeholder 'path to root'.")
        print("Please edit tree_scanner.py and set TARGET_ROOT to a valid directory.")
        
        # Write instructions to the markdown file instead of an empty tree
        lines = [
            "# Project Tree Generation Failed",
            "## Instructions",
            f"Please open `{os.path.basename(__file__)}` and update the `TARGET_ROOT` variable",
            "with the absolute or relative path of the directory you wish to scan.",
            f"Example: `TARGET_ROOT = r'/Users/YourName/Documents/MyProject'`"
        ]
        
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Instructions saved to {OUTPUT_MD}.")
        sys.exit(1)


    if not os.path.exists(root):
        print(f"ERROR: Root path not found: {root}")
        sys.exit(1)


    lines = []
    
    # Get the display name for the root folder
    root_name = os.path.basename(os.path.normpath(root))
    if not root_name:
         # Handle case where root is just '/' or 'C:\'
        root_name = os.path.normpath(root)
        if root_name.endswith(os.sep):
            root_name = root_name[:-1]
    
    # Root name must always end with '/'
    lines.append(root_name + "/")
    
    # Start the recursive scan with an empty prefix
    scan_and_print_tree(root, "", lines)

    # Wrap the output in markdown code block
    md_text = "```\n" + "\n".join(lines) + "\n```"

    try:
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(md_text)
        print(f"\nSuccessfully scanned directory and saved output to: {OUTPUT_MD}")
    except Exception as e:
        print(f"\nError writing to output file {OUTPUT_MD}: {e}")


if __name__ == "__main__":
    main()
