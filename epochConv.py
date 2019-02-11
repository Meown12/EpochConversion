import argparse
import gzip
import datetime
import os
import pytz
import traceback
import string

EPOCH_TIME = 5 # assumed EPOCH time in previous
WRITE_BUFFER = 100 # the number of conversions done before the results are logged into the outputfile
ALLOWED_PLAIN_EXTENSIONS = [".csv", ".txt"] # non compressed file types this script assumes to be able to operate with.
PREFIX_SET = False
TIMEZONE = "Europe/London"
# TODO add output file extension parameter to allow for other file extensions than .tsv


def getTimeStampDT(headerLine, offsetLine,epochTime=EPOCH_TIME, dayLightSavingsTime=False):
    timeStamp = ""
    headerInfo = str(headerLine).split(" ")
    startDate = headerInfo[3]
    startTime = headerInfo[4]
    endDate = headerInfo[6]
    end_time = headerInfo[7]
    sample_rate = int(headerInfo[11])
    if sample_rate != EPOCH_TIME:
        raise AttributeError
    # calculate offset:
    offsetSec = offsetLine * EPOCH_TIME
    offset = datetime.timedelta(seconds=offsetSec)
    startInfo = startDate + " " + startTime
    gmt = pytz.timezone(TIMEZONE)
    startDateTime = datetime.datetime.strptime(startInfo, '%Y-%m-%d %H:%M:%S').astimezone(gmt)
    currentTime = startDateTime + offset
    if dayLightSavingsTime:
        nullTime = datetime.timedelta(0)
        oneHour = datetime.timedelta(hours=1)
        if ((startDateTime.astimezone(gmt).dst() == nullTime) & (currentTime.astimezone(gmt).dst() == oneHour)):
            # dst started during the measurement, add one hour to the offset
            currentTime = currentTime + datetime.timedelta(hours=1)
        elif ((startDateTime.astimezone(gmt).dst() == oneHour) & (currentTime.astimezone(gmt).dst() == nullTime)):
            # dst ended during the measurement, take one hour off the offset
            currentTime = currentTime - datetime.timedelta(hours=1)
    return currentTime

def getTimeStamp(headerLine, offsetLine, dayLightSavingsTime=False):
    """
    getTimeStamp
    Function expects the header line to be in the following format:
    [w] [w] [w] [start_date] [start_time] [w] [end_date] [end_time] [w] [w] [w] [sample_rate] [w]
    with [w] being any continuous string, which will be ignored
    [start_date] and [end_date] are expected to be YYYY-MM-DD
    whilst times are expected as HH:MM:SS
    :param headerLine The line conataining the date information, usually the first line of the file.
    :param offsetLine How many lines of Values have been read after the initial occurence of the header line.
    :param dayLightSavingsTime Whether or not daylight savings time changes should be applied to the timestamps.
    :return Timestamp in the format YYYY-MM-DDThh:mm:ss
    """

    timeStamp = getTimeStampDT(headerLine,offsetLine,dayLightSavingsTime).strftime("%Y-%m-%dT%H:%M:%S")

    return timeStamp


def header(headerLine, epoch):
    """
    header(headerLine, epoch) creates a new header for the output from the existing header  in the following format:
    "[w1] [w2] [w3] [start_date] [start_time] [-] [end_date] [end_time] [-] [w] [w] [sample_rate] [w]"
    with [w] being any continuous string, which will be ignored
    [start_date] and [end_date] are expected to be YYYY-MM-DD
    whilst times are expected as HH:MM:SS
    It will then return a header of the format:
    "Measurement from: [start_date]  [start_time] to [end_date] [end_time]\t[w1] [w2] - sampleRate = [epoch]\tfraction of imputed data
    :param headerLine: the existing header line from the input file
    :param epoch: the epoch this file is getting converted to
    :return: a new header line with the appropriate format
    """
    oldheaderString = str(headerLine).split(" - ")
    startInfo = datetime.datetime.strptime(oldheaderString[1], '%Y-%m-%d %H:%M:%S')
    endInfo = datetime.datetime.strptime(oldheaderString[2], '%Y-%m-%d %H:%M:%S')
    newHeader = "Measurement from " + startInfo.strftime("%Y-%m-%d %H:%M:%S")
    newHeader = newHeader + " to " + endInfo.strftime("%Y-%m-%d %H:%M:%S")
    newHeader = newHeader + "\t" + oldheaderString[0] + " - sampleRate = " + str(epoch)
    newHeader = newHeader + "\t" + "fraction of imputed data"

    return newHeader


def getOutFileName(filename, outdir, epoch, prefix="", keepName=False):
    """
    Depending on the given arguments this function will create the absolute output path for a file.
    If no prefix is specified the file name will follow the scheme [old_name]_avg_[epoch].tsv
    If a prefix is specified the file name will be that prefix, unless keepName is True in which case the file name
    follows: [prefix]_[old_name].tsv
    :param filename: input file name (file that is currently being processed
    :param outdir: output directory for the file
    :param epoch: the epoch it will convert to. this will be used if no other prefix is specified.
    :param prefix: the new prefix
    :param keepName: whether the new file name should contain the old file name
    :return: string of the absolute path
    """
    outdir = os.path.realpath(outdir)
    oldname = os.path.splitext(os.path.basename(filename))[0]
    if filename.endswith(".csv.gz"):
        # we may expect double endings in the exisitng file name e.g. .csv.gz in case we detect this we need to call
        # splitext twice to ridden us of the second extension
        oldname = os.path.splitext(oldname)[0]
    if prefix != "":
        if keepName:
            outfile = os.path.join(outdir,prefix + "_" + oldname +".tsv")
        else:
            outfile = os.path.join(outdir, prefix + ".tsv")
    else:
        outname = oldname + "_avg_{}.tsv".format(epoch)
        outfile = os.path.join(outdir, outname)
    return outfile


# TODO acknowledge that for some epochs the last average may not be a true representation, should be done in the
# documentation, as the code handles "missing" data correctly
def workFile(filename, epoch, outdir, prefix="", keepName=False, daylightSavingsTime=False, noConsoleOutput=False, noOverwrite=False):
    """
    workFile is the central function to convert a file with one epoch to another epoch, not overwriting the original data
    it offers a few options in regards to how the new file should behave. It can be specified, whether a daylight
    savings time adjusted timestamp should be created, whether no console output should be given in regards to the
    workings of the file, a new file prefix
    either with or without the old file name attached can be specified and most importantly output directory and new
    epoch can be specified
    :param filename: the absolute path to the file that should be converted
    :param epoch: the new epoch in seconds to convert to (needs to be a multiple of 5 or 5)
    :param outdir: relative or absolute path to the output directory
    :param prefix: a new prefix, which will replace the old filename, when keepName is False, otherwise it will be put
    in front of the old file name
    :param keepName: see prefix argument
    :param daylightSavingsTime: specifies, whether or not there should be an auto adjust for the daylight savings time,
     if a change from dst to standard time (or inverse) occurs in the raw file
    :param noConsoleOutput: whether or not the function should output errors or  status messages to the console
    :return: none
    """
    # how many lines need to be read to convert one 5 second epoch to the new epoch time EPOCH
    linesNeeded = epoch/EPOCH_TIME
    lineAccumulator = []
    resultLineAcc = []
    lineCount = 0
    headerlinefound = False
    headerLine = ""
    outdir = os.path.realpath(outdir)
    extension= os.path.splitext(filename)[1]
    outputFile = getOutFileName(filename, outdir, epoch, prefix, keepName)
    # if this file exists already, delete it.
    try:
        if noOverwrite & (os.path.isfile(outputFile)):
            print("STATUS: File " + outputFile + " does exist already, it will be skipped.")
            return
        os.remove(outputFile)
    except OSError:
        pass
    # find out whether to gzip open or to plain open it
    compressed = False
    if (extension == ".gz") & (os.path.basename(filename).endswith(".csv.gz")):
        file = gzip.open(filename, "r")
        compressed = True
    elif (extension in ALLOWED_PLAIN_EXTENSIONS):
        file = open(filename, "r")
    else:
        if not noConsoleOutput:
            print("ERROR: Unknown file format: " + extension + ", file skipped.")
        return
    try:
        for line in file:
            if compressed:
                line = line.decode("utf-8")
            if headerlinefound == False:
                headerlinefound= True
                headerLine = line
                # new header output:
                resultLineAcc.append(header(headerLine, epoch))
                continue
            lineAccumulator.append(line)
            lineCount = lineCount + 1
            if (len(lineAccumulator) >= linesNeeded):
                try:
                    resultLineAcc.append(epochConversion(lineAccumulator, getTimeStamp(headerLine,(lineCount - (len(lineAccumulator)-1)), daylightSavingsTime)))
                    lineAccumulator.clear()
                except IndexError:
                    if not noConsoleOutput:
                        print("ERROR: Line around line number" + lineCount + " seems corrupted and missing a value. "
                                                                         "File conversion was aborted.")
                    return
                except AttributeError:
                    if not noConsoleOutput:
                        print("ERROR: time stamp creation failed, check sample rate defined equals the program defined sampling "
                          "rate ")
                    return
            if len(resultLineAcc) >= WRITE_BUFFER:
                writePart(outputFile, resultLineAcc, noConsoleOutput)
                resultLineAcc.clear()
        # write the remaining details into the output file
        if resultLineAcc:
            writePart(outputFile, resultLineAcc, noConsoleOutput)
    finally:
        file.close()


def epochConversion(lines, timestamp):
    """
    Takes a list of lines and a time stamp and creates the average and a overarching time stamp and returns the line
    :param lines: list of lines to be averaged
    :param timestamp: a timestamp to be put at the start of a line
    :return: the average line created form the list of lines
    """
    imputedCount = 0
    lineCount = 0
    values = []
    average= -1
    imputedPerc = -1
    for line in lines:
        lineContent = str(line).split(",")
        if len(lineContent) != 2 | (lineContent[0] == ""):
            # the line does not match what we would expect
            continue
        values.append(float(lineContent[0]))
        if lineContent[1].strip() == "1":
            imputedCount = imputedCount + 1
        lineCount = lineCount + 1
    if len(values) != 0:
        imputedPerc = imputedCount / lineCount
        average = sum(values)/ float(len(values))
    # all values are read
    # create new line
    resultLine = "\n{}\t{}\t{}".format(timestamp, "{0:.1f}".format(average), "{0:.2f}".format(imputedPerc))
    return resultLine

def writePart(outfile, content, noConsoleOutput=False):
    """
    takes a path to a file and appends content  (list of strings) to it
    :param outfile: absolute path to write to
    :param content: content that should be appended
    :param noConsoleOutput: whether errors should be displayed
    :return: none
    """
    file = open(outfile, "a")
    try:
        for line in content:
            file.write(line)
    except:
        if not noConsoleOutput:
            print("ERROR: Failed to write to: " + outfile + " please check file.")
    finally:
        file.close


def getFiles(inputFiles):
    """
    get files takes a plain text file containing paths and will return a list of absolute paths of the paths
    specified in the file.
    :param inputFiles: the file containing the paths
    :return: a list object containing the absolute paths
    """
    fileList = []
    if os.path.isfile(inputFiles):
        file = open(inputFiles, "r")
        dir = os.path.dirname(os.path.realpath(inputFiles))
        for line in file:
            fileList.append(os.path.join(dir,line.strip(" \n\t")))
    else:
        # it is a directory
        for file in os.listdir(inputFiles):
            fileName = os.path.join(inputFiles, file)
            if (os.path.isfile(fileName) & (
                    (os.path.splitext(fileName)[1] == ".csv") | (fileName.endswith(".csv.gz")))):
                fileList.append(fileName)
    return fileList


def main():
    """
    main function to process a list of files to be converted into a new epoch
    :return: none
    """
    parser = argparse.ArgumentParser(description="Epoch Conversion")
    #parser.add_argument("-f", dest= "fileSet",  action='claimInput', const= help= " If this flag is set, IL may be
    #  file locations directly entered into the command line.")
    parser.add_argument("inlis", metavar="IL",  help="A plain text document containing the list of files to be converted")
    parser.add_argument("epochTime", metavar="t", type= int, help="epoch duration to convert to. "
                                                       "This should be a multiple of the orginal epoch time of 5 "
                                                                  "seconds.")
    parser.add_argument("outputDir", metavar="OD", help="output directory for the results")
    parser.add_argument("-p", metavar="Prefix", required= False, help= "prefix for the output files. Otherwise the "
                                                                       "old name will be used, with the addition of "
                                                                       "_avg_[epoch].")
    parser.add_argument("-id", action="store_true" , help= "If the original filenames are a specific id, which "
                                                           "should be conserved, this flag should be set. It does"
                                                           " not need to be used, when no prefix is specified")
    parser.add_argument("-d", action="store_true", help= "If set, the timestamps will change according to "
                                                         "daylight saving time.")
    parser.add_argument("-o", action="store_true", help= "If a file already exists e.g. from a previous run it will "
                                                         "be skipped")
    # parser.add_argument("-f", action="store_true", help= "When this option is selected the input in IL will be treated "
    #                                                      "as a directory of files instead of a file")
    parser.add_argument("-n", action="store_true", help="This option should be selected if no console output should be "
                                                        "made, e.g. when no non-shared console is available. In this "
                                                        "case only error messages will be displayed.")
    args = parser.parse_args()
    inputFiles = args.inlis
    epoch = int(args.epochTime)
    outdir = args.outputDir

    # initial sanity check
    if not((epoch % EPOCH_TIME) == 0):
        if(not args.n):
            print("ERROR: entered epoch time does not fit base epoch time")
        return
    if (epoch / EPOCH_TIME < 1):
        if not args.n:
            print("ERROR: requested epoch to short to be generated from given data")
        return
    extension = os.path.splitext(inputFiles)[1]
    if ((extension != ".txt") & (os.path.isfile(inputFiles))):
        if not args.n:
            print("ERROR: the specified list of input files of the " + extension + " does not match the required type of .txt")
        return
    # get input files into a list
    try:
        inList = getFiles(inputFiles)
        if not args.n:
            print("STATUS: " + str(len(inList)) + " files were detected and will be converted.")
    except IOError:
        if not args.n:
            print("ERROR: could not read the file of input files "+ inputFiles + ". Please check.")
        return
    prefix = ""
    if args.p:
        prefix = args.p

    index = 0
    for file in inList:
        if os.path.dirname(file) == outdir:
            if not args.n:
                print("ERROR: Due to the input and output directory being the same this file could not be processed, "
                  "withouth risking overwriting.")
            continue
        start= datetime.datetime.now()
        if not args.n:
            print("STATUS: Analyzing file " + file)
        if args.p:
            prefixIndex = "{}_{:04d}".format(prefix, index)
        else:
            prefixIndex = ""
        try:
            workFile(file, epoch, outdir, prefixIndex, args.id, args.d, args.n, args.o)
        except FileNotFoundError:
            if not args.n:
                print("ERROR: The file: " + file + " could not be found under the specified path.")
                traceback.print_exc()
        finish = datetime.datetime.now()
        timeUsed = finish - start
        if not args.n:
            if PREFIX_SET:
                print("STATUS: Finished file " + prefixIndex + " , saved in " + os.path.abspath(outdir) + " in " + str(timeUsed))
            else:
                print("STATUS: Finished file " + file + " , saved in " + os.path.abspath(outdir) + " in " + str(timeUsed))
        index = index +1


# main script
if __name__ == "__main__":
    main()
