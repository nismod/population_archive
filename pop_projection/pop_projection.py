from __future__ import with_statement # for reading files using 'with' statement
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


__author__ = "nick"
__date__ = "$Jun 23, 2011 4:03:49 PM$"

import sys
#import copy
import random
import time
import os

from fertility_model import FertilityModel
from migration_model import MigrationModel
from mortality_model import MortalityModel
from projection_component import ProjectionComponent
from errors import ProjectionError
from pop_pyramid import PopPyramid
from residuals import Residuals
from data_reading import DataReading

from prm_converter import PRMConverter # For writing data in a PRM-format


class PopProjection():
    """Performs a sub-national (regional) population projection based on ONS
    methodology."""

    partial_subnat = False # Use the partial sub-national file (for debugging)

    pop_pyramids = True # Whether or not to print population pyramids at every iteration
    pyramid_area = "NATIONAL" # Area to draw pyramids for (None means do all areas, NATIONAL means do a single national one.)
    prm_output=True # Whether or not to make prm-formatted output data

    decade_summary = True # Whether to print results every decade

    constrain_to_national=False # Whether or not to constrain to national projections

    # Indicate where to look for non-baseline (scenario) data. (Not used as I no
    # longer try to constrain to national projections when running scenarios).
    base_dir = "../data/baseline_data/"
    
    __debug = True
    __debug_age = False # Debug the population ageing process

    __random_seed = 1 # Set to anything other than 1 to have it generated randomly


    # Define the fert, mort and migration multipliers for different scenarios (ratios derived from the ONS national projection documentation)
    # The string arguments give the location of national data to constrain against (if applicable) and a name for the scenario (used when
    # naming results files). I haven't created the constraining data for all the scenarios which is why they use 'baseline' (it only exists
    # for the high and low anyway). Using baseline data doesn't affect model but allows for making graphs comparing scenario to baseline).
    scenarios = { \
        "baseline":[1.0, 1.0, 1.0, "baseline", "baseline"], \
        "high":[1.108696, 0.99, 1.33, "high", "high"], \
        "low":[0.891304, 1.01, 0.67, "low", "low"], \
        "a":[1.15, 0.975, 0.01, "baseline", "a"], \
        "b":[0.95, 0.965, 1.33, "baseline", "b"], \
        "c":[1.15, 0.995, 1.33, "baseline", "c"], \
        "d":[0.95, 0.985, 2.65, "baseline", "d"], \
        "e":[1.05, 1.015, -0.65, "baseline", "e"], \
        "f":[0.85, 1.005, 0.67, "baseline", "f"], \
        "g":[1.05, 1.035, 0.67, "baseline", "g"], \
        "h":[0.85, 1.025, 1.99, "baseline", "h"] \
    }

    # OLD SCENARIOS
#    scenarios = { \
#        "baseline":[1.0, 1.0, 1.0, "baseline", "baseline"], \
#        "high":[1.108696, 0.99, 1.33, "high", "high"], \
#        "low":[0.891304, 1.01, 0.67, "low", "low"], \
#        "a":[0.95, 0.97, 0.01, "baseline", "a"], \
#        "b":[1.15, 0.97, 1.33, "baseline", "b"], \
#        "c":[0.95, 0.99, 1.33, "baseline", "c"], \
#        "d":[1.15, 0.99, 2.65, "baseline", "d"], \
#        "e":[0.85, 1.01, -0.65, "baseline", "e"], \
#        "f":[1.05, 1.005, 0.67, "baseline", "f"], \
#        "g":[1.15, 1.03, 0.67, "baseline", "g"], \
#        "h":[1.05, 1.03, 1.99, "baseline", "h"] \
#    }


    # The main scenario to run (this will be overridden if scenario is set as a command-line argument).
    ProjectionComponent.scenario = scenarios["baseline"]


    def __init__(self, fert, mort, mig):
        self.__fert = fert
        self.__mort = mort
        self.__mig = mig

        self.start_year = 6 # Need to start from sixth year because 5 previous years data required for projection
        self.end_year = 103

        self.populations_male = {} # Lists of projected populations, one for each year (key is subnational area)
        self.populations_female = {} # Lists of projected populations, one for each year (key is subnational area)

        # Also keep populations for a baseline scenario (required to calculate residuals with scenarios)
        self.populations_male_base = {}
        self.populations_female_base = {}

        
        # Some lists to keep track of births/deaths and migration (for info, don't influence sim)

        self.births_m = {}
        self.births_f = {}
        self.deaths_m = {}
        self.deaths_f = {}
        self.mig_m = {}
        self.mig_f = {}

        # Residuals objects (initialised later) maintain lists of residuals and perform analysis
        # Need to maintain one object to store baseline residuals (i.e. the difference between
        # projected and expected subnational populations under base conditions) to esimate migration
        self.base_residuals = None
        self.scenario_residuals = None

        # National level populations. These are for comparing national residuals
        self.__nat_pops_women = [] 
        self.__nat_pops_men = []

        # These national-level popualtions are for the scenario (e.g. high/low). They
        # are used to constrain the projection to national projection numbers
        self.__nat_pops_women_scenario = []
        self.__nat_pops_men_scenario = []

        
        self.__sub_nat_pops_men = {} # Key is area code, value is list of populations (one for each year)
        self.__sub_nat_pops_women = {}

        self.__nat_asfr = [] # National age-specific-fertility-rates (year by age group)
        self.__nat_asmr_m = [] # National age-specific-mortality-rates for men
        self.__nat_asmr_f = [] # Nnational age-specific-mortality-rates for women

        # Sub-national rates (these will all be 1 as we don't have sub-national data)
        self.__subnat_asfr = {} # Subnational age-specific-fertility-rates (age/rate matrix for each area)
        self.__subnat_asmr_m = {} # Subnational age-specific-mortality-rates for men
        self.__subnat_asmr_f = {}# Subnational age-specific-mortality-rates for women

        # National components of change (not broken down by age)
        self.__nat_cc_m = [] # For each year there will be a list with: 
        self.__nat_cc_f = [] # StartPop, Births, Deaths, Natural change, Migration, Total change, EndPop

        # National components of change (not broken down by age). Key is area.
        self.__subnat_cc_m = {} # For each year there will be a list with: ,
        self.__subnat_cc_f = {} # StartPop, Births, Deaths, Natural change, Migration, Total change, EndPop

        # Filenames
        print "Projection is using base data directory",PopProjection.base_dir


        # National projections
        self.male_filename = PopProjection.base_dir+"national/males1.csv"
        self.female_filename = PopProjection.base_dir+"national/females1.csv"

        # Subnational projection and components of change
        self.subnat_file_f = PopProjection.base_dir
        self.subnat_file_m = PopProjection.base_dir
        self.sub_cc_file_f = PopProjection.base_dir
        self.sub_cc_file_m = PopProjection.base_dir
        if PopProjection.partial_subnat:
            self.subnat_file_f += "sub-national/partial_csv/subnational_projection-female.csv"
            self.subnat_file_m += "sub-national/partial_csv/subnational_projection-male.csv"
            self.sub_cc_file_f += "sub-national/partial_csv/subnat_components_of_change_f.csv"
            self.sub_cc_file_m += "sub-national/partial_csv/subnat_components_of_change_m.csv"
        else:
            self.subnat_file_f += "sub-national/full_csv/subnational_projection-female1.csv"
            self.subnat_file_m += "sub-national/full_csv/subnational_projection-male1.csv"
            self.sub_cc_file_f += "sub-national/full_csv/subnat_components_of_change_f1.csv"
            self.sub_cc_file_m += "sub-national/full_csv/subnat_components_of_change_m1.csv"

        # Age-specific fertility/mortality rates (asfr/asmr)
        self.asfr_file = PopProjection.base_dir+"national/fert_rate1.csv"
        self.asmr_file_m = PopProjection.base_dir+"national/mort_males1.csv"
        self.asmr_file_f = PopProjection.base_dir+"national/mort_females1.csv"

        # Components of change (for scaling)
        self.cc_file_m = PopProjection.base_dir+"national/components_of_change_m1.csv"
        self.cc_file_f = PopProjection.base_dir+"national/components_of_change_f1.csv"


        # Setup random number generator
        if PopProjection.__random_seed == 1:
            random.seed(PopProjection.__random_seed)
        else:
            random.seed() # Use current system time as the seed

        # An area lookup for aggregating to regions later
        self.area_lookup = {}
        self.area_lookup_file = PopProjection.base_dir+"sub-national/area_lookup/area_lookup.csv"


    def set_scenario(self, scenario):
        if scenario in PopProjection.scenarios:
            ProjectionComponent.scenario = PopProjection.scenarios[scenario]
            print "Using scenario",scenario
        else:
            print "Unrecognised scenario name:",str(scenario),". Cannot continue"
            exit(0)


        # Check that we're not trying to constrain a scenario to a national
        # projection when there aren't any national data. The ONS have national
        # data for base, high and low, but for any others there is nothing to
        # constrain them to
        if not (ProjectionComponent.scenario[4]=="baseline" or \
           ProjectionComponent.scenario[4]=="high" or\
           ProjectionComponent.scenario[4]=="low") and \
           PopProjection.constrain_to_national==True:

            raise ProjectionError("Trying to constrain to a national projection but "+\
                "the scenario "+str(ProjectionComponent.scenario)+" does not have "+ \
                "any data to constrain to.")



    __age_lookup = ["0-4","5-9","10-14","15-19","20-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64","65-69","70-74","75-79","80-84","85-89","90+"]
    @classmethod
    def group_ages(cls, all_ages):
        """Groups individual ages into 5-year groups up to 90+ (opposite to split_subnat_age)."""
        num_groups = 19
        groups = [0 for i in range(num_groups)]

        for i in range(num_groups): # 19 groups
            if i==18: # Last groups for 90 plus
                groups[i] = all_ages[(i*5)]+all_ages[(i*5)+1]+all_ages[(i*5)+2]
            else:
                for j in range(5):
                    groups[i]+=all_ages[j+(i*5)]

        return groups


    @classmethod
    def same_dimensions(cls, m1, m2):
        """Check the dimensions of the two mattrices are the same. Return
        True if they're the same, false otherwise."""
        if len(m1) != len(m2):
            return False
        else:
            for i in range(len(m1)):
                if len(m1[i]) != len(m2[i]):
                    return False
        return True

    @classmethod
    def check_array_lengths(self, *arrays):
        """Checks the lengths of all the input arrays and returns true if they
        are all the same, false otherwise"""
        if False in [len(arrays[i])==len(arrays[i-1]) for i in range(1,len(arrays))]:
            return False
        else:
            return True

    @classmethod
    def age_population(cls, pop):
        """Age the given popualtion by one year"""
        newpop = []
        eightyniners=None # Remeber the 89 year olds (see comments below)
        for age, num_people in enumerate(pop):

            # Create a new group of people with incremented ages. This is effectively
            # the same population with one less age group (age 0), but with some
            # maths to work out transitions into older age groups.
            #p = People(people=people)
            # Check Special case for age > 88. After age 89 people are grouped into
            # 90-94, 95-100 and 100+ so cannot just increment age. Also, 89 year olds need
            # to be merged with 90-94 group, not just incremented, and this has to be done
            # *after* the 90-94 group has been incremented
            if age < 89:
                #p.increment_age()
                newpop.append(num_people)
            elif age==89:
                eightyniners=num_people # (Note: not adding to newpop, will be integrated to 90-94 group later)
            elif age == 90:
                # Remove 1 in 5 people (who age to next group) and add those who were 89
                newpop.append((num_people*0.8)+eightyniners)
            elif age == 91:
                # Remove 1 in 5 people but also add 1 in 5 from the previous group
                newpop.append((num_people*0.8)+(pop[age-1]*0.2))
                # Add 1 in 5 people from the previous group. No one is removed (oldest group)
            elif age == 92:
                newpop.append(num_people+(pop[age-1]*0.2))
            else:
                raise ProjectionErrpr("Unrecognised age in age_population(): "+str(age))

        # Finally add the 89-year-olds to the 90-94 year group
        #newpop[90].add_to_pop_size(eightyniners.get_num_people())

        # Check the new population is one smaller than previous
        if len(newpop)!=(len(pop)-1):
            raise ProjectionError("Internal error: the population after ageing by "\
                "one year is not one age-group smaller.")

        if PopProjection.__debug_age:
            print "Have aged a population"
            for people in pop:
                print "\t"+str(people)
            print "new pop:"
            for people in newpop:
                print "\t"+str(people)
            print "\n\n"
        return newpop

    @classmethod
    def _append(cls,list,*items):
        """Convenience funtion for appending items to a list. All items are
        converted to string objects before being added"""
        for item in items:
            list.append(str(item))

    def __read_area_lookup(self):
        """Read the list of super and sub reagions for spatial aggregation.
        Also add hypothetical entries for Wales, Scotland and Northern Ireland"""
        
        print "Reading area lookup from",self.area_lookup_file

        with open(self.area_lookup_file, 'r') as f:
            for line in f:
                linesplit = line.strip().split(",")
                big_area = linesplit[0]
                self.area_lookup[big_area] = []
                for small_area in linesplit[1:]:
                    if small_area=="": # Ignore areas with zero size (nothing between commas in file)
                        pass
                    else:
                        self.area_lookup[big_area].append(small_area)
                assert len(self.area_lookup[big_area]) >= 4, "Should be at least four areas for "+ \
                    big_area+": "+str(len(self.area_lookup[big_area]))

        #assert len(self.area_lookup) == 9, "Should be 9 regions in lookup"+str(len(self.area_lookup))

        # Finally add wales, scot, ni. The codes match arbitrary names that I chose
        # when creating the UK subnational file (had to add hypothetical regions for the
        # other three countries)
        self.area_lookup["Wales"] = ["WALE"]
        self.area_lookup["Scotland"] = ["SCOT"]
        self.area_lookup["Northern Ireland"] = ["NIRE"]



    def summary_table(self, file="summary_table.csv", print_sexes=True, aggregate=True):
        """Write a big table showing the male and female population
        for each region over the course of the projection.
        The print_sexes boolean parameter can be used to specify whether
        columns for males and females should be included (True) or just use
        'all persons' without separate gender counts.
        The 'aggregate' parameter determines whether to aggregate from districts
        to government office regions (True) or not (Fasle)"""

        print "Writing summary table",str(file)

        s = "" # Build up the table as text

        # First thing to write are the headers. First header is year (three
        # columns for each year: pop, males, females)
        s+="Region,"
        year_txt = [str(y) for y in range(2004, 2004+self.end_year)] # String years
        for year in year_txt:
            if print_sexes:
                s+=(year+","+year+","+year+",")
            else:
                s+=(year+",")
        s+="\n"

        # Sort the area codes in ascending alphabetical order
        #areas = self.populations_male.keys()
        #areas.sort()

        # Now, for each area, write the populations by age group for each year.
        # Next bit is quite complicated because it aggregates spatially using list comprehensions.
        # The code iterates over each region (e.g. 'North West') and aggregates the number of
        # people for each age in all the districts in the region. Here's an example of the
        # for loop converted to a single comprehension to aggregate ages:
        #
        #sum_ages = [0 for i in range(num_ages)]
        #for area in areas:
        #   for i in range(num_ages):
        #        sum_ages[i]+=self.populations_male[area][yr][i]
        #
        # Or with list comprehension:
        # sum_ages = [sum([self.populations_male[area][yr][i] for area in areas]) for i in range(num_ages)]
        
        regions = None # List of regions to iterate over (could be aggregate gor's or disaggregate
        if aggregate:
            regions = self.area_lookup.keys() # GOR regions
        else:
            regions = self.populations_male.keys() # Normal districts

        num_ages= 93 # Number of age groups

        for i, region in enumerate(regions):

            # List of all areas in this region, required if aggregating to gor
            areas = None
            if aggregate:
                areas = self.area_lookup[region]
            
            # First write the header for the region
            s += (region+",")

            if (i==0): # First pass, also need to write 'pop, male, female' for each year
                for i in range(self.end_year): # Write
                    if print_sexes:
                        s+="Persons,Male,Female,"
                    else:
                        s+="Persons,"
            s+="\n"

            # Need to know how many years of population we have for iterating. Pick any random area, they're all the same.
            pop_years = len(self.populations_male[random.choice(list(self.populations_male.keys()))])

            # Now write the data for each age group - first need to group into 5-yr groups
            grouped_ages_m = []  # ages for each year
            grouped_ages_f = []
            for yr in range(pop_years):
                if aggregate:
                    # Sum number of people in each age group across all areas (see explanation above)
                    sum_ages_m = [sum([self.populations_male[area][yr][i] for area in areas]) for i in range(num_ages)]
                    sum_ages_f = [sum([self.populations_female[area][yr][i] for area in areas]) for i in range(num_ages)]

                    # Now group the ages into 5-year groups
                    grouped_ages_m.append(PopProjection.group_ages(sum_ages_m) )
                    grouped_ages_f.append(PopProjection.group_ages(sum_ages_f) )

                else: # Not aggregating areas
                    grouped_ages_m.append(PopProjection.group_ages(self.populations_male[region][yr])) # (Here region is the district, not gor)
                    grouped_ages_f.append(PopProjection.group_ages(self.populations_female[region][yr]))

            for age in range(len(grouped_ages_m[0])):
                age_str = PopProjection.__age_lookup[age]
                s+=(age_str+",")
                for year in range(len(grouped_ages_m)):
                    males = grouped_ages_m[year][age]
                    females = grouped_ages_f[year][age]

                    if print_sexes:
                        s+= ( str(males+females)+","+str(males)+","+str(females)+"," )
                    else:
                        s+= ( str(males+females)+"," )
                s+="\n"
                
            # And finish with total population, births, deaths, migration (only for projected years)


            s+="Total,"
            for year in range(pop_years):
                # Total people calculated by adding up num people in each age group
                tot_males = sum(grouped_ages_m[year])
                tot_females = sum(grouped_ages_f[year])
                if print_sexes:
                    s+= ( str(tot_males+tot_females)+","+str(tot_males)+","+str(tot_females)+"," )
                else:
                    s+= ( str(tot_males+tot_females)+",")
            s+="\n"

            min = -6 # Special indexes because no birth/death esimates for non-projected years
            #max = len(self.populations_male[area])-6
            max = pop_years-6
            
            s+="Births,"
            for year in range(min,max):
                if year < 0: # No data for pre-projection years
                    if print_sexes:
                        s+="na,na,na,"
                    else:
                        s+="na,"
                else:
                    # Again need to aggregate births across all areas with a list comprehension
                    male_babies = None
                    female_babies = None
                    if aggregate:
                        male_babies = sum([self.births_m[area][year] for area in areas])
                        female_babies = sum([self.births_f[area][year] for area in areas])
                    else:
                        male_babies = self.births_m[region][year]
                        female_babies = self.births_f[region][year]

                    if print_sexes:
                        s+= ( str(male_babies+female_babies)+","+str(male_babies)+","+str(female_babies)+"," )
                    else:
                        s+= ( str(male_babies+female_babies)+",")
            s+="\n"
            
            s+="Deaths,"
            for year in range(min, max):
                if year < 0: # No data for pre-projection years
                    if print_sexes:
                        s+="na,na,na,"
                    else:
                        s+="na,"
                else:
                    male_deaths = None
                    female_deaths = None
                    if aggregate:
                        male_deaths = sum([self.deaths_m[area][year] for area in areas])
                        female_deaths = sum([self.deaths_f[area][year] for area in areas])
                    else:
                        male_deaths = self.deaths_m[region][year]
                        female_deaths= self.deaths_f[region][year]

                    if print_sexes:
                        s+= ( str(male_deaths+female_deaths)+","+str(male_deaths)+","+str(female_deaths)+"," )
                    else:
                        s+= ( str(male_deaths+female_deaths)+"," )
            s+="\n"

            s+="Migration,"
            for year in range(min,max):
                if year < 0: # No data for pre-projection years
                    if print_sexes:
                        s+="na,na,na,"
                    else:
                        s+="na,"
                else:
                    male_migrants = None
                    female_migrants = None
                    if aggregate:
                        male_migrants= sum([self.mig_m[area][year] for area in areas])
                        female_migrants= sum([self.mig_f[area][year] for area in areas])
                    else:
                        male_migrants = self.mig_m[region][year]
                        female_migrants = self.mig_f[region][year]

                    if print_sexes:
                        s+= ( str(male_migrants+female_migrants)+","+str(male_migrants)+","+str(female_migrants)+"," )
                    else:
                        s+= ( str(male_migrants+female_migrants)+"," )

            s+="\n"

        with open(file, 'w') as f:
            f.write(s)

#    def national_table(self, file="national_table.csv"):
#        """Write a table showing some national statistics. These are good for
#        making graphs that compare different scenarios. Years are down the
#        side with some variables (e.g. Births, Deaths, PeoplePerAgeGp)
#        as columns.
#        """
#
#        # Number of years projected
#        pop_years = len(self.populations_male[random.choice(list(self.populations_male.keys()))])
#
#        # Births
#        total_pop = []
#        for yr in range(pop_years):
#            pop = 0
#            for area in self.populations_male.keys():
#                pop += self.populations_male[area][yr]
#                pop += self.populations_female[area][yr]
#
#        # Deaths
#
#        # Migraion
#
#        # Total population
#        total_pop = []
#        for yr in range(pop_years):
#            pop = 0
#            for area in self.populations_male.keys():
#                pop += self.populations_male[area][yr]
#                pop += self.populations_female[area][yr]
#
#
#        # Age groups
#
#        pass




    def run_projection(self):

        # Read the national projections
        DataReading.read_national_projection(self.male_filename, self.__nat_pops_men)
        DataReading.read_national_projection(self.female_filename, self.__nat_pops_women)
        
        # And the projections for the current scenario (the filename will have the
        # scenario name just before the '.csv')
        mf = self.male_filename[:-4]+"_"+ProjectionComponent.scenario[3]+self.male_filename[-4:]
        ff = self.female_filename[:-4]+"_"+ProjectionComponent.scenario[3]+self.female_filename[-4:]
        DataReading.read_national_projection(mf, self.__nat_pops_men_scenario)
        DataReading.read_national_projection(ff, self.__nat_pops_women_scenario)
        del mf, ff
        
        # Read the subnational projections, storing them in dictionaries for males and females
        print "Reading male subnational projections from",self.subnat_file_m
        DataReading.read_subnational_projection(self.subnat_file_m, self.__sub_nat_pops_men)
        print "Reading female subnational projections from",self.subnat_file_f
        DataReading.read_subnational_projection(self.subnat_file_f,self.__sub_nat_pops_women)

        # Check the area keys in the projections are the same
        assert set(self.__sub_nat_pops_men)==set(self.__sub_nat_pops_women),\
            "Error, they are keys in the male and femals subnational"\
                "population files that are different."

        # Read the national and subnational fertility/mortality rates
        DataReading.read_national_fert_mort_rates([ \
            (self.asfr_file, self.__nat_asfr), \
            (self.asmr_file_m, self.__nat_asmr_m), \
            (self.asmr_file_f, self.__nat_asmr_f)])

        # Read the subnational fert/mort rates (no data for this at the moment, just populate a matrix of 1s)
        DataReading.read_subnational_fert_mort_rates(\
            self.__sub_nat_pops_men.keys(),# Area keys are requuired, could come from populations of men or women.. \
            self.__subnat_asfr, \
            self.__subnat_asmr_m, \
            self.__subnat_asmr_f )

        # Read components of change for scaling
        DataReading.read_nat_components_of_change(self.cc_file_m, self.__nat_cc_m)
        DataReading.read_nat_components_of_change(self.cc_file_f, self.__nat_cc_f)

        DataReading.read_subnat_components_of_change(self.sub_cc_file_f, self.__subnat_cc_f, self.end_year)
        DataReading.read_subnat_components_of_change(self.sub_cc_file_m, self.__subnat_cc_m, self.end_year)

        # Check that all subnational area keys match those of the projections
        assert set(self.__sub_nat_pops_men)==set(self.__subnat_cc_f)==set(self.__subnat_cc_m),\
            "Error, they are keys in subnational files that are different."

        # Read the area-lookup for aggregating regions
        self.__read_area_lookup()

        # Create the obejct to monitor residuals - initialise with the expected populations
        self.base_residuals = Residuals(self.__nat_pops_men, self.__nat_pops_women, self.__sub_nat_pops_men, self.__sub_nat_pops_women)
        self.scenario_residuals = Residuals(self.__nat_pops_men, self.__nat_pops_women, self.__sub_nat_pops_men, self.__sub_nat_pops_women)

        # Initialise the population to be projected (starts of same as subnational projection)
        print "Initialising starting population"
        for key in self.__sub_nat_pops_men.keys():
            self.populations_female[key] = []
            self.populations_male[key] = []
            self.populations_male_base[key] = []
            self.populations_female_base[key] = []
            for yr in range(0, self.start_year):
                self.populations_female[key].append(self.__sub_nat_pops_women[key][yr])
                self.populations_male[key].append(self.__sub_nat_pops_men[key][yr])
                self.populations_female_base[key].append(self.__sub_nat_pops_women[key][yr])
                self.populations_male_base[key].append(self.__sub_nat_pops_men[key][yr])

        # Initialise the birth/death/migration counters
        for area in self.populations_male:
            self.births_m[area] = []
            self.births_f[area] = []
            self.deaths_m[area] = []
            self.deaths_f[area] = []
            self.mig_m[area] = []
            self.mig_f[area] = []


        # We need to run a baseline scenario alongside the existing one to calculate
        # residuals for migration. Use this variable to remember which scneario ww're
        # running so we can trick the model into thinking it's running a baseline when
        # infact it's running a different one
        running_scenario = ProjectionComponent.scenario
        print "Running scenario", running_scenario

        # XXXX NEED THE NEXT LINE? Probably not
        #scenario = ProjectionComponent.scenario
        #print "Running scenario", running_scenario

        if PopProjection.constrain_to_national:
            print "Constraining to national projection"
        else:
            print "Not constraining to national projection"

        #print self.populations_female["35UF"],"\n\n"
        #print self.populations_male["35UF"]

        # Start the projection. Note that for each component (fert, mort, mig)
        # we have to calculate components of change for each area and then scale,
        # so can't iterate over each area in one big loop
        # (year is index for arrays, year count is useful for info)
        for year_count, year in enumerate(range(self.start_year, self.end_year-self.start_year)):
            
            print "Projecting year",year_count,"(",year,")"

            start_time = time.time()

            # Need some dictionaries to keep track of the populations as they change
            start_pop_m = {} # The starting population
            start_pop_f = {}
            start_pop_m_base = {} # The starting population
            start_pop_f_base = {}
            aged_pop_m = {} # The population after ageing
            aged_pop_f = {}
            aged_pop_m_base = {} # The population after ageing
            aged_pop_f_base = {}

            fert_pop_m = {} # Population after births
            fert_pop_f = {}
            fert_pop_m_base = {} # (Baseline populations - used for comparing scenarios
            fert_pop_f_base = {} # to the baseline)

            mort_pop_m = {} # Population after mortality
            mort_pop_f = {}
            mort_pop_m_base = {}
            mort_pop_f_base = {}

            mig_pop_m = {} # Population after migration (adding residuals)
            mig_pop_f = {}
            mig_pop_m_base = {} # Population after migration (adding residuals)
            mig_pop_f_base = {}

            # PopPyramid for printing population pyramids later
            p = PopPyramid(self.populations_male, self.populations_female)

            #print "Ageing population"
            for area in self.populations_male:
                #print "\tAging people in ",area
                # The starting populations
                start_pop_m[area] = self.populations_male[area][year-1]
                start_pop_f[area] = self.populations_female[area][year-1]
                start_pop_m_base[area] = self.populations_male_base[area][year-1]
                start_pop_f_base[area] = self.populations_female_base[area][year-1]

                # Check no starting populations are negative
                assert True not in (i<0 for i in start_pop_f[area]), area+" (index "+str(year-1)+") "+str(start_pop_f[area])
                assert True not in (i<0 for i in start_pop_m[area]), area+" (index "+str(year-1)+") "+str(start_pop_m[area])
                assert True not in (i<0 for i in start_pop_f_base[area]), area+" (index "+str(year-1)+") "+str(start_pop_f_base[area])
                assert True not in (i<0 for i in start_pop_m_base[area]), area+" (index "+str(year-1)+") "+str(start_pop_m_base[area])



                # Age the population by incrementing pop from previous year
                aged_pop_m[area] = PopProjection.age_population(start_pop_m[area])
                aged_pop_f[area] = PopProjection.age_population(start_pop_f[area])
                aged_pop_m_base[area] = PopProjection.age_population(start_pop_m_base[area])
                aged_pop_f_base[area] = PopProjection.age_population(start_pop_f_base[area])

                # Size of population after ageing should not change
                assert round(sum(start_pop_f[area]),5)==round(sum(aged_pop_f[area]),5) \
                    and round(sum(start_pop_m[area]),5)==round(sum(aged_pop_m[area]),5), \
                    "Population size should be the same after aging "+str([sum(start_pop_f[area]), \
                    sum(aged_pop_f[area]), sum(start_pop_m[area]), sum(aged_pop_m[area]) ])
                    
                # Also check that there are no negatives numbers in the population
                assert True not in (i<0 for i in aged_pop_f[area]), area+","+str(aged_pop_f[area])
                assert True not in (i<0 for i in aged_pop_m[area]), area+","+str(aged_pop_m[area])
                assert True not in (i<0 for i in aged_pop_f_base[area]), area+","+str(aged_pop_f_base[area])
                assert True not in (i<0 for i in aged_pop_m_base[area]), area+","+str(aged_pop_m_base[area])



            # Use the fertility model to work out how many male/female babies are born
            # under baseline and scenario conditions
            tot_babies_m = 0
            tot_babies_f = 0
            for area in self.populations_male:
                babies = self.__fert.project(
                    self.populations_female[area][year-6:year-1], # 5 year previous female pop
                    self.__nat_asfr[year-6:year], # 5 year national asfr plus current year
                    self.__subnat_asfr[area][year-6:year-1], # 5 year previous subnational
                    self.__subnat_cc_m[area][year], # Male/female components of change for scaling births
                    self.__subnat_cc_f[area][year],
                    aged_pop_f[area], # Population who have been aged and are ready to give birth
                    area # Sot the fert model knows the name of the area
                    )
                # Now run a baseline too
                ProjectionComponent.scenario = PopProjection.scenarios["baseline"]
                base_babies = self.__fert.project(
                    self.populations_female_base[area][year-6:year-1], # 5 year previous female pop
                    self.__nat_asfr[year-6:year], # 5 year national asfr plus current year
                    self.__subnat_asfr[area][year-6:year-1], # 5 year previous subnational
                    self.__subnat_cc_m[area][year], # Male/female components of change for scaling births
                    self.__subnat_cc_f[area][year],
                    aged_pop_f_base[area], # Population who have been aged and are ready to give birth
                    area # Sot the fert model knows the name of the area
                    )
                # Revert back to scenario we're really running
                ProjectionComponent.scenario = running_scenario
                    
                # Add babies to population
                fert_pop_m[area] = aged_pop_m[area]
                fert_pop_f[area] = aged_pop_f[area]
                fert_pop_m[area].insert(0,babies[0]) # Insert male babies
                fert_pop_f[area].insert(0,babies[1]) # Insert female babies

                fert_pop_m_base[area] = aged_pop_m_base[area]
                fert_pop_f_base[area] = aged_pop_f_base[area]
                fert_pop_m_base[area].insert(0,base_babies[0]) # Insert male babies from baseline scenario
                fert_pop_f_base[area].insert(0,base_babies[1]) # Insert female babies from baseline scenario

                # Now that babies have been added the population list should be same size as before
                assert PopProjection.check_array_lengths(\
                    start_pop_f[area],fert_pop_f[area], start_pop_m[area], fert_pop_m[area]) , \
                    "Arrays are not same length:"+\
                    str(len(start_pop_f[area]))+","+str(len(fert_pop_f[area]))+","+ \
                    str(len(start_pop_m[area]))+","+str(len(fert_pop_m[area]))

                # Check no populations are negative
                assert True not in (i<0.0 for i in fert_pop_f[area]), area+" (index "+str(year-1)+") "+str(fert_pop_f[area])
                assert True not in (i<0.0 for i in fert_pop_m[area]), area+" (index "+str(year-1)+") "+str(fert_pop_m[area])
                assert True not in (i<0.0 for i in fert_pop_f_base[area]), area+" (index "+str(year-1)+") "+str(fert_pop_f_base[area])
                assert True not in (i<0.0 for i in fert_pop_m_base[area]), area+" (index "+str(year-1)+") "+str(fert_pop_m_base[area])


                # Also check that there are more people in the population after fertility
                 # Check that there are fewer people in the population after mortality
                assert sum(fert_pop_f[area])>=sum(aged_pop_f[area]), \
                    "Area "+area+":"+''.join([str(sum(fert_pop_f[area])),str(sum(aged_pop_f[area]))])
                assert sum(fert_pop_f_base[area])>=sum(aged_pop_f_base[area]), \
                    "Area "+area+":"+''.join([str(sum(fert_pop_f_base[area])),str(sum(aged_pop_f_base[area]))])
                assert sum(fert_pop_m[area])>=sum(aged_pop_m[area]), \
                    "Area "+area+":"+''.join([str(sum(fert_pop_m[area])),str(sum(aged_pop_m[area]))])
                assert sum(fert_pop_m_base[area])>=sum(aged_pop_m_base[area]) , \
                    "Area "+area+":"+''.join([str(sum(fert_pop_m[area])),str(sum(aged_pop_m_base[area]))])
                # Store number of births for info
                self.births_m[area].append(babies[0])
                self.births_f[area].append(babies[1])
                tot_babies_m+=babies[0]
                tot_babies_f+=babies[1]

            
            if FertilityModel._debug:
                print "Babies after fertility and scaling:"
                print "Area, Start females, start males, end females, end males"

            for area in self.populations_male:
                if FertilityModel._debug:
                    print area, ",", start_pop_f[area][0],",",start_pop_m[area][0],",",\
                        fert_pop_f[area][0],",",fert_pop_m[area][0]

            # Kill people (mortality)
            tot_deaths_m = 0 # Total deaths for all areas
            tot_deaths_f = 0
            for area in self.populations_male:
                num_deaths = [0,0] # Num deaths for this area (female/male)
                new_populations = self.__mort.project(
                    (self.populations_female[area][year-6:year-1], self.populations_male[area][year-6:year-1]),# 5 year previous pops
                    (self.__nat_asmr_f[year-6:year], self.__nat_asmr_m[year-6:year]),# 5 year national asmr plus current year
                    (self.__subnat_asmr_f[area][year-6:year-1], self.__subnat_asmr_m[area][year-6:year-1]), # 5 year previous subnational
                    (self.__subnat_cc_f[area][year],self.__subnat_cc_m[area][year]), # Male/female components of change for scaling deaths
                    (fert_pop_f[area], fert_pop_m[area]), # Population who are ready for mortality
                    num_deaths,
                    area,
                    year)
                # Now run a baseline too
                ProjectionComponent.scenario = PopProjection.scenarios["baseline"]
                num_deaths_base = [0,0] # (Not actually used but don't want to overide the other counter)
                new_populations_base = self.__mort.project(
                    (self.populations_female_base[area][year-6:year-1], self.populations_male_base[area][year-6:year-1]),# 5 year previous pops
                    (self.__nat_asmr_f[year-6:year], self.__nat_asmr_m[year-6:year]),# 5 year national asmr plus current year
                    (self.__subnat_asmr_f[area][year-6:year-1], self.__subnat_asmr_m[area][year-6:year-1]), # 5 year previous subnational
                    (self.__subnat_cc_f[area][year],self.__subnat_cc_m[area][year]), # Male/female components of change for scaling deaths
                    (fert_pop_f_base[area], fert_pop_m_base[area]), # Population who are ready for mortality
                    num_deaths_base,
                    area,
                    year)
                # Revert back to scenario we're really running
                ProjectionComponent.scenario = running_scenario

                mort_pop_f[area] = new_populations[0]
                mort_pop_m[area] = new_populations[1]
                mort_pop_f_base[area] = new_populations_base[0]
                mort_pop_m_base[area] = new_populations_base[1]

                assert len(new_populations) == 2 and \
                    len(mort_pop_f[area])==len(fert_pop_f[area]) == \
                    len(mort_pop_m[area])==len(fert_pop_m[area])== \
                    len(mort_pop_f_base[area])==len(mort_pop_m_base[area])

                # Check that there are no negatives
                assert True not in (i<0 for i in mort_pop_f[area]), area+" (index "+str(year-1)+") "+str(mort_pop_f[area])
                assert True not in (i<0 for i in mort_pop_m[area]), area+" (index "+str(year-1)+") "+str(mort_pop_m[area])
                assert True not in (i<0 for i in mort_pop_f_base[area]), area+" (index "+str(year-1)+") "+str(mort_pop_f_base[area])
                assert True not in (i<0 for i in mort_pop_m_base[area]), area+" (index "+str(year-1)+") "+str(mort_pop_m_base[area])

                # Check that number of deaths makes sense
                assert num_deaths[0] >= 0.0, "Negative number female deaths "+str(num_deaths[0])
                assert num_deaths[1] >= 0.0, "Negative number male deaths "+str(num_deaths[1])
                assert num_deaths_base[0] >= 0.0, "Negative number female deaths "+str(num_deaths_base[0])
                assert num_deaths_base[1] >= 0.0, "Negative number male deaths "+str(num_deaths_base[1])

                # Check that there are fewer people in the population after mortality
                assert sum(mort_pop_f[area])<=sum(fert_pop_f[area]), "Area "+area+": "+\
                    str(sum(mort_pop_f[area]))+"<="+str(sum(fert_pop_f[area]))

                assert sum(mort_pop_m[area])<=sum(fert_pop_m[area]),"Area "+area+": "+\
                    str(sum(mort_pop_m[area]))+"<="+str(sum(fert_pop_m[area]))

                # Store number of deaths for info
                male_deaths = num_deaths[1]
                female_deaths = num_deaths[0]
                self.deaths_m[area].append(male_deaths)
                self.deaths_f[area].append(female_deaths)
                tot_deaths_m+=male_deaths
                tot_deaths_f+=female_deaths

            # FOR DEBUGGING PRINT THE CURRENT POPULATION AND THE EXPECTED ONE
#            for area in ["00DA"]:
#                print "AGE, CURRENT(M), EXPECTED(M)",area
#                for age in range(93):
#                    print age,",",mort_pop_m[area][age],",",self.__sub_nat_pops_men[area][year][age]



            # Calculate the scenario residuals for all areas this year, required for graphs etc
            # This is the difference between the projection and the baseline ONS data (or 'high'/'low'
            # data if running these particular scenarios).
            self.scenario_residuals.calc_residuals(year, mort_pop_m,mort_pop_f, file=None)

            # Calculte base residuals as well (these are needed for migration). This is the difference
            # between the base projection and baseline ONS data
            self.base_residuals.calc_residuals(year, mort_pop_m_base,mort_pop_f_base, file=None)

            nat_mig_counter_f = 0 # Total migration nationally (for printing cc tables)
            nat_mig_counter_m = 0
            
            # Residuals object is traking subnational residuals per age group, assume these are
            # migration and add them to each area. Note that *base* residuals are used because
            # there is no subnational scenario data - therefore when using scenarios the projected
            # population will be larger/smaller than expected so residuals will change as well
            # and migration will be affected.
            # NOTE: after 2033 these will be simulated by Residuals
            for area in self.populations_male:
                mig_counter = [0.0, 0.0]   # Count total migration (male/female)
                new_populations = self.__mig.project(
                    (mort_pop_f[area], mort_pop_m[area]), # The population to add residuals to
                    (self.base_residuals.residuals_f[area][year-self.start_year],self.base_residuals.residuals_m[area][year-self.start_year]),
                    mig_counter,
                    area
                )
                # Now run a baseline too
                ProjectionComponent.scenario = PopProjection.scenarios["baseline"]
                mig_counter_base = [0.0, 0.0]
                new_populations_base = self.__mig.project(
                    (mort_pop_f_base[area], mort_pop_m_base[area]),
                    (self.base_residuals.residuals_f[area][year-self.start_year],self.base_residuals.residuals_m[area][year-self.start_year]),
                    mig_counter_base,
                    area
                )
                # Revert back to scenario we're really running
                ProjectionComponent.scenario = running_scenario

                mig_pop_f[area] = new_populations[0]
                mig_pop_m[area] = new_populations[1]
                mig_pop_f_base[area] = new_populations_base[0]
                mig_pop_m_base[area] = new_populations_base[1]


                assert len(new_populations) == 2 and \
                    len(mig_pop_f[area])==len(fert_pop_f[area]) == \
                    len(mig_pop_m[area])==len(fert_pop_m[area])

                # Check migration hasn't reduced the population to below 0
                assert True not in (i<0 for i in mig_pop_f[area]), area+" (index "+str(year-1)+") "+str(mig_pop_f[area])
                assert True not in (i<0 for i in mig_pop_m[area]), area+" (index "+str(year-1)+") "+str(mig_pop_m[area])
                assert True not in (i<0 for i in mig_pop_f_base[area]), area+" (index "+str(year-1)+") "+str(mig_pop_f_base[area])
                assert True not in (i<0 for i in mig_pop_m_base[area]), area+" (index "+str(year-1)+") "+str(mig_pop_m_base[area])

                # Keep a record of migration
                self.mig_f[area].append(mig_counter[0])
                self.mig_m[area].append(mig_counter[1])
                nat_mig_counter_f += mig_counter[0] # Increment national migration for cc tables.
                nat_mig_counter_m += mig_counter[1]


            # Count the expected and projected populations so that the projections can
            # be scaled (constrained to national projections).

            projected_pop = 0.0
            expected_pop = 0.0

            # Count total subnational population for each year (males+females of all ages)

            for area in self.populations_male:
                for people_m, people_f in zip(mig_pop_m[area], mig_pop_f[area]):
                    projected_pop+=(people_m+people_f)
            #print "PROJECTED A", year, projected_pop


            # Count total expected national population for each year
            j=year# (index into national data - will start some years before projection starts)
            for people_m, people_f in zip(self.__nat_pops_men_scenario[j], self.__nat_pops_women_scenario[j]):
                expected_pop+=(people_m+people_f)
            #print "EXPECTED A", year, expected_pop
            
            # Scale sub-national populations to national projections (effectively constraining them)
            # NOTE: for some reason I didn't used to do this post 2033 (hence the commented 'if'
            # statement below). Can't see any reason not to though
            #if year < self.start_year+24:

            if PopProjection.constrain_to_national:
                scale = expected_pop / projected_pop
                print "Scaling to national projection"
                print "\t",expected_pop , projected_pop, scale
                for ar in self.populations_male:
                    for age in range(len(mig_pop_m[ar])):
                        mig_pop_m[ar][age]*=scale
                        mig_pop_f[ar][age]*=scale

            # TODO Need to go over births/deaths etc and scale as well?

            # Add new population to array
            for ar in self.populations_male:
                self.populations_male[ar].append(mig_pop_m[ar])
                self.populations_female[ar].append(mig_pop_f[ar])
                self.populations_male_base[ar].append(mig_pop_m_base[ar])
                self.populations_female_base[ar].append(mig_pop_f_base[ar])


            # Add some components of change data for printing later
            self.scenario_residuals.add_cc_data(\
                (tot_babies_m,tot_babies_f), \
                (tot_deaths_m, tot_deaths_f),
                (nat_mig_counter_m, nat_mig_counter_f)\
                )

            a = "00DA"
            dir= "../../results/"+ProjectionComponent.scenario[4]+"/"
            prm_dir = dir+"prm/" # Directory for PRM-formatted tables
            pyramid_dir=dir # (No new dir if not printing them every iteration)
            try:
                os.makedirs(dir)
                print "Created new directory for results: ",dir
            except OSError:
                pass
            if PopProjection.prm_output:
                try:
                    os.makedirs(prm_dir)
                    print "Created new directory for results: ",prm_dir
                except OSError:
                    pass
            if PopProjection.pop_pyramids: 
                pyramid_dir = dir+"pyramids/"
                try:
                    os.makedirs(pyramid_dir)
                    print "Created new directory for pop pyramids:",pyramid_dir
                except OSError:
                    pass

            # Graph residuals for Leeds
            #self.scenario_residuals.residual_graph("/Users/nick/Desktop/graphs/", start_year, self.populations_male, self.populations_female, self.__sub_nat_pops_men[a], self.__sub_nat_pops_women[a])

            # Make a pop pryamid for this year
            if PopProjection.pop_pyramids:
                p.pop_graph((pyramid_dir+"pp.pdf"), single_area=PopProjection.pyramid_area, one_year=True)

            # Write a table that the PRM can use for projections. Note that 'year_count' is
            # used rather than 'year' because the prm file uses household data that are only
            # from 2008-2083 (not 2004 onwards)
            if PopProjection.prm_output:
                print "Writing PRM file"
                prm = PRMConverter(self.populations_male, self.populations_female, self.populations_male_base, self.populations_female_base)
                prm_filename = prm_dir+"prm_data"
                prm.make_prm_table(prm_filename, year_count, select_areas=None)
                #prm.make_prm_table(prm_filename, year_count, select_areas=[a]) # Just Leeds (or whatever 'a' is above)

            # Occasionally write some info/results
            if (PopProjection.decade_summary and year%10==0):
                # Make national residual graphs from data so far.
                # Do one for residuals compared to baseline data..
                self.scenario_residuals.residual_graph((dir+"total_residuals"), self.start_year, self.populations_male, self.populations_female, self.__nat_pops_men, self.__nat_pops_women)
                # ..and another for comparing the projection to scenario data (there are only ONS scenario
                # data available for the 'high', 'low' and 'baseline' projections.
                # (These residuals will be 0 if constraining to the national population).
                if ProjectionComponent.scenario[4]=="baseline" or ProjectionComponent.scenario[4]=="high" or ProjectionComponent.scenario[4]=="low":
                    self.scenario_residuals.residual_graph((dir+"scenario_residuals"), self.start_year, self.populations_male, self.populations_female, self.__nat_pops_men_scenario, self.__nat_pops_women_scenario)

                # Write a summary table 
                self.summary_table(file=dir+"summary_table_"+ProjectionComponent.scenario[4]+"_persons"+str(year)+".csv", print_sexes=False)
                self.summary_table(file=dir+"summary_table_"+ProjectionComponent.scenario[4]+"_disaggregate"+str(year)+".csv", print_sexes=True, aggregate=False)

                # Make some graphs of components of change
                self.scenario_residuals.cc_tables((dir+"cc.csv"), self.start_year, self.__nat_cc_m, self.__nat_cc_f)


            # Free some memory now the old populations aren't required (I don't think
            # this actually helps to free memory)
            del start_pop_m, start_pop_f, aged_pop_m, aged_pop_f, fert_pop_f, fert_pop_m, \
                mort_pop_f, mort_pop_m, mig_pop_m, mig_pop_f

            print "\tFinished year", year, "in","%.2f" % ((time.time()-start_time)),"sec"

        # Finished the projection.
        print "Finished projection, creating results"

        # Make a table of residuals (and subsequent predicted trends) for each age group
        self.scenario_residuals.residual_trends(a, dir)
            
        # Make some graphs of components of change
        self.scenario_residuals.cc_tables((dir+"cc.csv"), self.start_year, self.__nat_cc_m, self.__nat_cc_f)

        # Make a graph of national residuals (difference between projected populations and ONS baseline data)
        self.scenario_residuals.residual_graph((dir+"total_residuals"), self.start_year, self.populations_male, self.populations_female, self.__nat_pops_men, self.__nat_pops_women)

        # Scenario residuals are the difference between the projected population and expected scenario populations.
        # Only relevant to baseline, high, low scenarios (no ONS data for other scenarios).
        # When constraining to the national projection these will be 0.
        if ProjectionComponent.scenario[4]=="baseline" or ProjectionComponent.scenario[4]=="high" or ProjectionComponent.scenario[4]=="low":
            self.scenario_residuals.residual_graph((dir+"scenario_residuals"), self.start_year, self.populations_male, self.populations_female, self.__nat_pops_men_scenario, self.__nat_pops_women_scenario)


        # Look at how the scaling factors were changing in a given area (print a csv table)
        scale_text=[]
        scale_text.append("Year, MaleBirthScale, FemaleBirthScale,MaleDeathScale, FemaleDeathScale\n")
        for i in range(year-self.start_year):
            PopProjection._append(scale_text, i,",",self.__fert.scaling_factors[a][i][0],",",\
                self.__fert.scaling_factors[a][i][1],",",self.__mort.scaling_factors[a][i][0],\
                ",",self.__mort.scaling_factors[a][i][1],"\n")
        with open(dir+"scaling_"+a+".csv",'w') as f:
            f.write(''.join(scale_text))

        # Make a population pyramid table and graph (pyramids might also have been created earlier)
        # TODO: pop_table wont work - needs updating to include option
        # for NATIONAL single_area
        #p.pop_table(file=(dir+"pop_pyramid_table.csv"), single_area=PopProjection.pyramid_area)

        # Mark a pyramid for the last year, regardless of whether or not they've been made every year
        p.pop_graph((dir+"pp.pdf"), single_area=PopProjection.pyramid_area, one_year=True)

        # Make big summary tables (one with Male/Female columns, one with just with total person counts and a disaggregate one)
        self.summary_table(file=dir+"summary_table_"+ProjectionComponent.scenario[4]+".csv")
        self.summary_table(file=dir+"summary_table_"+ProjectionComponent.scenario[4]+"_persons.csv", print_sexes=False)
        self.summary_table(file=dir+"summary_table_"+ProjectionComponent.scenario[4]+"_disaggregate.csv", print_sexes=True, aggregate=False)

#        # Also make a table of national data, (births, deaths, agegroups etc) with years down the side
#        self.national_table(file=dir+"national_table_"+ProjectionComponent.scenario[4]+".csv")

        print "Finished"



if __name__ == '__main__':
    fert = FertilityModel()
    mort = MortalityModel()
    mig = MigrationModel()

    # Can optionally set the scenario as a command line argument (otherwise
    # it is hard coded in the PopProjection class).
    scenario = "a"
    if len(sys.argv)==2:
        scenario=sys.argv[1]
        print "Running scenario:",scenario
    else:
        print "Will use the hard-coded scenario"

    p = PopProjection(fert, mort, mig)
    if scenario != None:
        p.set_scenario(scenario)
        
    p.run_projection()