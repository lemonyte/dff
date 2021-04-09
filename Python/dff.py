import os, hashlib, json, ctypes, sys, time
from pyconsole import *

class FileInfo:
    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(self.path)

def GetFilePaths(dir: str):
    global vaildInput
    print()
    PrintMessage("Searching for files...", "Info")
    files = []

    for (dirPath, dirName, fileName) in os.walk(dir):
        for f in fileName:
            files.append(os.path.join(dirPath, f))

    if len(files) == 0:
        PrintMessage("No files found in the specified directory.", "Error")
        vaildInput = False
    
    else:
        PrintMessage(f"Found {len(files)} files in '{dir}'.", "Info")
        if len(files) == 1:
            vaildInput = False

    return files

def MakeDictionary(dictionary: dict, operation, prefix: str = '', enableProgressBar: bool = True):
    tempDictionary = {}
    progressBarTotal = sum(len(val) for val in dictionary.values())

    if progressBarTotal == 0:
        return

    if enableProgressBar == True:
        progressCounter = 1
        progressBar = ProgressBar(total=progressBarTotal, prefix=prefix, decimals=3)

    for items in dictionary.values():
        for item in items:
            tempDictionary.setdefault(operation(item), []).append(item)
            if enableProgressBar is True:
                progressBar.suffix = f'...{item.path[-25:]} {progressCounter}/{progressBarTotal}'
                progressBar.Update(iteration=progressCounter)
                progressCounter += 1

    for attr in list(tempDictionary):
        if len(tempDictionary.get(attr)) <= 1:
            del tempDictionary[attr]
    
    if 'unabletohash' in tempDictionary:
        del tempDictionary['unabletohash']

    dictionary.clear()
    dictionary.update(tempDictionary)

def GenerateHash(fileInfo: FileInfo, position: str = 'full', chunkSize: int = 4096):
    try:
        with open(fileInfo.path, 'rb') as file:
            fileHash = hashlib.md5()
            size = fileInfo.size
            if size < (4096 * 3) and position != 'full':
                return 'unhashed'

            if size > (4096 * 3):
                if position == 'end':
                    ending = file.seek(chunkSize, 2)
                    chunk = file.read(ending)
                    fileHash.update(chunk)

                elif position == 'start':
                    chunk = file.read(chunkSize)
                    fileHash.update(chunk)

                elif position == 'middle':
                    middle = file.seek(round(size / 2), 0)
                    chunk = file.read(middle - (middle - chunkSize))
                    fileHash.update(chunk)
                
            if position == 'full':
                while chunk := file.read(chunkSize):
                    fileHash.update(chunk)
            
            return fileHash.hexdigest()

    except Exception as exception:
        PrintMessage(f"Could not hash file: {exception}", "Warning")
        return 'unabletohash'

def Log(dictionary: dict, dir: str):
    outputDir = f'{dir}/dff_output.txt'
    output = []
    for key, value in dictionary.items():
        outputObject = {}
        outputObject['hash'] = key
        outputObject['size'] = value[0].size
        outputObject['files'] = []
        for item in value:
            outputObject['files'].append(item.path)

        output.append(outputObject)
    
    def SortBySize(dictionary):
        return dictionary['size']

    output.sort(key=SortBySize)
    try:
        outputFile = open(outputDir, 'w')
        json.dump(output, outputFile, indent=2, separators=('', ': '))

    except Exception as exception:
        PrintMessage(f"Could not create output file. Using alternate location. {exception}", "Warning")
        dir = projectDir
        outputDir = f'{dir}/dff_output.txt'
        outputFile = open(outputDir, 'w')
        json.dump(output, outputFile, indent=2, separators=('', ': '))

    finally:
        outputFile.close()

    PrintMessage(f"Check the output file in '{dir}' for more information.", "Info")

def main():
    global exitProgram
    global vaildInput
    vaildInput = True
    dictionary = {0: []}
    userInput = UserInput("Enter a directory to scan: ")
    startTime = time.time()
    allFiles = GetFilePaths(userInput)
    if vaildInput is True:
        progressCounter = 1
        progressBarTotal = len(allFiles)
        progressBar = ProgressBar(prefix="Calculating file sizes...", decimals=3, total=progressBarTotal)
        for file in allFiles:
            try:
                dictionary[0].append(FileInfo(file))

            except Exception as exception:
                PrintMessage(f"Could not calculate file size: {exception}", "Warning")

            progressBar.suffix = f'...{file[-25:]} {progressCounter}/{progressBarTotal}'
            progressBar.Update(progressCounter)
            progressCounter += 1

        MakeDictionary(dictionary, lambda fileInfo: fileInfo.size, enableProgressBar=False)
        PrintMessage(f"Found {sum(len(val) for val in dictionary.values())} files with matching sizes in '{userInput}'.", "Info")
        MakeDictionary(dictionary, lambda fileInfo: GenerateHash(fileInfo, 'middle'), "Hashing files (Phase 1)...")
        skippedFiles = len(dictionary.get('unhashed', 0))
        PrintMessage(f"Found {(sum(len(val) for val in dictionary.values())) - skippedFiles} files with minihashes that match other files in '{userInput}' (Phase 1)", "Info")
        if 'unhashed' in dictionary:
            PrintMessage(f"{skippedFiles} files were skipped because they are smaller than 12 KB.", "Info")

        MakeDictionary(dictionary, lambda fileInfo: GenerateHash(fileInfo, 'full'), "Hashing files (Phase 2)...")
        endTime = time.time()
        totalTime = endTime - startTime
        foundFiles = sum(len(val) for val in dictionary.values())
        print()
        PrintMessage(f"Found {foundFiles} duplicate files in '{userInput}' in {round(totalTime, 6)} seconds.", "Info")
        if sum(len(val) for val in dictionary.values()) != 0:
            if 'd41d8cd98f00b204e9800998ecf8427e' in dictionary:
                PrintMessage(f"{len(dictionary.get('d41d8cd98f00b204e9800998ecf8427e'))} out of {foundFiles} files are empty files.", "Info")
            
            Log(dictionary, userInput)

        UserInput("\nPress enter to exit the program... ")
        exitProgram = True

if '-a' in sys.argv or '--admin' in sys.argv:
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, sys.argv[0], None, 1)

else:
    exitProgram = False
    os.system('mode 185, 50')
    Logger.Set(False, False)
    PrintMessage("Duplicate File Finder by LemonPi314. https://github.com/LemonPi314/duplicate-file-finder \n")
    try:
        while exitProgram is False:
            main()

    except Exception as exception:
        PrintMessage(f"Fatal error: {exception}", "Error")
        input("\nPress enter to exit the program...")