# This file is part of PopProjection.

# PopProjection is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

# PopProjection is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PopProjection.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import with_statement # for reading files using 'with' statement

import random

from errors import ProjectionError

class PRMConverter():

    """
    This program takes projection data and creates a file that is in a format
    the Population Reconstruction Model (PRM) can read. Therefore this can be
    used to run PRM simulations using projected data.

    The output data should look like this:

    OA, NHH, Npers, detached, semi, terraced, flat, zero_to_nine, Age_10_to_19, Age_20_to_29, Age_30_to_39, Age_40_to_49, Age_50_to_59, Age_60_to_69, Age_70_to_79, Age_80plus, car_none, car_one, car_two_plus, Economically_Active, Economically_Inactive, White, Asian, Black, Other, Good, Fair, Not_good, house_size_1, house_size_2, house_size_3, house_size_4, house_size_5, house_size_6, house_size_7, house_size_8_plus, house_represent_1, house_represent_0, with_LLTI, without_LLTI, SWD, Married, Prof_manag, Intermediate, Non_manual, unemployed, student, no_qualifications, Level_1_2, Level_3_plus, room_1_4, room_5_6, room_7_plus, Males, Females, Owned, Council, Private_rented
    00HBNM0001, 123, 283, 3, 8, 108, 4, 40, 31, 52, 59, 53, 17, 12, 10, 9, 34, 63, 23, 156, 45, 199, 17, 77, 16, 192, 59, 27, 31, 53, 22, 9, 4, 3, 0, 0, 123, 160, 43, 235, 216, 62, 56, 13, 26, 3, 19, 39, 57, 107, 41, 64, 19, 142, 141, 97, 12, 13
    00HBNM0002, 120, 253, 0, 8, 29, 83, 48, 30, 57, 56, 24, 8, 17, 10, 3, 74, 40, 10, 103, 83, 141, 17, 135, 4, 180, 57, 29, 54, 38, 12, 7, 9, 0, 0, 0, 120, 133, 56, 210, 225, 41, 25, 5, 35, 20, 31, 49, 49, 87, 79, 32, 13, 117, 136, 23, 78, 21
    
    """

    header = "OA, NHH, Npers, detached, semi, terraced, flat, zero_to_nine, Age_10_to_19, Age_20_to_29, Age_30_to_39, Age_40_to_49, Age_50_to_59, Age_60_to_69, Age_70_to_79, Age_80plus, car_none, car_one, car_two_plus, Economically_Active, Economically_Inactive, White, Asian, Black, Other, Good, Fair, Not_good, house_size_1, house_size_2, house_size_3, house_size_4, house_size_5, house_size_6, house_size_7, house_size_8_plus, house_represent_1, house_represent_0, with_LLTI, without_LLTI, SWD, Married, Prof_manag, Intermediate, Non_manual, unemployed, student, no_qualifications, Level_1_2, Level_3_plus, room_1_4, room_5_6, room_7_plus, Males, Females, Owned, Council, Private_rented"

    # Need to store proportions of people who are heads of household per
    # age and district for estimating number of households
    # Ages will be single-year groups (as with projections)
    # Dictionary of headship counts (area, year, age) used to calculate rates
    headship_counts = None # e.g. num heads in leeds, year 13, age 25: [00DA][13][25] = x
    
    # Remember areas with missing data (to cut down error messages)
    bad_areas = {}

    def __init__(self, populations_male, populations_female, base_pop_male, base_pop_female):
        """Constructor takes distionaries of projected male/populations.
        The base populations are needed for estimating headship rate (i.e. the
        probability of a person being the head of household).
        Key is subnational area (e.g. '00DA') and there is one list for each
        projected year then sub-lists for number of people per age group
        e.g. populations_male['00DA'][10][78] = num male 78 y/olds in year 10"""

        self.populations_male = populations_male
        self.populations_female = populations_female
        self.base_pop_male = base_pop_male
        self.base_pop_female = base_pop_female

        # Read data on households (stored in class level variable)
        self._read_headship_data()

    @classmethod
    def _group_ages(self, ages):
        """Group a list of people (num people per single year age group)
        into 9 groups that the prm expects:
        0-9, 10-19, 20-29, 30-39, 40-49, 50-59, 60-69, 70-79, 80+"""
        grouped = []
        for i in range(9):
            if i==8: # Group 80+
                grouped.append(sum(ages[80:]))
            else:
                grouped.append(sum(ages[i*10:(i*10)+10]))

#        for i,j in enumerate(ages):
#            print i,",",j

#        for i,j in enumerate(grouped):
#            print i,",",j

        return grouped

    def _read_headship_data(self):
        """Read some headship data (counts of households by age of head) and
        estimate trends"""

        # See if the data has already been read
        if PRMConverter.headship_counts != None:
            return

        # Read headship information for the first time.
        PRMConverter.headship_counts = {}

        with open("../data/headship_counts.csv", 'r') as f:
            print "Reading headship data from",str(f)
            linecount = 0
            for line in f:
                linecount+=1

                ls = line.split(",")

                area=ls[0]
                
                # Ignore lines without a properly formed district name
                if len(area) != 4:
#                    print "\t IGNORE 1"
                    continue
                # Ignore lines that don't have projection data
                elif area not in self.populations_male:
#                    print "\t IGNORE 2"
                    continue
                # This line should be OK, check it has the right number of columns
                # (16 age groups and two for district name/code)
                elif len(ls) != 18:
                    raise ProjectionError("Error reading household count data, line "+\
                        str(linecount)+" has "+str(len(ls))+" columns, not 18.")

                # This line is OK, store the number of households per age in 2008 and 2033
                numages = 8 # 8 age groups in input file: 0-25 25-34, 35-44, 45-54, 55-64, 65-74, 75-84, 85+
                age_counts_08 = map(int, ls[2:10]) # (also convert to int
                assert len(age_counts_08)==numages, str(len(age_counts_08))
                age_counts_33 = map(int, ls[10:18])
                assert len(age_counts_33)==numages, str(len(age_counts_33))

                # Calculate trends to end year (2100)

                # Gradient and y intercept for each year
                m = [ float(y2-y1) / float(2033-2008) for y1,y2 in zip(age_counts_08, age_counts_33) ]
                c = [ y - em*2033 for y,em in zip(age_counts_33,m)]

                years = [i for i in range(2008,2100+1)]
                house_trends = [] # Matrix of year, age

                for yr in years:
                    age_list = []
                    for age in range(numages):
                        estimate = m[age]*yr+c[age]
                        age_list.append(estimate)
                    house_trends.append(age_list)

                # Print the trends for info
                #print "\nHousehold trends (original age groups) \n"
                #for i,ht in zip(years,house_trends):
                #    print i,",",
                #    for k in ht:
                #        print k,",",
                #    print

                # Finally disaggregate ages into single-age groups assuming uniform distribution.
                # Original groups are 0-24 25-34, 35-44, 45-54, 55-64, 65-74, 75-84, 85+
                disag_trends = []
                for year in range(len(years)):
                    single_ages = []
                    for age in range(93):
                        if age < 25: # group 0: 0-24
                            single_ages.append(\
                                house_trends[year][0]/25.0)
                        elif age < 35: # group 1: 25-34
                            single_ages.append(house_trends[year][1]/10.0)
                        elif age < 45: # group 2: 35-44
                            single_ages.append(house_trends[year][2]/10.0)
                        elif age < 55: # group 3: 45-54
                            single_ages.append(house_trends[year][3]/10.0)
                        elif age < 65: # group 4: 55-64
                            single_ages.append(house_trends[year][4]/10.0)
                        elif age < 75: # group 5: 65-74
                            single_ages.append(house_trends[year][5]/10.0)
                        elif age < 85: # group 6: 75-84
                            single_ages.append(house_trends[year][6]/10.0)
                        # group 7: 85+.
                        # This one is really difficult to split. For now just assume
                        # that half the people are in single year groups (85-90) and
                        # remainer (in ratio 3:2:1) are in 90-95,95-100 and 100+
                        elif age < 90:
                            single_ages.append( (house_trends[year][7]*0.5) / 5.0)
                        elif age == 90:
                            single_ages.append( (house_trends[year][7]*0.2499))
                        elif age == 91:
                            single_ages.append( (house_trends[year][7]*0.1666))
                        elif age == 92:
                            single_ages.append( (house_trends[year][7]*0.0833))
                        else:
                            raise ProjectionError("Internal error, shouldn't be here.")

                    disag_trends.append(single_ages)

                # Print disaggregate trends for info
                #print "\nHousehold trends (single age groups) \n"
                #for i,j in zip(years,disag_trends):
                #    print i,",",
                #    for k in j:
                #        print k,",",
                #    print

                # Save the household trends
                PRMConverter.headship_counts[area] = disag_trends

        print "\t Finished reading household counts per age and esimating trends"

    def _estimate_households(self, area, year):
        """Estimate the number of households in a given area for a given year.
        Uses the headship counts per age group (already read in) to esimate a
        headship rate for each age group (i.e. the probability of a person being
        a head of household) and then esimate total housheolds by multiplying
        headship rates by number of people in each age group.
        """
        # Aggreate female/male populations (just want total population)
        male_pop = self.populations_male[area][year]
        female_pop = self.populations_female[area][year]
        base_male_pop = self.base_pop_male[area][year]
        base_female_pop = self.base_pop_female[area][year]
        assert len(male_pop) == len(female_pop) == len(base_male_pop)==len(base_female_pop)

        # Get the headship counts per age group
        heads = None
        try:
            # TODO Get headship information for all area (inc Scotland etc)
            heads = PRMConverter.headship_counts[area][year]
        except KeyError:
            if area not in PRMConverter.bad_areas:
                PRMConverter.bad_areas[area] = None
                print "Warning, no headship information for ", area
            return -1

        # Go through each age group and calculate the headship rate (num heads in
        # age group divided by base population for age group) and then estimate
        # number of households by multiplying by popualtion size
        hcount = 0
        for age in range(len(male_pop)):
            popn = float(base_male_pop[age]+base_female_pop[age])
            if popn <= 0.0: # need to check for div by zero
                popn=0.000001
            headship_rate = float(heads[age]) / popn
            households = headship_rate * (male_pop[age]+female_pop[age])
            hcount = hcount + households
            #if area=='00DA':
            #    print age, heads[age], headship_rate, households

        #if area=='00DA':
        #    print "TOTAL HOUSEHOLDS", hcount, "tot heads:", sum(heads)
        #    exit()

        return hcount



    def make_prm_table(self, file, year=0, select_areas=None):
        """Make prm-formatted table.
        'file' is the name (full path) of the file to write to. The year and a
        .csv extension will be appended to the name
        'year' is the year to write (index into the projection). The default (0)
        means write all years.
        'select_areas' is an optional list that lets you select the areas
        that you want to make a PRM table for. E.g. ['00DA', '00MB'] """

        # TODO check the input female/male dictionaries are consistent (same
        # number of age groups, years etc).


        # Decide which areas (discricts) to make the table for
        areas = self.populations_male.keys() # Assume using all areas

        if select_areas != None: # Want to select a few areas in particular
            if len(select_areas)<=0 :
                raise ProjectionError("Size of 'select_areas' list must be > 0")
            elif type(select_areas)!=type([]):
                raise ProjectionError("I was expecting a list of selected areas, not "+str(type(select_areas)))
            # Check that projections are available for all areas
            for a in select_areas:
                if a not in self.populations_male.keys():
                    raise ProjectionError("There is not projection data for area '"+str(a)+"'.")
            # Input areas seem OK
            areas = select_areas

            
        # Work out the maximum number of projected years (pick any random area)
        pop_years = len(self.populations_male[random.choice(list(self.populations_male.keys()))])
        #print "\tThere are",pop_years,"years of projection data"

        # Iterate over all projection years
        years = None
        if year == 0: # Iterate over each year
            years = range(pop_years)
            #years = range(len(self.populations_male))
        else: # Chose just a single year
            years = [year]

        # Write a new file for each year
        for year in years:
            filename = file+"_yr"+str(year)+".csv"
            #print "\tWill write file",filename
            with open(filename, 'w') as f: # (will automatically close file)

                # Header
                f.write(PRMConverter.header+"\n")

                # Make a line for each area (district)
                for area in areas:
                    #print "\tAREA:",area
                    
                    # Get number of people in the area (men,women)
                    num_men = sum(self.populations_male[area][year])
                    num_women = sum(self.populations_female[area][year])
                    #print "\t\tPeople (m,f):", num_men, num_women

                    # Estimate the number of households
                    num_houses = self._estimate_households(area, year)
                    #print "\t\tHouseholds:",num_houses

                    # Group ages into nine groups
                    age_groups_m = PRMConverter._group_ages(self.populations_male[area][year])
                    age_groups_f = PRMConverter._group_ages(self.populations_female[area][year])
                    assert len(age_groups_f)==len(age_groups_m)==9, "M:"+str(age_groups_f)+" F:"+str(age_groups_m)

                    #
                    # Write out the data. For any variables not being used (basically
                    # everything other than age and gender) just write 0.5 as the PRM
                    # will be set to disregard these variables anyway.
                    #
                    #OA, NHH, Npers, detached, semi, terraced, flat, zero_to_nine, Age_10_to_19, Age_20_to_29, Age_30_to_39, Age_40_to_49, Age_50_to_59, Age_60_to_69, Age_70_to_79, Age_80plus, car_none, car_one, car_two_plus, Economically_Active, Economically_Inactive, White, Asian, Black, Other, Good, Fair, Not_good, house_size_1, house_size_2, house_size_3, house_size_4, house_size_5, house_size_6, house_size_7, house_size_8_plus, house_represent_1, house_represent_0, with_LLTI, without_LLTI, SWD, Married, Prof_manag, Intermediate, Non_manual, unemployed, student, no_qualifications, Level_1_2, Level_3_plus, room_1_4, room_5_6, room_7_plus, Males, Females, Owned, Council, Private_rented
                    f.write(area+",") # Area

                    f.write(str(int(round(num_houses*1000)))+", " ) # Num houses (as an int)

                    f.write(str(int(round((num_men+num_women)*1000)))+", ") # Num people (as an int)

                    for i in range(4):  # House type (detached, semi, terraced, flat)
                        f.write(str(0.5)+",")

                    for i in range(9):  # Age groups ( 0-9, 10-19, 20-29, 30-39, 40-4950-59, 60-69, 70-79, 80+
                        age_gps = age_groups_m[i]+age_groups_f[i]
                        f.write(str(age_gps*1000)+",")

                    for i in range(37): # Other un-used variables ( car_none, car_one, car_two_plus, Economically_Active, Economically_Inactive, White, Asian, Black, Other, Good, Fair, Not_good, house_size_1, house_size_2, house_size_3, house_size_4, house_size_5, house_size_6, house_size_7, house_size_8_plus, house_represent_1, house_represent_0, with_LLTI, without_LLTI, SWD, Married, Prof_manag, Intermediate, Non_manual, unemployed, student, no_qualifications, Level_1_2, Level_3_plus, room_1_4, room_5_6, room_7_plus )
                        f.write(str(0.5)+",")

                    f.write(str(num_men*1000)+",") # Num men

                    f.write(str(num_women*1000)+",") # Num women

                    for i in range(3): # House tenure (Owned, Council, Private_rented)
                        f.write(str(0.5)+",")

                    f.write("\n")



# Running the file directly is used for testing.
if __name__ == '__main__':

    # Dictionaries for all areas
    pop_m = {}
    pop_f = {}
    pop_m["00DA"] = []
    pop_f["00DA"] = []
    pop_m["00BH"] = []
    pop_f["00BH"] = []

    # Number of people per age group
    male_pop = [i * 1.1 for i in range(93)]
    female_pop = [i * 1.2 for i in range(93)]

    # Add 30 year projections (growing each year but slightly less for 00BH)
    for i in range(30):
        pop_m["00DA"].append([int(x * (float(i) / 10.0)) for i, x in enumerate(male_pop)])
        pop_f["00DA"].append([int(x * (float(i) / 10.0)) for i, x in enumerate(female_pop)])
        pop_m["00BH"].append([int(x * (float(i) / 15.0)) for i, x in enumerate(male_pop)])
        pop_f["00BH"].append([int(x * (float(i) / 15.0)) for i, x in enumerate(female_pop)])

#    for i in range(30):
#        print "*******************",i,"*******************"
#        print pop_m["00DA"][i]
#        print pop_f["00DA"][i]

    # Test the prm converter

    c = PRMConverter(pop_m, pop_f)
    c.make_prm_table("test_prm", 0)