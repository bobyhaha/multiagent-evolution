import csv,sys
if sys.argv[1:] == ['count']:
 print(max(0,len(list(csv.reader(sys.stdin)))-1))
else:
 sys.exit(1)
