# Duplicate File Finder
By [LemonPi314](https://github.com/LemonPi314)

A simple command line tool to find duplicate files on your PC.
## Overview
- [Requirements](#requirements)
    - [Python File](#python-file)
    - [Executable File](#executable-file)
- [Usage](#usage)
    - [Command Line](#command-line)
- [Versions](#versions)
- [How It Works](#how-it-works)
    - [Size](#size)
    - [Minihash](#minihash)
    - [Full Hash](#full-hash)
- [Disclaimer](#disclaimer)
- [License](#license)
## Requirements
### Python File
- [Python 3.9](https://www.python.org/downloads/) or higher
- [`pyco`](https://test.pypi.org/project/pyco)
### Executable File
Optional executable file. Python and any required packages are included in the executable.
- 7 MB of free space for the executable
- 6 MB of free space for temporary files
## Usage
> Note: these instructions refer to the Python version of the tool.

This tool only works on Windows. Download the executable from the [latest release](https://github.com/LemonPi314/dff/releases/latest). Double click `dff.exe` and enter a directory path to search for duplicate files.

You can also download the source code and use the Python file if you prefer.
### Command Line
For advanced options, you may run the tool from a command line terminal such as Command Prompt or PowerShell. Navigate to the same directory as the tool and run the following command with any necessary options.

Command syntax:
```bash
dff [-d <path>] [-o <path>] [-l <level>] [-a] [-xd <pattern>...] [-xf <pattern>...]
```
Some terminals such as PowerShell do not automatically load files from the current directory, in which case you must replace `dff` with `./dff`. This tool works best in Command Prompt. If you are using the Python file, replace `dff` with `python dff.py`.

Options:
|Option|Description|
|--|--|
|`-h`, `--help`|Show this help message and exit.|
|`-d <path>`, `--dir <path>`|Directory path to search.|
|`-o <path>`, `--output-dir <path>`|Directory path to place the output file and log files. Default is the current working directory.|
|`-l <level>`, `--log <level>`|Log level integer from 0 to 5. Default is 1.|
|`-a`, `--admin`|Run with administrator privileges.|
|`-xd <pattern>...`, `--exclude-dir <pattern>...`|Exclude directories matching this pattern, can be repeated multiple times. (e.g. `.*`)|
|`-xf <pattern>...`, `--exclude-file <pattern>...`|Exclude files matching this pattern, can be repeated multiple times. (e.g. `*.txt`)|

Example:
```bash
dff -a -d ~ -o ~/Desktop -xd .* -xd AppData
```
Exclude pattern examples:
- Directories:
    - `.*`
    - `AppData`
    - `Unity`
    - `build`
    - `*env*`
- Files:
    - `license.txt`
    - `readme.md`
    - `*.log`

In all path options (`-d` and `-o`) the `~` character resolves to the current user's home directory.  
See the [`pyco` docs](https://duplexes.me/pyco/#/logging?id=log-levels) for a list of log levels.  
See the [Python `fnmatch` docs](https://docs.python.org/3/library/fnmatch.html) for more information on patterns.

It is recommended to search only user-specific files such as your `Documents` folder, as searching the entire disk including the Windows operating system will take exceedingly long and produce a very large output file filled with system file names. After the tool is finished it will create an output file named `dff_output.json` in the directory you specified. The output file is formatted as a list of JSON objects (or Python dictionaries) sorted by file size, with each object containing a list of files matching a hash and size. This tool does not automatically delete any files. It is up to the user to delete or modify files.
## Versions
This tool has 3 versions written in Python, Java (in progress), and C# (in progress). All 3 versions do the same thing, but were made using different programming languages.
## How It Works
The tool has 3 stages of filtering:  
1. Filter files by size
2. Filter files by minihash
3. Filter files by full hash
### Size
A file size in bytes is calculated for every file. Files with matching sizes continue onto the next stage.
### Minihash
A "minihash" is calculated for every file. A "minihash" is an MD5 hash of the middle 4 kilobytes of the file. Calculating a minihash before a full hash saves time by eliminating different files with matching sizes. Files with matching minihashes continue onto the next stage. Files less than 12 kilobytes in size are skipped and continue onto the next stage.
### Full Hash
A full MD5 hash is calculated for every file. Files that have matching hashes are duplicates. The tool also lists empty files. It may be worth noting that there is an extremely small chance of two MD5 hashes matching for files that are different. MD5 collisions do not affect this tool significantly, the only consequence is that the output will list two non-duplicate files as duplicates, which the user will be able to notice and take into account.
## Disclaimer
I am not liable for any data loss, damage, or any other consequences resulting from corruption or general use of this software. Security is not guaranteed. Use at your own risk.
## License
[MIT License](https://choosealicense.com/licenses/mit/)
