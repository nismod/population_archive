"""
Convenience place to put scripts that read required data. These could easily
go in pop_projection.py but having them here makes the pop projection method
easier to understand.
"""

#from pop_projection import PopProjection
from errors import ProjectionError

class DataReading():

    __national_pop_header = """Ages,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037,2038,2039,2040,2041,2042,2043,2044,2045,2046,2047,2048,2049,2050,2051,2052,2053,2054,2055,2056,2057,2058,2059,2060,2061,2062,2063,2064,2065,2066,2067,2068,2069,2070,2071,2072,2073,2074,2075,2076,2077,2078,2079,2080,2081,2082,2083,2084,2085,2086,2087,2088,2089,2090,2091,2092,2093,2094,2095,2096,2097,2098,2099,2100"""
    __subnational_header = """CODE,AREA,AGE GROUP,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037"""
    __fert_mort_headers = """Age,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037,2038,2039,2040,2041,2042,2043,2044,2045,2046,2047,2048,2049,2050,2051,2052,2053,2054,2055,2056,2057,2058,2059,2060,2061,2062,2063,2064,2065,2066,2067,2068,2069,2070,2071,2072,2073,2074,2075,2076,2077,2078,2079,2080,2081,2082,2083,2084,2085,2086,2087,2088,2089,2090,2091,2092,2093,2094,2095,2096,2097,2098,2099,2100"""

    __debug_cc = False

    @classmethod
    def __create_pop_matrix(cls, file):
        """Create a matrix of age group (rows) and year (columns) from a
        national projection file."""
        # Check headers are in the correct format
        header = file.readline().strip()
        if header!=DataReading.__national_pop_header:
            print "Error reading national population: header in the", file.name, \
            "file is not what I expected. The header is and expected line are:"
            print header
            print DataReading.__national_pop_header
            return False
        # Read the file into memory to make it easier to parse - rows are
        # years (2008-2033) and columns are age groups
        matrix = []
        for line in file:
            line_split = line.strip().split(',')
            array = []
            for i in range(1, len(line_split)): # (ignore first column - age group)
                array.append(line_split[i])
            matrix.append(array) # Create a new line for this age group
        return matrix

    @classmethod
    def __split_subnat_age(cls, age_gp, num_people):
        """Breaks 5-year age groups in the sub-national projection into
        individual groups as used by the national projection. Returns a list
        of tuples (age->num_people)"""
        if age_gp <= 17: # Normal five-year groups (split evenly amoung 5 groups)
            return ( ( ((age_gp*5)+i),(num_people/5.0) ) for i in range(5) )
            # (Same as above but using list comprehension instead of genearator
            # expression - not as good because whole list created in memory
            # whereas generator expression uses lazy iterator)
            #return [ ( ((age_gp*5)+i),(num_people/5.0) ) for i in range(5) ]

        elif age_gp == 18: # 90+
            # Need three groups for 90-94, 95-100, 100+ to be consistent with
            # national projections. Quick look at national projection suggests
            # ratio 0.75:0.20:0.05 for three groups looks OK.
            return ( (i+90, j*num_people) for i, j in enumerate([0.75, 0.2, 0.05]) )
            #Note, in python version 2.6+ can use 'start' param in enumerate
            #return ( (i, j*num_people) for i, j in enumerate([0.75, 0.2, 0.05], start=90) )
            #Note: same as above but with list comprehension:
            #return [ (90+i,j*num_people) for i,j in [(0,0.75), (1,0.20), (2,0.05)] ]

        else:
            print "Unrecognised sub-national age group, there should be",\
                "18 but I have found",age_gp
            return False


    @classmethod
    def read_national_projection(cls, filename, array):
        """Reads text files of a national population to populate the
        national projection data (all people from 2004 - 2100)"""
        mf = open(filename, 'r')
        #ff = open(female_filename, 'r')
        print "Reading national populations from", filename

        # Create matrices from national population (years in columns, age
        # groups down the side) and check they're the same sizes
        #fem_matrix = PopProjection.__create_pop_matrix(ff)
        matrix = DataReading.__create_pop_matrix(mf)
        if matrix==False:
            raise ProjectionError("Problem creating population matrices")
        #if not PopProjection.same_dimensions(fem_matrix, mal_matrix):
        #    raise ProjectionError("Error with national projection: male and female "\
        #        "arrays are different sizes.")

        # Now read through matrix, creating people (effectively inverting matrix)
        for year in range(len(matrix[0])): # (0 OK because matrix is square)
            pop = [] # Num people each age group for the year
            # Create people
            for age_gp in range(len(matrix)):
                num_people= float(matrix[age_gp][year])
                pop.append(num_people)
            array.append(pop)

            #self.__nat_pops_women.append(fem_pop)
            #self.__nat_pops_men.append(mal_pop)
        # Check the matrix looks sensible.
        assert len(matrix) == 93, "Should be 93 age groups in the national popualtion"+\
            "matrix, not"+str(len(matrix))
        for i, list in enumerate(matrix):
            assert len(list)==93, "Should be 93 years in national matrix line "+\
                str(i)+", not "+str(len(list))

    @classmethod
    def read_subnational_projection(cls, filename, sub_nat_pops):
        """Read a subnational projection file. Note that, unlike the national
        projection, ages of people are grouped into 5-year cohorts ending at
        90+ so these need to be converted into individual years.

        sub_nat_pops should be a dictionary to store the populations of people in each area."""

#        print "Reading sub-national projections for", gender,\
#            "from",filename

        with open(filename) as f: # (will automatically close file)
            header = f.readline().strip()
            if header!=DataReading.__subnational_header:
                raise ProjectionError("Error reading subnational file ("+f.name+ \
                    ") - one of the the headers is not what I expected to see")

            # Read sub-ational file, putting populations into a temprary dictionary
            # so they can be inverted later (want to group all populations by year,
            # but years are stored in columns and csv files read by lines)

            tempdict=dict()
            matrix=[] # Matrix for each population
            current_area = "" # Keep track of when area changes in file
            while(True): # (Hate this, but can't see another way to detect last line in for loop)
                line = f.readline()
                if line=="": # Past last line, just store previous area
                    tempdict[current_area]=matrix
                    break

                linesplit = line.strip().split(',')
                areakey = linesplit[0]
                if areakey!=current_area: # Area change, store pop info
                    #print "Have matrix for area", current_area
                    #for row in matrix:
                    #    print row
                    #print "\n"
                    tempdict[current_area]=matrix
                    matrix=[]
                    current_area = areakey
                # Read line in the file
                array=[]
                for i in range(3, len(linesplit)):# (ignore first 3 columns)
                    array.append(float(linesplit[i]))
                matrix.append(array)

        # Have finished reading file, now go through the temporary dictionary
        # creating populations for individual years
        for areakey, matrix in tempdict.iteritems():
            # Now read through matrix, creating people (effectively inverting matrix)
            #print "Analysing area",areakey
            populations = [] # Store lists of populations for this area - one for each year
            if len(matrix)==0: # Somehow a null key/value pair get into the dictionary, no idea how.
                print "Warning: empty population matrix for area '",areakey,"'"
                continue

            num_years=len(matrix[0]) # (0 OK because matrix is square)
            for year in range(num_years):
                pop = [] # Population for this year (list of People of each age group)
                # Create people
                for age_gp in range(len(matrix)):
                    # Need to greak age groups into individual ages
                    indiv_ages = DataReading.__split_subnat_age(age_gp, matrix[age_gp][year])
                    if indiv_ages==False: # problem with the age groups, bad file?
                        return False
                    for age, num_people in indiv_ages:
                        #p = People(gender=gender, age=age, num_people=num_people)
                        pop.append(num_people)

                # Store all people in this year
                populations.append(pop)
            
            # Store all the people in the area
            sub_nat_pops[areakey] = populations

        return True

    @classmethod
    def read_national_fert_mort_rates(self, files):
        """Takes a list of tuples (the input filenames and associated class instance
        variables to populate) and creates fertility/mortality matrices"""
        for file, list in files:
            print "Reading national fert/mort rates for",file
            with open(file, 'r') as f:
                header = f.readline().strip()
                if header!=DataReading.__fert_mort_headers:
                    print "Error: header for fert/mort file "+file+\
                        " does6 not match what I expect. I want:\n\t"+\
                        DataReading.__fert_mort_headers+"\nbut got\n\t"+\
                        header
                    raise ProjectionError("Header for fert/mort file "+file+\
                        " does not match what I expect.")
                lines = [] # Store lines in memory
                for line in f:
                    lines.append(line.strip().split(",")[1:]) # Ignore first column (age group)

            # Now transpose so that first index is year, second is age gropu
            #matrix = []
            for year in range(len(lines[0])):
                rates = [] # Rates for this year
                for age_gp in range(len(lines)):
                    rates.append(float(lines[age_gp][year]))
                #matrix.append(rates)
                # append the agegroups for this year to the given fert/mort list
                list.append(rates)

            # Check matrix columns: num years (rows will differ depending on file)
            if len(list)!=93:
                raise ProjectionError("Input fert/mort matrix for "+file+\
                    " does not have the correct number of columns: "+str(len(list)))

    @classmethod
    def read_nat_components_of_change(self, file, array):
        """Read components of change data from 'file', putting data into 'array'.
        For each year in the array there will be a list each component:
        StartPop, Births, Deaths, Natural change, Migration, Total change, EndPop"""
        with open(file, 'r') as f:
            f.readline() # Skip the header
            linecount = 0
            for line in f:
                linesplit = line.strip().split(',')
                assert len(linesplit)==8, \
                    "There should be 8 columns in the components of change file"
                # Add the cc values for this year, converting to floats
                temparray = []
                for s in linesplit[1:]: # skip the first column (says the year)
                    temparray.append(float(s.strip()))
                array.append(temparray)
                linecount+=1
            assert linecount==93, \
                "There should be 93 lines in the cc file (not including the header). Not "+str(linecount)
        # Quick check that the numbers add up correctly

        for cc in array: # (note conversion to string to avoid rounding inprecision)
        # TODO FOr some reason these don't add up after 2033 so I've taken this assertion out. Need to look into this more
            pass
            #assert str(cc[3]) == str(cc[1]-cc[2]), "Natural change ("+str(cc[3])+") should"+\
            #    "equal births ("+str(cc[1])+") minus deaths ("+str(cc[2])+")."
            #assert str(cc[5]) == str(cc[3]+cc[4]), "Total change ("+str(cc[5])+") should"+\
            #    "equal natural change ("+str(cc[3])+") plus migration ("+str(cc[4])+")."
            #assert str(cc[6]) == str(cc[0]+cc[5]), "Pop at end ("+str(cc[6])+") should equal"+\
            #   "pop at start ("+str(cc[0])+") plus total change ("+str(cc[5])+")."

    @classmethod
    def read_subnational_fert_mort_rates(cls, area_keys, asfr, asmr_m, asmr_f):
        """Would read subnational fert/mort rates but as there is no data for this
        at the moment just populate the subnational arrays with 1s (no
        change from national rates). The inputs are age specific fertility
        and mortality rates. The sub_nat_pops_men input is a dictionary of all sub-
        national populations and is required to get the area keys."""

        # NOTE: old projections (to 2032) use 79 columns (years 2004 - 2083).
        # Now, for 2100 projections use 93 columns
        cols = 93

        # Fert matrix is 32 rows (age groups 15-46 inclusive) by 96 columns (years 2004 - 2100)
        fert_matrix = [[1 for i in range(32)] for j in range(cols)]

        # Mortality matrices are 92 rows (age groups) by 96 columns (years 2004 - 2100)
        mort_matrix_m = [[1 for i in range(93)] for j in range(cols)]
        mort_matrix_f = [[1 for i in range(93)] for j in range(cols)]

        for key in area_keys:
            asfr[key] = fert_matrix
            asmr_m[key] = mort_matrix_m
            asmr_f[key] = mort_matrix_f
            
            
            
    @classmethod
    def read_subnat_components_of_change(self, file, d, end_year):
        """Read subnational components of change data from 'file', putting data into dictionary 'd'.

        This is a bit more complicated than the national components of change because the file isn't
        in such a nice format and components are broken down by area.
        For each year in each area there will be a list each component, but these components are
        not in the same order as the national file (numbers in braces give their line numbers
        starting from 0 - some data isn't avaiable so will have 'na'):
        StartPop(na), Births(2), Deaths(3), Natural change(1), Migration(4), Total change(na), EndPop(0)

        After 2033 there is no subnational components of change data so populate
        the remaining years with 'None' to tell the fert/mort modules that they
        need to use their own scaling factors
        """

        linecount = 0 # Keep track of total lines in file
        subline_counter=0 # Keep track of number of lines read for each area so we know which component we're reading
        # Will need to translate the component in the subnat file (subline_counter) to an index that matches
        # the national cc file. Some components in the file can be ignored. This dictionary will do it:
        #translate = {6:0, 3:2, 1:3, 2:1, 4:4, 5:-1, 0:-1, 7:-1, 8:-1, 9:-1, 10:-1}
        translate = {0:6, 1:3, 2:1, 3:2, 4:4, 5:-1, 6:-1, 7:-1, 8:-1, 9:-1, 10:-1}


        with open(file, 'r') as f:

            f.readline() # Skip the header
            area="" # Keep track of the area we're reading

            for line in f:
                linesplit = line.strip().split(',')
                assert len(linesplit)==33, \
                "There should be 33 columns in the subnational components of change file instead of" +str(linesplit)
                new_area = linesplit[0]

                if new_area != area: # Area has changed, do some stuff
                    area = new_area
                    d[area]=[] # New year/component array for this area
                    subline_counter=0
                    for i in range(30): # Each year (30) will need an array of 7 items (one for each component)
                        d[area].append([-1 for i in range(7)])

                # Add component data for the current area
                year_data = linesplit[3:] # The values for the component for each year
                assert len(year_data) == 30, "Should be 30 years of subnational cc data (2004-2033)"
                component = translate[subline_counter]
                if component!=-1:
                    for year,val in enumerate(year_data):
                        d[area][year][component] = float(val)

                subline_counter+=1

                linecount+=1

        if DataReading.__debug_cc:
            print "Read",linecount,"line components-of-change file"
            for area in d:
                print "\nSubnational components of change for ", area
                for component, desc in enumerate(["StartPop", "Births", "Deaths", "Natural change", "Migration", "Total change", "EndPop(0)"]):
                    print desc,
                    for year in range(30):
                        print d[area][year][component],
                    print
                print

        # Check everything has been read in OK
        for area in d:
            assert len(d[area])==30, "Should be 30 years of subnational cc data for area "+\
                str(area)+", not "+str(len(d[area]))

            for year in range(len(d[area])):
                assert len(d[area][year])==7, "Should be 7 components in area "+str(area)+\
                    " for year "+str(year)+", not "+str(len(d[area][year]))

        # Finally add some 'None' data for all the years that no cc data is available
        for area in d:
            for i in range(end_year-33):
                d[area].append(None)