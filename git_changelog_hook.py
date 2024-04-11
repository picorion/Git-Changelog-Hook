import argparse
import json
import re
import os.path
from datetime import datetime as dt

# --- default notice and regex patterns ---

NOTICE = """All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)."""

CHANGE_TYPES = {
    "Added": "Add(ed)?(s)?",
    "Changed": "Change(d)?(s)?",
    "Deprecated": "Deprecate(d)?(s)?",
    "Removed": "Remove(d)?(s)?",
    "Fixed": "Fix(ed)?(es)?",
    "Security": "Security"
}

CHANGELOG_INDICATOR = "((Changelog)|(Change(s)?)):.*"

TIMESTAMP_FORMAT = "%Y-%m-%d"

# appends additional details to the changelog entries
SHOW_ADDITIONAL_INFO = True
ADDITIONAL_INFO = " ~ {author} ({timestamp})"

# --- node class for tree representation and functions ---

class Node:
    """Represents a parsed markdown header with related text as content and sub-headers as children."""
    def __init__(self, value):
        # the heading itself as string
        self.value: str = value
        # hierarchy of the node, determined by the amount of "#"
        self.level: int = value.count("#")
        self.contents: list[str] = []
        self.children: "Node" = []
        self.parent: "Node" = None
        
    def append_content(self, content):
        self.contents.append(content)
    
    def append_child(self, child):
        self.children.append(child)
        child.set_parent(self)

    def prepend_child(self, child):
        self.children.insert(0, child)
        child.set_parent(self)

    def set_parent(self, parent):
        self.parent = parent
    
    def __repr__(self) -> str:
        return f"{self.value}"


def parse_changelog(file_path) -> Node:
    """Parses a Markdown file from a given file path and returns it in a tree representation."""
    root = Node("root")
    current_node = root

    with open(file_path, "r") as file:
        for line in file:
            if line.startswith("#"):
                # current line is a header
                new_node = Node(line)
                if new_node.level == 1:
                    root.children.append(new_node)
                else:
                    parent_node = current_node
                    # traverses the tree until a higher-level header or the root node is reached
                    while parent_node.parent is not None and parent_node.level >= new_node.level:
                        parent_node = parent_node.parent
                    parent_node.append_child(new_node)
                current_node = new_node
            elif line:
                # current line is not a header
                current_node.append_content(line)
        return root


def write_changelog(changelog, output_file):
    """Recursively traverses the Markdown tree representation (depth-first) and writes it to the given file.
    The file will be either created or overwritten.
    """
    with open(output_file, "w") as file:
        _write_changelog_recursive(changelog, file)


def _write_changelog_recursive(node, file):
    if node.value != "root":
        file.write(node.value)
    for content in node.contents:
        file.write(content)
    for child in node.children:
        _write_changelog_recursive(child, file)


def setup_changelog() -> Node:
    """Builds a new changelog tree and returns it."""
    root = Node("root")
    changelog_node = Node("# Changelog\n")
    root.append_child(changelog_node)
    changelog_node.append_content(NOTICE + "\n")
    changelog_node.append_child(Node("## [Unreleased]\n"))
    return root


def add_change(changelog, change_type, change, release="Unreleased"):
    """Traverses to the target header and appends the change, missing headers are created."""
    content = f"- {change}\n"
    changelog_node = find_section_node(changelog, "changelog", 1)
    if changelog_node is None:
        changelog_node = Node(f"# [Changelog]\n")
        changelog.append_child(changelog_node)
    release_node = find_section_node(changelog_node, release, 2)
    if release_node is None:
        release_node = Node(f"## [{release}]\n")
        changelog_node.prepend_child(release_node)
    type_node = find_section_node(release_node, change_type, 3)    
    if type_node is None:
        type_node = Node(f"### [{change_type}]\n")
        release_node.prepend_child(type_node)
    type_node.append_content(content)


def find_section_node(parent_node, section_name, section_level) -> Node | None:
    """Returns a subsection node with by its name, if it exists, by traversing the children of a node.
    The section name must not include preceding '#'."""
    regex = f"{'#' * section_level} \[?{section_name}\]?.*[\r\n]?"
    for child in parent_node.children:
        if re.match(regex, child.value, re.IGNORECASE):
            return child
    return None


def traverse_commit(commit, changelog):
    """Walks through the commit body and adds the contained changes to the changelog."""
    body = commit["body"]
    interesting = False
    # iterate over lines in commit body
    for line in body.split("\n"):
        if interesting and line.startswith(("- ", "* ")):
            # follows the changelog indicator and is a bullet point (- or *)
            change_type = "Other"
            # determine type of change with regex
            for descriptor, regex in CHANGE_TYPES.items():
                if re.match(f"(-|\*) +\[?{regex}\]? ", line, re.IGNORECASE):
                    change_type = descriptor
                    break
            # isolate change message
            match = re.search("(-|\*) +(\[.*\] +)?", line)
            if match:
                message = line[match.end():]
                # optionally append additional details to changelog entry
                if SHOW_ADDITIONAL_INFO:
                    message += ADDITIONAL_INFO.format(
                        author = commit["author"]["name"],
                        timestamp = dt.fromisoformat(commit["author"]["date"]).strftime(TIMESTAMP_FORMAT)
                    )
                # add change to changelog
                add_change(changelog, change_type, message)
        else:
            # does not follow the changelog indicator or is not a bullet point
            interesting = False
        # set `interesting` to consider following lines as changes
        if re.match(CHANGELOG_INDICATOR, line, re.IGNORECASE):
            interesting = True


# --- main ---

def main():
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--commits", dest="commits", type=json.loads, required=True,
                        help="Commit(s) from git log in JSON format.")
    parser.add_argument("-t", "--target", dest="target", type=str, required=True,
                        help="Target file for storing the changelog.")
    args = parser.parse_args()

    # set the target file for storing the changelog
    changelog_file = args.target
    
    # get existing changelog from file or create one
    changelog = None
    if os.path.isfile(changelog_file):
        changelog = parse_changelog(changelog_file)
    else:
        changelog = setup_changelog()

    # iterate over commits, traverse commit body and add changes
    for commit in args.commits:
        traverse_commit(commit, changelog)
    
    write_changelog(changelog, changelog_file)


if __name__ == "__main__":
    main()
