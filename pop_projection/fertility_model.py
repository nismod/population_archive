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


from projection_component import ProjectionComponent
from errors import ProjectionError
from trend import Trend

#import copy


class FertilityModel(ProjectionComponent):
    """Fertility component of a projection model."""

    _debug = False  # Some debugging info for the fertility model
    _debug2 = False # Some more detailed debugging info
    _debug_scaling = False # Details about scaling number of births

    __use_sub_asfr = False # No subnational asfr data, ignore it for now (matrix is populated with 1s)

    __neg_warning_areas = {} # For limitting number of warnings printed

    def __init__(self):
        # Need to remember how births are scaled, index is area key and, for each area,
        # there is a list of tuples with the male/female scale factors used.
        self.scaling_factors = {}
        
        self.trend = Trend() # Object to look for trends in scaling factors(convenience)

    def project(self, *args):
        """Create and return a tuple of male and female babies. Required arguments are:
        1: the subnational female population for the last five years (year by age matrix)
        2: national ASRFs (last five years)
        3: sub-national ASFRs (last five years)
        4: sub-national components of change (male)
        5: sub-national components of change (female)
        6: current projected population who are ready to give birth
        9: area key"""
        
        assert len(args)==7, "FertilityModel expects 7 arguments but I "+ \
                "received "+str(len(args))

        pop_data = args[0]
        asfr_nat = args[1]
        asfr_sub = args[2]
        cc_m = args[3] # Components of change
        cc_f = args[4]
        current_pop = args[5]
        area = args[6]
        
        if len(pop_data)!=5 or len(asfr_nat)!=6 or len(asfr_sub)!=5:
            raise ProjectionError("FertilityModel expects 5years of population "+ \
                "data, 6 years of national ASFRs and 5 years of sub-"\
                "national ASFRs, but I got "+ \
                str(len(pop_data))+","+str(len(asfr_nat))+","+str(len(asfr_sub)) + \
                "\nThe arrays are:"+ \
                "\n"+str(pop_data) + \
                "\n"+str(asfr_nat) + \
                "\n"+str(asfr_sub) )

        # Check the components of change. Should be:
        # StartPop, Births, Deaths, Natural change, Migration, Total change, EndPop
        if cc_m==None and cc_f==None:
            # No components of change data for validation are available,
            # will look for trend in previous scaling factors later
            pass
        else:
            assert len(cc_m)==len(cc_f)==7, "Expected 7 components of change, not "+\
                str(len(cc_m))+" and "+str(len(cc_m))

        if FertilityModel._debug2:
            print "------------------Input to fertility data for area,",area,"---------------------"
            print "Male/female scaling factors (births are index 2):"
            print "\t",str(cc_m),"\n\t",str(cc_f)
            print "Age_group,pop1,pop2,pop3,pop4,pop5,"\
                "asfrnat1,asfrnat2,asfrnat3,asfrnat4,asfrnat5,asfrnat6,"\
                "asfrsub1,asfrsub2,asfrsub3,asfrsub4,asfrsub5"
            for i in range(93): # For each age group
                print i,",",
                for j in range(5):
                    print pop_data[j][i],",",
                for j in range(6):
                    if i < 15 or i > 46: # Fertility rates for selected age only
                        print "-1,",
                    else:
                        print asfr_nat[j][i-15],",",
                for j in range(5):
                    if i < 15 or i > 46: # Fertility rates for selected age only
                        print "-1,",
                    else:
                        print asfr_sub[j][i-15],",",
                print
            print "--------------------- end",area,"------------------\n"

        # See if we need to start storing information about birth scaling (first use)
        if area not in self.scaling_factors:
            self.scaling_factors[area] = [] # New array to store male/female scale factors

        # Calculate fertility differential by age
        # (this doesn't do anything at the moment because no local fertility data)
        fert_diff = []
        num_fert_groups=32 # 93 age groups in total (including 0) but only 32 of them are fertile (15-46 inc)
        for i in range(num_fert_groups): # 93 age groups in total (including 0) but only 32 of them are fertile (15-46 inc)
            asfr_nat_tots = 0 # National and sub-national asfr totals
            asfr_sub_tots = 0
            for j in range(5): # For 5 years
                asfr_nat_tots += asfr_nat[j][i]
                asfr_sub_tots += asfr_sub[j][i]

            if FertilityModel.__use_sub_asfr: # Using local ASFR data
                fert_diff.append( float(asfr_sub_tots) / float(asfr_nat_tots))
            else: # No local asfr data, ignore  (fertility differential will be 1)
                fert_diff.append(1)


        # Now calculate current ASFR for each age group
        asfr = []
        for i in range(num_fert_groups):
            asfr.append(asfr_nat[5][i]*fert_diff[i])

        # Count number of boys and girls produced by each age group 
        girls = [0.0 for i in range(num_fert_groups)]
        boys = [0.0 for i in range(num_fert_groups)]

        # Finally apply these ASFRs to make babies
        for i in range(num_fert_groups): # For each fertile age group
            num_women = current_pop[i+15] # Num women in the fertile age group for the year we're projecting
            num_babies = num_women * (asfr[i]/1000) # Divide ASFR because it should be per 1000 females
            # Work out how many babies are male and how many female (ratio 105 men : 100 women)
            girls[i] = 0.476191 * float(num_babies) # 0.476191 = (105 / 100) / 2
            boys[i] = float(num_babies) - float(girls[i])

        assert sum(boys) > 0 and sum(girls) > 0, "No babies have been born (m/f):" +\
            str(sum(boys))+" / "+str(sum(girls))


        # Now two possibilities for how to scale births:
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
            # fertility, this has to be prevented.
            if scale_m < 0.0:
                scale_m=0.0
                if area not in FertilityModel.__neg_warning_areas: # Limit number of errors printed
                    FertilityModel.__neg_warning_areas[area] = None
                    print "Warning, fertility male scaling factor for area", area, \
                        "has become negative. Setting to 0.", scale_m
            if scale_f < 0.0:
                scale_f=0.0
                if area not in FertilityModel.__neg_warning_areas:
                    FertilityModel.__neg_warning_areas[area] = None
                    print "Warning, fertility female scaling factor for area", area, \
                    "has become negative. Setting to 0.", scale_f
                
            if (FertilityModel._debug_scaling):
                print "Fertility scaling info from previous trend for area",area,":"
                print "\tProjected births (m/f)=",sum(boys),sum(girls)
                print "\tScale: (m/f)=",scale_m,scale_f

        else:
            # Calculate scaling factors so that number babies matches components of change
            scale_m = cc_m[1] / float(sum(boys)) # (Index 2 in cc data is births)
            scale_f = cc_f[1] / float(sum(girls))
            if (FertilityModel._debug_scaling):
                print "Scaling info from components of change for area",area,":"
                print "\tProjected births (m/f)=",sum(boys),sum(girls)
                print "\tExpected births (m/f)=",cc_m[1],cc_f[1]
                print "\tScale: (m/f)=",scale_m,scale_f

        assert scale_m >= 0.0, scale_m
        assert scale_f >= 0.0, scale_f

        # Save the scaling factors to calculate trend for when there are no cc data
        self.scaling_factors[area].append((scale_m,scale_f))

        # Scale births according to the calculated scale factors
        for i in range(num_fert_groups): # For each fertile age group
            girls[i] *= scale_f
            boys[i] *= scale_m

        # Now scale again depending on the scenario we're running
        scenario_scale = ProjectionComponent.scenario[0]
        for i in range(num_fert_groups):
            girls[i] *= scenario_scale
            boys[i] *= scenario_scale


        if FertilityModel._debug:
            print "Have generated male/female babies:", \
                "\n\ttotal scenario:",sum(boys),sum(girls),\
                "\nfrom following fert data:"
            print "FertileAgeGroup, Fertility_Differential, ASFR, NumWomen, NumMaleBabies(scenario), NumFemaleBabies(scenario)"
            for i in range(num_fert_groups):
                print i,",",fert_diff[i],",",asfr[i],",",current_pop[i+15],\
                    ",",boys[i],",",girls[i]

        return (sum(boys), sum(girls))