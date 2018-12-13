# Epoch Conversion Script

## Summary

A script which takes a csv file or a csv.gz file, containing 
accelerometer data recorded at 5 second epochs, or whatever value is defined as the EPOCH_TIME internally, and 
converts it to a file with a different epoch interval and labels
it with timestamps.

## Operation

### File Requirements
    //TODO
### Standalone Operation
Run via the terminal using 

    python epochConv.py [-h] [-p Prefix] [-id] [IL] [t] [OD]
    
where the arguments represent the following:
   + -h : A terminal explanation of this paragraph, similar to other console applications.
   + -p : Optional argument that allows the specification of a new filename (prefix), which
           will consist of the supplied file and a four digit padded integer number, increasing
           throughout the runtime of the program, whenever a new file is analyzed.
   + -id :  In case the files, needing conversion, have important information in the file name, e.g. an ID, this flag can be set to         retain the existing file name, but to use the prefix and the index, defined by -p before it. It should not be used if -p is not specified, as the existing file name will be used any way, retaining the information.
   + IL : A plain text (.txt) document containing 
           the list of files to be converted. It has to be keept in mind that currently only .csv.gz and .csv are permitted. In future version or branches of this software new file types can be supported, by adding them to the 
   + t : epoch duration to convert to. This should be a
          multiple of the orginal epoch time of 5 seconds but can be 5 seconds.
   + OD : output directory for the results

### Integrated Operation
    //TODO
