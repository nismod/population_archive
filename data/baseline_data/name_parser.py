from __future__ import with_statement # for reading files using 'with' statement

with open('full_area_names.csv', 'r') as f:
  areas = {}
  area = ""
  for line in f:
    linesplit = line.strip().split(',')
    if len(linesplit)!=2:
      print "Error on line",line
      exit()
    
    a = linesplit[0]
    b = linesplit[1]
	
    # Looking for 'a' to be a single character code (and not a number).
	# This is the new region that the following districts are part of.
    if len(a)==1:
	  try:
		int(a)
		print "Ignoring line",line
	  except: # Code is not a number so it should be the new code
		areas[b] = []
		area = b


    elif len(a)==4:
      if a not in areas[area]:
	areas[area].append(a)
    
    elif len(a)==2:
      print "Ignoring line",line

with open('area_lookup.csv', 'w') as f:

  for area in areas:
    f.write(area+",")
    for region in areas[area]:
      f.write(region+",")
    f.write("\n")

  print "Have written area_lookup.csv"
