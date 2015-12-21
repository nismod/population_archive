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

import copy

class MigrationModel(ProjectionComponent):

    _debug_migration = False

    """Migration component of a projection model"""
    def project(self, *args):
        """Takes in residuals per age group after fertility and mortality
        have been run to guess migration.
        Arguments are touples:
        1. female/male populations that the residuals should be added to
        2. female/male residuals
        3. female/male migration counter (2 element array which should be populated with total migration)
        4. the area under study"""
        
        assert len(args)==4, "Exppected four arguments, not "+str(len(args))
        for i in range(2):
            assert type(args[i])==type((1,1)), "Argument "+str(i)+" should be a tuple."

        assert len(args[2])==2, "Third argument shouold be two-element array"
        mig_counter = args[2]

        popf = args[0][0]
        popm = args[0][1]
        resf = args[1][0]
        resm = args[1][1]

        area = args[3]

        assert len(area)==4 # (e.g. 00DA)

        assert len(popf)==len(popm)==len(resf)==len(resm)

        #Need the copy below if I want to debug
        newpop_f = copy.copy(popf)
        newpop_m = copy.copy(popm)
        #newpop_f = popf
        #newpop_m = popm

        scenario_multiplier = ProjectionComponent.scenario[2]

        for i in range(len(popf)):
            #female_mig = -1*resf[i]
            #male_mig = -1*resm[i]
            female_mig = resf[i]*scenario_multiplier
            male_mig = resm[i]*scenario_multiplier

            #newpop_f[i] = self.migrate(newpop_f[i], female_mig*scenario_multiplier, area)
            #newpop_m[i] = self.migrate(newpop_m[i], male_mig*scenario_multiplier, area)
            newpop_f[i] = self.add_residuals(newpop_f[i], female_mig, area)
            newpop_m[i] = self.add_residuals(newpop_m[i], male_mig, area)


            mig_counter[0]+=female_mig
            mig_counter[1]+=male_mig

        #print sum(newpop_f), sum(newpop_m)

        if MigrationModel._debug_migration:
            print "--------------- Migration/residual info ",\
            area,ProjectionComponent.scenario[3],"Total (f/m):",mig_counter[0],mig_counter[1],"---------------"
            print "Age, resM, resF, beforeM, beforeF, afterM(scenario), afterF(scenario)"
            for i in range(len(popf)):
                print i, resm[i], resf[i], popm[i], popf[i], newpop_m[i], newpop_f[i]

            print " ***TOTALS*** "
            print "resM, resF, beforeM, beforeF, afterM(scenario), afterF(scenario)"
            print sum(resm), sum(resf), sum(popm), sum(popf), sum(newpop_m), sum(newpop_f)
            print "----------------------- END MIGRATION INFO -----------------------"

        
        return (newpop_f, newpop_m)

    __warning_areas = {}

    def add_residuals(self, current_pop, num_to_add, area):
        """Check that adding a negative population wont reduce it below zero"""
        if (current_pop + num_to_add)< 0:
            if area not in MigrationModel.__warning_areas:
                print "Warning, migration is attempting to reduce a population to less than 0 in area", area
                MigrationModel.__warning_areas[area] = None
            return 0.0
        else:
            return current_pop + num_to_add
        
#    def migrate(self, num_people, num_to_migrate, area):
#        """Check that the number of people who want to migrate wont reduce the population to below
#        0 (in this case return a population of 0) and then return num_people-num_to_migrate.
#        Only prints the warning once for the given area"""
#        if (num_people-num_to_migrate )< 0:
#            if area not in MigrationModel.__warning_areas:
#                print "Warning, migration is attempting to reduce a population to less than 0 in area", area
#                MigrationModel.__warning_areas[area] = None
#            return 0.0
#        else:
#            return num_people-num_to_migrate

#  __warning_areas = {}
#    def migrate(self, pop_to_migrate, people_to_mig, scenario_multiplier, area):
#        """Work out how many people to migrate. Use of the scenario multiplier depends
#        on whether people are leaving or moving in. If it is < 1 then increase the
#        number of people leaving and decrease the number of people staying (a 'low'
#        scenario), otherwise do the opposite (a 'high' scenario).
#        Also checks that the final population won't be less than zero, returning 0.0
#        in this case.
#        If the scenario multiplier is None it will just check that the returned population
#        is greater than, but not do any multiplying.
#        """
#
#        num_to_migrate = None
#
#        if scenario_multiplier == None:
#            num_to_migrate = people_to_mig
#
#        elif scenario_multiplier < 1: # 'low scenario' - fewer people in the population
#            if people_to_mig<0: # people leaving - increase this by the multiplier
#                num_to_migrate=people_to_mig*(1-scenario_multiplier)
#            else: # people moving in, decrease this by the multiplier
#                num_to_migrate=people_to_mig*scenario_multiplier
#        else: # 'high' scenario - more people in the population
#            if people_to_mig<0: # people leaving decrease this by the multiplier
#                num_to_migrate=people_to_mig*(scenario_multiplier-1)
#            else: # people moving in, increase this by the multiplier
#                num_to_migrate=people_to_mig*scenario_multiplier
#
#
#        if (num_people-num_to_migrate )< 0:
#            if area not in MigrationModel.__warning_areas:
#                print "Warning, migration is attempting to reduce a population to less than 0 in area", area
#                MigrationModel.__warning_areas[area] = None
#            return 0.0
#        else:
#            return num_people-num_to_migrate