# duplicate-file-finder
By [LemonPi314](https://github.com/LemonPi314)

A simple console program that finds duplicate files on your PC.
## Requirements
* Windows operating system
* 20 MB of free space for the executable file
* 50 MB of free space for temporary files
## Usage
Download the project files and extract the `dff.exe` file from `duplicate-file-finder/Python/dist`. Run the `dff.exe` file and enter a directory you would like to scan for duplicate files. It is recommended to scan only user-specific files such as your `Documents` folder, as scanning your entire disk including the Windows operating system will take a long time and produce a very large output file filled with system file names. After the program is finished it will create an output file named `dff_output.txt` in the directory you specified. The output file is formatted as a list of dictionaries, with each dictionary containing a list of files matching a hash and size.  
Note: This program does not automatically delete any files. It is up to the user to delete or modify files.
## Variants
This program has 3 variants:
* Python
* Java (in progress)
* C# (in progress)

All 3 variants do the same thing, but were made using different programming languages.
## How It Works
The program has 3 stages of filtering:  
1. Sort files by size
2. Sort files by minihash
3. Sort files by full hash
### Size
Self explanatory. Files with matching sizes (in bytes) move onto the next stage.
### Minihash
A "minihash" is calculated for files with matching sizes. A "minihash" is an `MD5` checksum hash of the middle 4 kilobytes of the file. Calculating a minihash before a full hash saves time by eliminating different files with matching sizes.
### Full Hash
A full `MD5` checksum hash is calculated for files with matching minihashes. Files that have matching hashes are duplicates (however there is a very small chance that the hash matches for different files).
## Disclaimer
I am not liable for any data loss, damage, or other consequences due to corruption, improper encryption/decryption, or general use of this software. Security is not guaranteed. Use at your own risk.
## License
[MIT License](https://choosealicense.com/licenses/mit/)