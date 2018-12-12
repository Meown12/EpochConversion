# Epoch Conversion Software

## Summary

A script which takes a csv file containing 
accelerometer data recorded at 5 second epochs and 
converts it to a file with a different epoch interval and labels
it with timestamps.

## Operation

Run via the terminal using 

    python epochConv.py [IL] [t] [OD]

where the arguments represent the following:
   + IL : A plain text document containing 
           the list of files to be converted
   + t : epoch duration to convert to. This should be a
          multiple of the orginal epoch time of 5 seconds.
   + OD : output directory for the results
