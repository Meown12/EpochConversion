import argparse
import gzip
import datetime
import os
import pytz

EPOCH_TIME = 5 #assumed EPOCH time in previous
WRITE_BUFFER = 100 # the number of conversions done before the results are logged into the outputfile
ALLOWED_PLAIN_EXTENSIONS = [".csv", ".tsv", ".txt"] # non compressed file types this script assumes to be able to operate with.
PREFIX_SET = False
TIMEZONE = "Europe/London"
# TODO Daylight Savings time conversion, when inside measuring area
"""
Function expects the header line to be in the following format:
[w] [w] [w] [start_date] [start_time] [w] [end_date] [end_time] [w] [w] [w] [sample_rate] [w]
with [w] being any continuous string, which will be ignored
[start_date] and [end_date] are expected to be YYYY-MM-DD
whilst times are expected as HH:MM:SS

"""
def getTimeStamp(headerLine, offsetLine, dayLightSavingsTime):
    timeStamp = ""
    headerInfo = str(headerLine).split(" ")
    startDate = headerInfo[3]
    startTime = headerInfo[4]
    endDate = headerInfo[6]
    end_time = headerInfo[7]
    sample_rate = int(headerInfo[11])
    if sample_rate != EPOCH_TIME:
        raise AttributeError
    #calculate offset:
    offsetSec = offsetLine * EPOCH_TIME
    offset = datetime.timedelta(seconds= offsetSec)
    startInfo = startDate + " " + startTime
    gmt = pytz.timezone(TIMEZONE)
    startDateTime = datetime.datetime.strptime(startInfo, '%Y-%m-%d %H:%M:%S').astimezone(gmt)
    currentTime = startDateTime + offset
    if dayLightSavingsTime:
        nullTime = datetime.timedelta(0)
        if ((startDateTime.dst() != nullTime) & (currentTime.dst() == nullTime)):
            # dst ended during the measurement, take one hour of the offset
            currentTime = currentTime - datetime.timedelta(hours=1)
        elif ((startDateTime.dst() == nullTime) & (currentTime.dst() != nullTime)):
            currentTime = currentTime + datetime.timedelta(hours=1)
    timeStamp = currentTime.strftime("%Y-%m-%dT%H:%M:%S")

    #"{}-{}-{}T{}:{}:{}".format(currentTime.year, currentTime.month, currentTime.day, currentTime.hour,
                 #                          currentTime.minute, currentTime.second)
    return timeStamp


def header(headerLine, epoch):
    oldheaderString = str(headerLine).split(" - ")
    startInfo = datetime.datetime.strptime(oldheaderString[1], '%Y-%m-%d %H:%M:%S')
    endInfo = datetime.datetime.strptime(oldheaderString[2], '%Y-%m-%d %H:%M:%S')
    newHeader = "Measurement from " + startInfo.strftime("%Y-%m-%d %H:%M:%S")
    newHeader = newHeader + " to " + endInfo.strftime("%Y-%m-%d %H:%M:%S")
    newHeader = newHeader + "\t" + oldheaderString[0] + " - sampleRate = " + str(epoch)
    newHeader = newHeader + "\t" + "fraction of imputed data"

    return newHeader


def getOutFileName(filename, outdir, epoch, prefix, keepName):
    outdir = os.path.realpath(outdir)
    if prefix != "":
        if keepName:
            outfile = os.path.join(outdir,prefix + "_" +os.path.splitext(os.path.basename(filename))[0] +".tsv")
        else:
            outfile = os.path.join(outdir, prefix + ".tsv")
    else:
        outname = os.path.splitext(os.path.basename(filename))[0] + "_avg_{}.tsv".format(epoch)
        outfile = os.path.join(outdir, outname)
    return outfile



def workFile(filename, epoch, outdir, prefix, keepName, daylightSavingsTime, noConsoleOutput):
    #
    # how many lines need to be read to convert one 5 second epoch to the new epoch time EPOCH
    linesNeeded = epoch/EPOCH_TIME
    lineAccumulator = []
    resultLineAcc = []
    lineCount = 0
    headerlinefound = False
    headerLine = ""
    outdir = os.path.realpath(outdir)
    extension= os.path.splitext(filename)[1]
    outputFile = getOutFileName(filename, outdir, epoch, prefix, keepName)  #TODO should they have identical names?
    # if this file exists already, delete it.
    try:
        os.remove(outputFile)
    except OSError:
        pass
    # find out whether to gzip open or to plain open it
    compressed = False
    if (extension == ".gz") & (".csv.gz" in os.path.basename(filename)):
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
                #TODO print header on top of file
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
    # generate new timestamp

def epochConversion(lines, timestamp):
    imputedCount = 0
    lineCount = 0
    values = []
    for line in lines:
        lineContent = str(line).split(",")
        values.append(float(lineContent[0]))
        if lineContent[1].strip() == "1":
            imputedCount = imputedCount + 1
        lineCount = lineCount + 1
    imputedPerc = imputedCount / lineCount
    average = sum(values)/ float(len(values))
    # all values are read
    # create new line
    resultLine = "\n{}\t{}\t{}".format(timestamp, "{0:.1f}".format(average), "{0:.2f}".format(imputedPerc))
    return resultLine

def writePart(outfile, content, noConsoleOutput):
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

    file = open(inputFiles, "r")
    fileList = []
    dir = os.path.dirname(os.path.realpath(inputFiles))
    for line in file:
        fileList.append(os.path.join(dir,line.strip(" \n\t")))
    return fileList



def main():
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
    if (extension != ".txt"):
        if not args.n:
            print("ERROR: the specified list of input files of the " + extension + " does not match the required type of .txt")
        return
    # get input files into a list
    inList = getFiles(inputFiles)
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
            workFile(file, epoch, outdir, prefixIndex, args.id, args.d, args.n)
        except FileNotFoundError:
            if not args.n:
                print("ERROR: The file: " + file + " could not be found under the specified path.")
        finish = datetime.datetime.now()
        timeUsed = finish - start
        if not args.n:
            if PREFIX_SET:
                print("STATUS: Finished file " + prefixIndex + " , saved in " + outdir + " in " + str(timeUsed))
            else:
                print("STATUS: Finished file " + file + " , saved in " + outdir + " in " + str(timeUsed))
        index = index +1
# main script
if __name__ == "__main__":
    main()