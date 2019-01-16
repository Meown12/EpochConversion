# Epoch Conversion Script

## Summary

A script which takes a csv file or a csv.gz file, containing 
accelerometer data recorded at 5 second epochs, or whatever value is defined as the EPOCH_TIME internally, and 
converts it to a file with a different epoch interval and labels
it with timestamps.

## Operation

### Requirements
#### Script Requirements
To use this script the pytz module is required, as otherwise the Daylight Savings Time adjustment could not be performed with ease.
#### Input File Requirements
This section mainly refers to the files that should be processed, as the script input is just a text file with the file locations in it. The script is built to be used with .csv or .csv.gz files it does however work with all plain uncompressed types, as long as they follow the standard of the comma seperated values, and their extension is marked as supported in the script (currently .csv and .txt). One important requirement of the script is the  header of the input file which needs to follow a certain pattern to be reckognized. `[w] [w] [w] [start_date] [start_time] [w] [end_date] [end_time] [w] [w] [w] [sample_rate] [w] `,with `[w]` being any continuous string, which will be ignored `[start_date]` and `[end_date]` are expected to be YYYY-MM-DD whilst times are expected as HH:MM:SS.

#### Output File Requirements
The created output file will overwrite identically named files in the specified output directory. Therefore the -p (and -id) options should be selected, when running the script, to avoid data loss for multiple runs.

### Standalone Operation
Run via the terminal using 

```
python epochConv.py [-h] [-p Prefix] [-id] [-d] [-n] [-o] [IL] [t] [OD]
```
    
where the arguments represent the following:
   + -h : A terminal explanation of this paragraph, similar to other console applications.
   + -p : Optional argument that allows the specification of a new filename (prefix), which
           will consist of the supplied file and a four digit padded integer number, increasing
           throughout the runtime of the program, whenever a new file is analyzed.
   + -id :  In case the files, needing conversion, have important information in the file name, e.g. an ID, this flag can be set to         retain the existing file name, but to use the prefix and the index, defined by -p before it. It should not be used if -p is not specified, as the existing file name will be used any way, retaining the information.
   + -d : If this flag is selected the created timestamps for the output will adjust for a change in time due to daylight   
          savings time, meaning the time stamp will reduce or increase by an hour when it encounters the respective time.
   + -n : With this flag set all command line outputs of the script will be suppresed.
   + -o : If an output file already exists e.g. from a previous run it will be skipped during the conversion.
   + IL : A plain text (.txt) document containing 
          the list of files to be converted. It has to be keept in mind that currently only .csv.gz and .csv are permitted. In future version or branches of this software new file types can be supported, by adding them to the 
   + t : epoch duration to convert to. This should be a
          multiple of the orginal epoch time of 5 seconds but can be 5 seconds.
   + OD : output directory for the results

### Integrated Operation
   To integrate this script/functionality in other code it can be recommended to call the 
   ```python
   def workFile(filename, epoch, outdir, prefix="", keepName=False, daylightSavingsTime=False, noConsoleOutput=False)
   ``` 
   function, which will convert one file, which absolute path should be specified in `filename` to a file with either the name
   specified in `prefix` or the file name of `filename` or both, depending on the state of the boolean `keepName`, intended to
   be used to preserve the given file name. The file created will then be saved in `outdir`, which can either be an absolute or
   relative path. When `daylightSavingsTime` is set the function will behave as if -d would have been selected in the command
   line call. Similar applies to `noConsoleOutput`, which functions like -n.
