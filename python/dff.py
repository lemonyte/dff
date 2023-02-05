"""Duplicate File Finder by Lemonyte
https://github.com/lemonyte/dff

Usage:
  dff [-d <path>] [-o <path>] [-l <level>] [-a] [-xd <pattern>...] [-xf <pattern>...]

Options:
  -h, --help                                    show this help message and exit
  -d <path>, --dir <path>                       directory path to search for duplicate files
  -o <path>, --output-dir <path>                directory path to place output files [default: .]
  -l <level>, --log <level>                     logging level from 0 to 5 [default: 1]
  -a, --admin                                   run with administrator privileges
  -xd <pattern>..., --exclude-dir <pattern>...  exclude directories matching this pattern,
                                                can be repeated multiple times (e.g. .*)
  -xf <pattern>..., --exclude-file <pattern>... exclude files matching this pattern,
                                                can be repeated multiple times (e.g. *.txt)

See https://duplexes.me/pyco/#/logging?id=log-levels for a list of log levels
See https://docs.python.org/3/library/fnmatch.html for more information on patterns

"""

import os
import json
from sys import argv, executable
from hashlib import md5
from time import perf_counter
from fnmatch import fnmatch
from ctypes import windll
from pyco import print_message, user_input, logging, progress, prefix, terminal, utils

EMPTY_HASH = 'd41d8cd98f00b204e9800998ecf8427e'


class FileInfo:
    def __init__(self, path: str):
        self.path = path
        self.size = os.path.getsize(self.path)


def get_file_paths(dir: str, exclude_dirs: list[str] = [], exclude_files: list[str] = []) -> list[str]:
    global valid_input
    print_message()
    print_message("Searching for files...")
    files = []
    dir = os.path.normpath(os.path.expanduser(dir))
    exclude_dirs = [os.path.normpath(os.path.sep + dir if ':' not in dir else dir) for dir in exclude_dirs]
    exclude_files = [os.path.normpath(file) for file in exclude_files]
    for dirpath, dirnames, filenames in os.walk(dir):
        fulldirs = [os.path.join(dirpath, dir) for dir in dirnames]
        fullfiles = [os.path.join(dirpath, file) for file in filenames]
        files.extend(fullfiles)
        for dirname, fulldir in zip(dirnames.copy(), fulldirs.copy()):
            for pattern in exclude_dirs:
                if fnmatch(fulldir, '*' + pattern):
                    dirnames.remove(dirname)
                    fulldirs.remove(fulldir)
                    break
        for filename, fullfile in zip(filenames.copy(), fullfiles.copy()):
            for pattern in exclude_files:
                if fnmatch(filename, pattern):
                    files.remove(fullfile)
                    break
    if len(files) == 0:
        print_message("No files found in the specified directory.", prefix.ERROR)
        valid_input = False
    else:
        print_message(f"Found {len(files)} files in '{dir}'.")
        if len(files) == 1:
            valid_input = False
    return files


def create_dictionary(dictionary: dict, operation, prefix: str = '', enable_progress_bar: bool = True):
    temp_dictionary = {}
    progress_bar_total = sum(len(value) for value in dictionary.values())
    if progress_bar_total == 0:
        return
    if enable_progress_bar is True:
        progress_bar = progress.ProgressBar(iteration=1, total=progress_bar_total, prefix=prefix, decimals=3)
    for items in dictionary.values():
        for item in items:
            temp_dictionary.setdefault(operation(item), []).append(item)
            if enable_progress_bar is True:
                progress_bar.increment(suffix=f'{item.path[:12]}...{item.path[-13:]} {progress_bar.iteration}/{progress_bar_total}')
    for key in temp_dictionary.copy().keys():
        if len(temp_dictionary.get(key)) <= 1:
            del temp_dictionary[key]
    if 'unabletohash' in temp_dictionary:
        del temp_dictionary['unabletohash']
    dictionary.clear()
    dictionary.update(temp_dictionary)


def generate_hash(file_info: FileInfo, position: str = 'full', chunk_size: int = 4096) -> str:
    try:
        with open(file_info.path, 'rb') as file:
            file_hash = md5()
            size = file_info.size
            if size < (4096 * 3) and position != 'full':
                return 'unhashed'
            if size > (4096 * 3):
                if position == 'end':
                    ending = file.seek(chunk_size, 2)
                    chunk = file.read(ending)
                    file_hash.update(chunk)
                elif position == 'start':
                    chunk = file.read(chunk_size)
                    file_hash.update(chunk)
                elif position == 'middle':
                    middle = file.seek(round(size / 2), 0)
                    chunk = file.read(middle - (middle - chunk_size))
                    file_hash.update(chunk)
            if position == 'full':
                while chunk := file.read(chunk_size):
                    file_hash.update(chunk)
            return file_hash.hexdigest()
    except Exception as exception:
        terminal.clear_line()
        print_message(f"Could not hash file: {exception}", prefix.WARNING)
        return 'unabletohash'


def dump(dictionary: dict, dir: str):
    output_dir = f'{dir}/dff_output.json'
    output = []
    for key, value in dictionary.items():
        output_object = {}
        output_object['hash'] = key
        output_object['size'] = value[0].size
        output_object['files'] = [item.path for item in value]
        output.append(output_object)
    output.sort(key=lambda dictionary: dictionary['size'])
    try:
        file = open(output_dir, 'w')
        json.dump(output, file, indent=2)
    except Exception as exception:
        print_message(f"Could not create output file. Using alternate location. {exception}", prefix.WARNING)
        dir = os.getcwd()
        output_dir = f'{dir}/dff_output.txt'
        file = open(output_dir, 'w')
        json.dump(output, file, indent=2)
    finally:
        file.close()
    print_message(f"Check the output file in '{dir}' for more information.")


def main(dir: str = None, output_dir: str = None, exclude_dirs: list[str] = [], exclude_files: list[str] = []):
    global exit_program
    global valid_input
    valid_input = True
    dictionary = {0: []}
    os.system('mode con cols=150 lines=50')
    print_message("Duplicate File Finder by Lemonyte", log=False)
    print_message("https://github.com/lemonyte/dff", log=False)
    print_message()
    dir = os.path.expanduser(os.path.normpath(user_input("Enter a directory to search: ") if dir is None else dir))
    output_dir = os.path.expanduser(os.path.normpath(dir if output_dir is None else output_dir))
    logging.log_path = os.path.join(output_dir, 'dff_log.txt')
    logging.clear_log()
    start_time = perf_counter()
    all_files = get_file_paths(dir, exclude_dirs, exclude_files)
    if valid_input is True:
        progress_bar_total = len(all_files)
        progress_bar = progress.ProgressBar(iteration=1, total=progress_bar_total, prefix="Calculating file sizes", decimals=3)
        for file in all_files:
            try:
                dictionary[0].append(FileInfo(file))
            except Exception as exception:
                terminal.clear_line()
                print_message(f"Could not calculate file size: {exception}", prefix.WARNING)
            progress_bar.increment(suffix=f'{file[:12]}...{file[-13:]} {progress_bar.iteration}/{progress_bar_total}')
        create_dictionary(dictionary, lambda file_info: file_info.size, enable_progress_bar=False)
        print_message(f"Found {sum(len(value) for value in dictionary.values())} files with matching sizes in '{dir}'.")
        create_dictionary(dictionary, lambda file_info: generate_hash(file_info, 'middle'), "Hashing files (Phase 1)")
        files_skipped = len(dictionary.get('unhashed', []))
        files_matching_minihashes = (sum(len(value) for value in dictionary.values())) - files_skipped
        if files_matching_minihashes > 0:
            print_message(f"Found {files_matching_minihashes} files with minihashes that match other files in '{dir}' (Phase 1)")
        if files_skipped > 0:
            print_message(f"Skipped minihashing {files_skipped} files because they are smaller than 12 KB.")
        create_dictionary(dictionary, lambda file_info: generate_hash(file_info, 'full'), "Hashing files (Phase 2)")
        total_time = perf_counter() - start_time
        files_found = sum(len(value) for value in dictionary.values())
        print_message()
        print_message(f"Found {files_found} duplicate files in '{dir}' in {round(total_time, 6)} seconds.")
        if sum(len(value) for value in dictionary.values()) != 0:
            if EMPTY_HASH in dictionary:
                print_message(f"{len(dictionary.get(EMPTY_HASH))} out of {files_found} files are empty files.")
            dump(dictionary, output_dir)
        print_message()
        print_message("Press any key to exit the program... ")
        utils.getch()
        exit_program = True


if '-h' in argv or '--help' in argv:
    print(__doc__)
elif ('-a' in argv or '--admin' in argv) and not windll.shell32.IsUserAnAdmin():
    windll.shell32.ShellExecuteW(None, "runas", executable, ' '.join(argv), None, 1)
else:
    try:
        dir = None
        output_dir = None
        exclude_dirs = []
        exclude_files = []
        if '-l' in argv and argv[-1] != '-l':
            logging.enable_message_logging = logging.enable_input_logging = True
            try:
                logging.log_level = int(argv[argv.index('-l') + 1])
            except ValueError:
                print_message("Log level value must be of type 'int'.", prefix.ERROR)
        elif '--log' in argv and argv[-1] != '--log':
            logging.enable_message_logging = logging.enable_input_logging = True
            try:
                logging.log_level = int(argv[argv.index('--log') + 1])
            except ValueError:
                print_message("Log level value must be of type 'int'.", prefix.ERROR)
        if '-d' in argv and argv[-1] != '-d':
            dir = argv[argv.index('-d') + 1]
        elif '--dir' in argv and argv[-1] != '--dir':
            dir = argv[argv.index('--dir') + 1]
        if '-o' in argv and argv[-1] != '-o':
            output_dir = argv[argv.index('-o') + 1]
        elif '--output-dir' in argv and argv[-1] != '--output-dir':
            output_dir = argv[argv.index('--output-dir') + 1]
        if '-xd' in argv:
            indices = [index for index, element in enumerate(argv) if element == '-xd']
            exclude_dirs.extend([argv[index + 1] for index in indices if index != len(argv) - 1])
        if '--exclude-dir' in argv:
            indices = [index for index, element in enumerate(argv) if element == '--exclude-dir']
            exclude_dirs.extend([argv[index + 1] for index in indices if index != len(argv) - 1])
        if '-xf' in argv:
            indices = [index for index, element in enumerate(argv) if element == '-xf']
            exclude_files.extend([argv[index + 1] for index in indices if index != len(argv) - 1])
        if '--exclude-file' in argv:
            indices = [index for index, element in enumerate(argv) if element == '--exclude-file']
            exclude_files.extend([argv[index + 1] for index in indices if index != len(argv) - 1])
        exit_program = False
        while exit_program is False:
            main(dir, output_dir, exclude_dirs, exclude_files)
    except KeyboardInterrupt:
        print_message("\nKeyboard interrupt detected. Shutting down.")
        print_message("\nPress any key to exit the program...")
        utils.getch()
    except Exception as exception:
        print_message(exception, prefix.ERROR)
        print_message("\nPress any key to exit the program...")
        utils.getch()
