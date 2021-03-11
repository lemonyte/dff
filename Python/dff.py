import os, hashlib, json, ctypes, sys, time
from pyconsole import *

class FileInfo:
    def __init__(self, path):
        self.path = path
        self.size = os.path.getsize(self.path)

def GetFilePaths(dir: str):
    global keepGoing
    PrintMessage("Searching for files...", "Info")
    files = []

    for (dirPath, dirName, fileName) in os.walk(dir):
        for f in fileName:
            files.append(os.path.join(dirPath, f))

    if len(files) == 0:
        PrintMessage("No files found in the specified directory.", "Error")
        keepGoing = False
    
    else:
        PrintMessage("Found " + str(len(files)) + " files in \"" + dir + "\".", "Info")
        if len(files) == 1:
            keepGoing = False

    return files

def MakeDictionary(dictionary: dict, operation, prefix: str = "", enableProgressBar: bool = True):
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
            if enableProgressBar == True:
                progressBar.suffix = "..." + item.path[-25:] + " " + str(progressCounter) + "/" + str(progressBarTotal)
                progressBar.update(iteration=progressCounter)
                progressCounter += 1

    for attr in list(tempDictionary):
        if len(tempDictionary.get(attr)) <= 1:
            del tempDictionary[attr]
    
    if "accessDenied" in tempDictionary:
        del tempDictionary["accessDenied"]

    dictionary.clear()
    dictionary.update(tempDictionary)

def GenerateHash(fileInfo: FileInfo, position: str = "full", chunkSize: int = 4096):
    try:
        with open(fileInfo.path, "rb") as file:
            fileHash = hashlib.md5()
            size = fileInfo.size

            if size > (4096 * 3):
                if position == "end":
                    ending = file.seek(chunkSize, 2)
                    chunk = file.read(ending)
                    fileHash.update(chunk)

                elif position == "start":
                    chunk = file.read(chunkSize)
                    fileHash.update(chunk)

                elif position == "middle":
                    middle = file.seek(round(size / 2), 0)
                    chunk = file.read(middle - (middle - chunkSize))
                    fileHash.update(chunk)
                
            if position == "full":
                while chunk := file.read(chunkSize):
                    fileHash.update(chunk)

        return fileHash.hexdigest()

    except Exception as exception:
        PrintMessage("Could not hash file: " + str(exception), "Warning")
        return "accessDenied"

def Log(dictionary: dict, dir: str):
    outputDir = dir + "\\dff_output.txt"
    output = []

    for key, value in dictionary.items():
        outputObject = {}
        outputObject["hash"] = key
        outputObject["size"] = value[0].size
        outputObject["files"] = []

        for item in value:
            outputObject["files"].append(item.path)

        output.append(outputObject)
    
    def SortBySize(dictionary):
        return dictionary["size"]

    output.sort(key=SortBySize)

    try:
        outputFile = open(outputDir, "w")
        json.dump(output, outputFile, indent=2, separators=("", ": "))
        outputFile.close()

    except Exception as exception:
        PrintMessage("Could not create output file. Using alternate location. " + str(exception), "Warning")
        dir = projectDir
        outputDir = str(dir) + "\\dff_output.txt"
        outputFile = open(outputDir, "w")
        json.dump(output, outputFile, indent=2, separators=("", ": "))
        outputFile.close()
    
    PrintMessage("Check the output file in \"" + str(dir) + "\" for more information.", "Info")

def main():
    global exitProgram
    global keepGoing
    keepGoing = True
    dictionary = {}
    userInput = UserInput("Enter a directory to scan: ")
    startTime = time.time()
    dictionary[0] = []
    allFiles = GetFilePaths(userInput)

    if keepGoing == True:
        progressCounter = 1
        progressBarTotal = len(allFiles)
        progressBar = ProgressBar(prefix="Calculating file sizes...", decimals=3, total=progressBarTotal)
        
        for file in allFiles:
            try:
                dictionary[0].append(FileInfo(file))

            except Exception as exception:
                PrintMessage("Could not calculate file size of: " + str(exception), "Warning")

            progressBar.suffix = "..." + file[-25:] + " " + str(progressCounter) + "/" + str(progressBarTotal)
            progressBar.update(progressCounter)
            progressCounter += 1

        MakeDictionary(dictionary, lambda fileInfo: fileInfo.size, enableProgressBar=False)
        PrintMessage("Found " + str(sum(len(val) for val in dictionary.values())) + " files with matching sizes in \"" + userInput + "\".", "Info")
        
        MakeDictionary(dictionary, lambda fileInfo: GenerateHash(fileInfo, "middle"), "Hashing files (Phase 1)...")
        PrintMessage("Found " + str(sum(len(val) for val in dictionary.values())) + " files with hashes that match other files in \"" + userInput + "\" (Phase 1).", "Info")
        
        MakeDictionary(dictionary, lambda fileInfo: GenerateHash(fileInfo, "full"), "Hashing files (Phase 2)...")
        endTime = time.time()
        totalTime = endTime - startTime
        foundFiles = sum(len(val) for val in dictionary.values())
        print()
        PrintMessage("Found " + str(foundFiles) + " duplicate files in \"" + userInput + "\" in " + str(round(totalTime, 6)) + " seconds.", "Info")

        if sum(len(val) for val in dictionary.values()) != 0:
            PrintMessage(str(len(dictionary.get('d41d8cd98f00b204e9800998ecf8427e'))) + " out of " + str(foundFiles) + " files are empty files.", "Info")
            Log(dictionary, userInput)

        UserInput("\nPress enter to exit the program... ")
        exitProgram = True

if ctypes.windll.shell32.IsUserAnAdmin() == True: # or sys.argv[1] == "noadmin":
    exitProgram = False
    keepGoing = True
    terminalSize = "mode 185, 50"
    os.system(terminalSize)
    Logger.Set(False, False)
    PrintMessage("Duplicate File Finder by LemonPi314. https://github.com/LemonPi314/duplicate-file-finder \n")

    while exitProgram == False:
        main()

else:
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)