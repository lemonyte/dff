# Duplicate File Finder

A dead-simple command line tool to find duplicate files on your computer.

> Note: the repository is currently undergoing some restructuring.
> The main branch no longer contains the code.
> Please see the branches listed under [Implementations](#implementations) to view the code.

## Implementations

This tool is implemented in multiple languages.
If you're looking for the code, please see the branches below for implementations.

| Language | Branch | Status |
| -------- | ------ | ------ |
| Python | [python](https://github.com/lemonyte/dff/tree/python) | Implemented |
| Rust | [rust](https://github.com/lemonyte/dff/tree/rust) | Implemented |
| C# | [csharp](https://github.com/lemonyte/dff/tree/csharp) | In development |
| Others | - | Planned |

## Specification

The main branch contains an [abstract specification](src/spec.md) of the behavior and structure of the tool.
The specification is language-agnostic and can be used as a reference for implementing the tool in other languages.

## How it works

The tool works by filtering files in three stages:

1. By size
2. By partial hash
3. By full hash

### Size

A file size in bytes is queried for every file.
Files with matching sizes continue onto the next stage.

### Partial hash

A partial hash is calculated for every file.
A partial hash is an MD5 hash of the first, last, and middle 64 kilobytes of a file.
Calculating a partial hash before a full hash saves processing time by eliminating files with matching sizes but sufficiently different content.
Files with matching partial hashes continue onto the next stage.
If the file is smaller than 192 kilobytes (the minimum size needed for a partial hash) a full hash is calculated instead since it is equivalent.

### Full hash

A full MD5 hash is calculated for every file.
Files that have matching hashes are duplicates.

## Disclaimer

I am not liable for any data loss, damage, or any other consequences resulting from corruption or general use of this software.
Security is not guaranteed.
Use at your own risk.

## License

[MIT License](license.txt)
