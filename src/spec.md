# Specification

This document describes abstractly the behavior and structure of the Duplicate File Finder tool.

## Table of Contents

- [Specification](#specification)
  - [Table of Contents](#table-of-contents)
  - [Command line interface](#command-line-interface)
  - [Application programming interface](#application-programming-interface)
  - [Behavior](#behavior)

## Command line interface

The implementation must provide a command line interface with the following features.

- Zero subcommands
- A variadic argument for paths to search
- A variadic option `--exclude` for path patterns to exclude
- A boolean flag `--fail-on-duplicate` to exit with a non-zero exit code if duplicates are found
- An enum option `--compare-method` to specify the method of comparing files
  - The enum must have the following variants:
    - `size`
    - `partial-hash`
    - `hash`
  - The default value must be `hash`
- An enum option `--output-format` to specify the format of the output
  - The enum must have the following variants:
    - `json`
    - `list`
  - The default value must be `json`

An example of an invocation command is given below.

```sh
executable path1 path2 --exclude pattern1 --exclude pattern2 --fail-on-duplicate --compare-method partial-hash --output-format list
```

## Application programming interface

The implementation must implement the following functions.

- A function to recursively find all files in a directory, excluding those matching an exclude pattern
  - Which accepts the following parameters:
    - A collection of directory paths to search
    - A collection of path patterns to exclude
  - And returns the following values:
    - A collection of file paths or implementation-specific objects which represent files
- A function to calculate an MD5 hash of a file
  - Which accepts the following parameters:
    - A file path or implementation-specific object representing a file
    - An enum member representing the type of hash to calculate, must be either partial or full
  - And returns the following values:
    - An MD5 hash of the file or an implementation-specific object which represents a file and contains the hash
- A function that serves as an entrypoint to invoke the [CLI](#command-line-interface)
  - Which accepts the parameters necessary to implement the [CLI](#command-line-interface)
  - Returns no values
  - And performs the actions described in [Behavior](#behavior)

## Behavior

Upon invocation, the implementation must perform the following actions.

- Search for files in the specified paths, excluding those matching the exclude patterns
- Filter the files by comparing them and ignoring unique files
  - The comparison methods performed must be all methods up to and including the specified method, in the order of size, partial hash, and full hash
- Output the results in the specified format to `stdout` as a mapping of hashes to collections of file paths

The implementation may output additional information to `stderr`, including but not limited to the following.

- Errors
- Progress information
- Execution time
- File count for each filtering stage
