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


from itertools import izip # More efficient zip() function (returns iterator rather than lists)

from projection_component import ProjectionComponent
from trend import Trend

class MortalityModel(ProjectionComponent):
    """Mortality component of a projection model"""

    _debug = False
    _debug_input = False # Display the input to the model for debugging
    _debug_scaling = False

    __use_sub_asmr = False # No subnational asmr data, ignore it for now (matrix is populated with 1s)

    __neg_warning_areas = {} # Limit number of times warning are printed for negative mortality

    def __init__(self):
        self.__nag=93 # number of age groups
        # Need to remember how deaths are scaled, index is area key and, for each area,
        # there is a list of tuples with the male/female scale factors used.
        self.scaling_factors = {}
        
        self.trend = Trend() # For calculating trends in scaling factors

    def project(self, *args):
        """Calculate new populations after mortality. The arguments
        it expects are below.
        In all cases the female arrays are the first element in the tuple.

        1. 5 year previous populations for males and females
        2. 5 year national asmr plus current year (6 years total)
        3. 5 year previous subnational asmr
        4. Male/female subnational components of change for scaling deaths
        5. The input populations who are ready for mortality
        6. Empty two item array which will be populated with female and male deaths
        7. The area code for the given area.
        8. The year of the projection
        """
        
        assert len(args)==8, "MortalityModel expects 8 arguments but I "+ \
            "received "+str(len(args))

        # First five arguments should be tuples of lists (exception is
        # compnents of change which can be a tuple of 'None's
        for i in range(5):
            assert type(args[i])==type((1,1)), "Argument "+str(i)+\
                " should be a tuple, not a "+str(type(args[i]))
            if i!=3:
                assert type(args[i][0])==type(args[i][1])==type([]), "Argument "+\
                    str(i)+" should be two lists, not "+str(type(args[i][0]))+","+str(type(args[i][1]))

        # 6th argument should be a two-element array of zeros (to be populated with death count)
        assert args[5]==[0,0]

        # 7th argument is text (e.g. '00DA')
        assert type(args[6])==type("") and len(args[6])==4, "7th argument should be "\
            "the area key, not "+str(args[6])+" (a "+str(type(args[6]))+")"

        # 8th (last) argument is an integer
        assert type(args[7])==type(1), str(args[7])
        assert args[7] >= 0.0, "Cannot have negative year "+str(args[7])

        # Check that input arguments are as expected (most are 5 years and 93 age groups)
        pop_data_f = MortalityModel.__check_array_lengths(args[0][0], 5, self.__nag, "Pop data - female")
        pop_data_m = MortalityModel.__check_array_lengths(args[0][1], 5, self.__nag, "Pop data - male")
        asmr_nat_f = MortalityModel.__check_array_lengths(args[1][0], 6, self.__nag, "ASMR national - female")
        asmr_nat_m = MortalityModel.__check_array_lengths(args[1][1], 6, self.__nag, "ASMR national - male")
        asmr_sub_f = MortalityModel.__check_array_lengths(args[2][0], 5, self.__nag, "ASMR subnat - female")
        asmr_sub_m = MortalityModel.__check_array_lengths(args[2][1], 5, self.__nag, "ASMR subnat - male")
        cc_f = args[3][0]
        cc_m = args[3][1]
        if cc_f != None and cc_m != None: #(components of change can be None)
            cc_f = MortalityModel.__check_array_lengths(args[3][0], 7, 0, "cc - female")
            cc_m = MortalityModel.__check_array_lengths(args[3][1], 7, 0, "cc - male")
        current_pop_f = MortalityModel.__check_array_lengths(args[4][0], self.__nag, 0, "Current pop - female")
        current_pop_m = MortalityModel.__check_array_lengths(args[4][1], self.__nag, 0, "Current pop - male")
        death_count = args[5]
        area = args[6]
        proj_year = args[7]

        # Check that there are no negatives numbers in the population
        assert True not in (i<0 for i in current_pop_f), str(current_pop_f)
        assert True not in (i<0 for i in current_pop_m), str(current_pop_f)

        # Check the components of change. This should be a list with these components (in order)
        # StartPop, Births, Deaths, Natural change, Migration, Total change, EndPop
        if cc_m==None and cc_f==None:# No components of change data for validation are available
            # No components of change data for validation are available,
            # will look for trend in previous scaling factors later
            pass
        else:
            assert len(cc_m)==len(cc_f)==7, "Expected 7 components of change, not "+\
                str(len(cc_m))+" and "+str(len(cc_m))

            
        if MortalityModel._debug_input:
            print "------------------Input to mortality data for area,",area,"---------------------"
            print "Male/female scaling factors (deaths are index 3):"
            print "\t",str(cc_m),"\n\t",str(cc_f)
            print "AgeGp,F1,M1,F2,M2,F3,M3,F4,M4,F5,M5,",\
                "natrF1,natrM1,natrF2,natrM2,natrF3,natrM3,natrF4,natrM4,natrF5,natrM5,natrF6,natrM6,",\
                "subrF1,subrM1,subrF2,subrM2,subrF3,subrM3,subrF4,subrM4,subrF5,subrM5,",\
                "currentPopM, currentPopf"
            for age in range(self.__nag): # For each age group
                print age,",",
                for year in range(5):
                    print pop_data_f[year][age],",",pop_data_m[year][age],",",
                for year in range(6):
                    print asmr_nat_f[year][age],",",asmr_nat_m[year][age],",",
                for year in range(5):
                    print asmr_sub_f[year][age],",",asmr_sub_m[year][age],",",
                print current_pop_f[age],",",current_pop_m[age]
            print ""

        # See if we need to start storing information about death scaling (first use)
        if area not in self.scaling_factors:
            self.scaling_factors[area] = [] # New array to store male/female scale factors
        
        # Calculate mortality differential by age
        mort_diff_f = self.__calc_mort_diff(asmr_nat_f, asmr_sub_f)
        mort_diff_m = self.__calc_mort_diff(asmr_nat_m, asmr_sub_m)
        assert len(mort_diff_f)==self.__nag and len(mort_diff_m)==self.__nag

        # Now calculate current ASMR for each age group
        asmr_f = []
        asmr_m = []
        for i in range(self.__nag):
            asmr_f.append(asmr_nat_f[5][i]*mort_diff_f[i])
            asmr_m.append(asmr_nat_m[5][i]*mort_diff_m[i])

        # Now we're ready to run the mortality by applying the ASMRs to the population.

        # Start by calculating expected number of deaths (this will be scaled)
        num_female_deaths = self.__calc_deaths(current_pop_f, asmr_f)
        num_male_deaths = self.__calc_deaths(current_pop_m, asmr_m)

        assert True not in [i<0.0 for i in num_female_deaths], str(num_female_deaths)
        assert True not in [i<0.0 for i in num_male_deaths], str(num_male_deaths)

        # Now two possibilities for how to scale deaths:
        # 1. Have subnat cc data (pre 2033) so work out a scaling factor
        # 2. No subnat data (post 2033) so look for trend in previous scaling factors
        scale_m=None
        scale_f=None

        if cc_m==None and cc_f==None: # No cc data, get trend in scaling factors
            # Create a list of separate male and female scaling factors (they're stored together in tuples)
            mfacs = [fac[0] for fac in self.scaling_factors[area] ]
            ffacs = [fac[1] for fac in self.scaling_factors[area] ]
            scale_m = self.trend.trend(mfacs)
            scale_f = self.trend.trend(ffacs)
            
            # Possible that scaling factors are becomming negative which would lead to negative
            # mortality, this has to be prevented.
            if scale_m < 0.0:
                scale_m=0.0
                if area not in MortalityModel.__neg_warning_areas: # Limit number of errors printed
                    MortalityModel.__neg_warning_areas[area] = None
                    print "Warning, mortality male scaling factor for area", area, \
                        "has become negative. Setting to 0.", scale_m
            if scale_f < 0.0:
                scale_f=0.0
                if area not in MortalityModel.__neg_warning_areas:
                    MortalityModel.__neg_warning_areas[area] = None
                    print "Warning, mortality female scaling factor for area", area, \
                        "has become negative. Setting to 0.", scale_f


            if (MortalityModel._debug_scaling):
                print "Scaling mortality info from previous trend for area",area,":"
                print "\tProjected deaths (m/f)=",sum(num_male_deaths),sum(num_female_deaths)
                print "\tScale: (m/f)=",scale_m,scale_f

        
        else: # Have components-of-change data, use this to calculate scaling factors
            expected_deaths_f = cc_f[2]
            expected_deaths_m = cc_m[2]

            # (need to check that expected deaths are not zero, this is possible with small areas)
            assert expected_deaths_f >= 0.0, expected_deaths_f
            assert expected_deaths_m >= 0.0, expected_deaths_m
        
            
            scale_f=sum(num_female_deaths)
            scale_m=sum(num_male_deaths)
            if expected_deaths_f != 0:
                scale_f =  sum(num_female_deaths) / float(expected_deaths_f)
            if expected_deaths_m != 0:
                scale_m =  sum(num_male_deaths) / float(expected_deaths_m)
            
            assert scale_m >= 0.0, ''.join(scale_m, expected_deaths_m, sum(num_male_deaths))
            assert scale_f >= 0.0, ''.join(scale_f, expected_deaths_f, sum(num_female_deaths))

                
            if MortalityModel._debug_scaling:
                print "Mortality scaling info for area",area,":"
                print "\tProjected deaths (m/f)=",sum(num_male_deaths),sum(num_female_deaths)
                print "\tExpected deaths (m/f)=",expected_deaths_m, expected_deaths_f
                print "\tScale: (m/f)=",scale_m,scale_f

        self.scaling_factors[area].append((scale_m,scale_f)) # Save the scaling factors to calculate trend later

        # Calculate total deaths after scaling to the components of change and also
        # using the scenario multiplier (specified by the scenario we're using).
        scen_multiply = ProjectionComponent.scenario[1]**proj_year
        for i in range(len(num_female_deaths)):
            # Scale to components of change:
            num_female_deaths[i]*=scale_f
            num_male_deaths[i]*=scale_m
            # Extra scaling determined by scenario
            num_female_deaths[i]*=scen_multiply
            num_male_deaths[i]*=scen_multiply

            
        # Tell the caller how many people died
        death_count[0] = sum(num_female_deaths)
        death_count[1] = sum(num_male_deaths)


        # Create arrays to store the population to be returned after mortality.
        # Need to return populations for baseline as well as high/low scenarios
        new_pop_f = [0.0 for i in range(len(current_pop_f))]
        new_pop_m = [0.0 for i in range(len(current_pop_f))]

        # Kill people
        for age in range(len(new_pop_f)):
            
            new_pop_f[age] = MortalityModel.remove_people(
                current_pop_f[age], float(num_female_deaths[age]), age, area)
            new_pop_m[age]= MortalityModel.remove_people(
                current_pop_m[age], float(num_male_deaths[age]), age, area)


        # Check the size of the populations have gone down
        assert sum(new_pop_f) <= sum(current_pop_f), str(sum(new_pop_f))+"<="+str(sum(current_pop_f))
        assert sum(new_pop_m) <= sum(current_pop_m), str(sum(new_pop_m))+"<="+str(sum(current_pop_m))
        

        # Check population sizes still make sense
        assert len(new_pop_f) == len(new_pop_m) == len(num_female_deaths) == len(num_male_deaths)

        if MortalityModel._debug:
            print "Have applied mortality to the population with m/f scale factors:",\
                scale_m,scale_f
            print "AgeGroup, MaleDeaths, FemaleDeaths, ASMR_M, ASMR_F, PrevPopPopM, PrevPopPopF, NewPopPopM, PrevPopPopF"
            for age, (m, f, rm, rf, cpm, cpf, npm, npf) in enumerate(izip(\
                    num_female_deaths, num_male_deaths, \
                    asmr_m, asmr_f, \
                    current_pop_m, current_pop_f,\
                    new_pop_f, new_pop_m)):

                print age,",",m,",",f,",",rm,",",rf,",",\
                    cpm,",",cpf,",",\
                    npm,",",npm

        return (new_pop_f, new_pop_m)


    def __calc_mort_diff(self, asmr_nat, asmr_sub):
        """Calculate the mortality differential for each age"""
        mort_diff = []
        for i in range(self.__nag): # For each of the 93 age groups
            asmr_nat_tots = 0 # National and sub-national asfr totals
            asmr_sub_tots = 0
            for j in range(5): # For 5 years
                asmr_nat_tots += asmr_nat[j][i]
                asmr_sub_tots += asmr_sub[j][i]

            if MortalityModel.__use_sub_asmr: # Using local ASFR data
                mort_diff.append( float(asmr_sub_tots) / float(asmr_nat_tots))
            else: # No local asfr data, ignore  (fertility differential will be 1)
                mort_diff.append(1)

        return mort_diff

    def __calc_deaths(self, current_pop, asmr):
        """Calculate the number of deaths for each age group by multiplying
        mortality differentials for each age group by the number of people
        in the age group"""

        assert len(current_pop)==len(asmr)
        deaths=[]
        for pop, rate in izip(current_pop, asmr):
            deaths.append(pop*(rate/100000.0)) # (rate is per 100,000 people)
        return deaths



    @classmethod
    def __check_array_lengths(cls, array, dim1, dim2, description):
        assert len(array)==dim1, "First dimension in data '"+description+\
            "' is length "+str(len(array))+" but should be "+str(dim1)
        if dim2>0: # Might not need to check second dimension if input is a list not a matrix
            for l in array:
                assert len(l)==dim2, "Second dimension in data '"+description+\
                    "' is length "+str(len(l))+" but should be "+str(dim2)
        return array

    @classmethod
    def remove_people(cls, num_people, num_to_remove, age_gp, area):
        """Check that the number of people to be removed doesn't reduce the number
        of people below 0. In this case return 0, otherwise return
        num_people-num_to_remove"""

        assert num_to_remove >= 0.0, "Cannot remove negative people: "+str(num_to_remove)

        if num_people-num_to_remove<0:
            print "Mortality warning - attempt to decrease popualation to less than 0", \
                "for age",age_gp,"in area",area

            return 0
        else:
            return num_people-num_to_remove