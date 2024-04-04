# Git Changelog Hook

A Git **post-commit** hook that automatically generates a changelog from changes specified in commit messages.

The changelog format adheres to the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) convention:

```md
# Changelog
All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
## [Unreleased]
### [Added]
- Added something
- Created another thing
### [Fixed]
- Fixes a bug
```


## Usage

Copy the Python script [git_changelog_hook.py](./git_changelog_hook.py) and the hook [post-commit](./post-commit) to the `.git\hooks\`-directory of your local Git project.

That's it, now changes specified in commit messages, as described [below](#commit-message-style), are recognized and added to the changelog file.
Thereby, the changelog file is amended to the respective commit.

For an example to try out creating a changelog without using the hook or creating commits, see the [tryout.nb](./tryout.ipynb) notebook.


### Good To Know

Note that this hook is only triggered locally. To use it in a shared project, everyone must add these files to their own copy.

Commits that contain the changelog file are ignored.
This prevents recursive calls, as the post-commit hook is executed again after the changelog has been amended to the commit.


### Commit Message Style

Changes to be included in the log are recognized by the indicator `Changelog:` followed by individual bullet points for the changes.
The indicator with the changes can be placed anywhere in the body of a commit message, but it must not be interrupted, e.g., by a blank line.
To allow custom change messages, either the first word after the bullet is mapped to a [change type](#supported-change-types) and retained, or the type indicator in the brackets is mapped and omitted.

```txt
This is a commit

Changelog:
- Added something
- Fixes the bug
- [Add] Created another thing
```

*Check out the changelog example at the top to see the result of this commit message.*

### Supported Change Types

The hook recognizes the following predefined types of changes in the listed variants and is case-insensitive:
- Add / Added / Addes
- Change / Changed / Changes
- Deprecate / Deprecated / Deprecates
- Remove / Removed / Removes
- Fix / Fixed / Fixes
- Security

*Changes that cannot be mapped are summarized as **Other**.*


### Create a changelog from multiple commits

Processing multiple commits is not supported by the post-commit hook.
If desired, manually fetch the log for the commits and call the Python script using the following bash commands.

```bash
FORMAT='{"commit_hash": "%H", "refs": "%D", "subject": "%s", "sanitized_subject_line": "%f", "body": "%b", "author": {"name": "%aN", "email": "%aE", "date": "%aI"}, "commiter": {"name": "%cN", "email": "%cE", "date": "%cI"} }'

COMMITS="[$(git --no-pager log -1 HEAD --no-merges --format="$FORMAT" | sed -r ':a;N;$!ba;s/\r{0,1}\n/\\n/g' | sed 's/}\\n{/},{/g')]"

python ./.git/hooks/git_changelog_hook.py --commit "$COMMITS"
```


## Approach

1. Post-commit hook is executed on after commit
    1. Check whether the commit contains the change log file, if so, exit to prevent recursion
    2. Fetch log for the last commit (`git log -1 HEAD`)
    3. ... format it as JSON ...
    4. ... escape new-line symbols ...
    5. ... and slurp the log object into an array (would be nicer with **jq** but it isn't pre-installed in Git Bash)
    6. Execute the Python script with the JSON object as argument
2. The Python script is executed
    1. Get the existing changelog from the file or create one
    2. Parse the changelog file to a tree-like structure
    3. Traverse the body of the passed commit
        1. Locate the changelog indicator and walk through the listed changes
        2. Identify the type of change
        3. Append the change to the changelog
    4. Write the changelog tree to the file
3. Amend the changelog to the commit
