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

from itertools import izip

from trend import Trend

import rpy2.robjects as robjects # for calling R to make graphs
#from rpy2.robjects.packages import importr # for importing the required r library
import rpy2.rlike.container as rlc # for ordered dictionaries

__author__="Nick Malleson"
__date__ ="$Jul 8, 2011 11:22:41 AM$"


class Residuals():
    def __init__(self, nat_m, nat_f, subnat_m, subnat_f):
        """Initialiser takes the national popualtions (a matrix of year by age)
        and the subnational populations (dictionary of area keys with year/age
        matrices as values)"""

        self.nat_m = nat_m # National popualtion year/age matrices
        self.nat_f = nat_f
        self.subnat_m = subnat_m # Subnational populations (dictionary)
        self.subnat_f = subnat_f

        self.residuals_m = {} # Dictionary of matrices storing residuals for each year and age group
        self.residuals_f = {}

        self.births_m = [] # Total number of births/deaths/migration for each year
        self.births_f = []
        self.deaths_m = []
        self.deaths_f = []
        self.mig_f = []
        self.mig_m = []

        # Check the national matrices have same dimensions
        assert len(nat_m)==len(nat_f)
        for lm, lf in izip(nat_m, nat_f):
            assert len(lm)==len(lf)

        # Check areas are the same
        assert set(subnat_m)==set(subnat_f),\
            "They are keys in the male and female subnational population files that are different."

        # Check that subnational matrices are the same
        for area in subnat_m:
            assert len(subnat_m[area])==len(subnat_f[area])
            for lm, lf in izip(subnat_m[area],subnat_f[area]):
                assert len(lm)==len(lf)

        self.projected_m = {} # Keep a record of the projected populations for
        self.projected_f = {} # analysis at the end of the projection

        self.areas = [] # List of all subnational areas

        # Initialise dictionaries/lists that need to know about area keys
        for area in subnat_m:
            self.areas.append(area)
            self.projected_m[area] = []
            self.projected_f[area] = []
            self.residuals_m[area] = []
            self.residuals_f[area] = []

        self.trend = Trend() # Object to look for trends (convenience)


    def calc_residuals(self, year, new_pop_m, new_pop_f, file=None):
        """Calculate residuals for the newly projected population. Will store
        these results so that overall residuals can be calculate at the end of
        a projection. Therefore this should be called after each year of projection.
        new_pop_m/f are dictionaries of the new male/female projections for the given
        year.
        'file' specifies where to write a table of residuals (if this is None
        then nothing is written)"""

        assert len(new_pop_m)==len(new_pop_f), "Male/female arrays are different lengths: "+\
            str(len(new_pop_m))+"/"+str(len(new_pop_f))
        assert year > 0
        assert set(new_pop_m)==set(new_pop_f),\
            "They are keys in the male and femals subnational population files that are different."


        
        for area in self.areas:
            str = [] # Table of residuals to be written to a file or printed (built as list for efficiency)

            # Calculate subnational residuals (can only do this upto 2033
            # because no subnat expected data past that year
            res_m = []
            res_f = []
            if year >= len(self.subnat_m[area]): # No subnat expected data
                # Look for a trend and add simulated data
                t_m = self.trend.trend2d(self.residuals_m[area])
                t_f = self.trend.trend2d(self.residuals_f[area])
                assert len(t_m)==len(t_f)==len(new_pop_m[area])==len(new_pop_f[area])
                for i in range(len(t_m)):
                    res_m.append(t_m[i])
                    res_f.append(t_f[i])
                    # Test by assuming residuals are 0:
                    #res_m.append(0)
                    #res_f.append(0)
            else:
                for age in range(len(new_pop_m[area])):
                    res_m.append(self.subnat_m[area][year][age]-new_pop_m[area][age])
                    res_f.append(self.subnat_f[area][year][age]-new_pop_f[area][age])
                    
            self.residuals_m[area].append(res_m)
            self.residuals_f[area].append(res_f)

            # Keep a record of the new populations for calculating projection-wide residuals later
            self.projected_m[area].append(new_pop_m[area])
            self.projected_f[area].append(new_pop_f[area])

        # Make a table of residuals for output
        # Header
        self._append(str, "Age,")
        for area in self.areas:
            self._append(str, area,"_M,",area+"_F,")
        self._append(str, "\n")

        for age in range(len(new_pop_m[area])):
            self._append(str, age,",")
            for area in self.areas:
                self._append(str, self.residuals_m[area][-1][age],",",self.residuals_f[area][-1][age],",")
            self._append(str, "\n")

        if file is not None:
            with open(file, 'w') as f:
                print "Writing residuals table for year ",year, "to",file
                f.write(''.join(str))

    def residual_trends(self, area, dir):
        """Make male and femals tables of residuals for the given area and save
        them in the given directory.
        The tables will have rows for each age and columns for years."""

        assert area in self.residuals_f

        assert len(self.residuals_f[area]) == len(self.residuals_m[area])

        # Need to transpose the residuals matrices
        m = []
        f= []
        for year in range(len(self.residuals_f[area][0])):
            list_m = []
            list_f = []
            for val in range(len(self.residuals_f[area])):
                list_m.append(self.residuals_m[area][val][year])
                list_f.append(self.residuals_f[area][val][year])
            m.append(list_m)
            f.append(list_f)

        male_tab = [] # Build up table as array of strings
        female_tab = []

        # Header
        male_tab.append("Age,")
        female_tab.append("Age,")
        for i in range(len(self.residuals_f[area])):
            self._append(male_tab, "Yr", str(i), ",")
            self._append(female_tab, "Yr", str(i), ",")
        male_tab.append("\n")
        female_tab.append("\n")

        # Data
        for age in range(len(m)):
            self._append(male_tab, str(age), ",")
            self._append(female_tab, str(age), ",")
            for year in range(len(m[0])):
                self._append(male_tab, m[age][year], ",")
                self._append(female_tab, f[age][year], ",")
            male_tab.append("\n")
            female_tab.append("\n")

        # Write to csv files
        mf = dir+"/resid_"+area+"m.csv"
        ff = dir+"/resid_"+area+"f.csv"
        with open(mf, 'w') as f:
            print "Writing subnational residuals table for area ",area, "to",file
            f.write(''.join(male_tab))
        with open(ff, 'w') as f:
            print "Writing subnational residuals table for area ",area, "to",file
            f.write(''.join(female_tab))


    def add_cc_data(self, births, deaths, migration):
        self.births_m.append(births[0])
        self.births_f.append(births[1])
        self.deaths_m.append(deaths[0])
        self.deaths_f.append(deaths[1])
        self.mig_m.append(migration[0])
        self.mig_f.append(migration[1])

#        # Also add residuals (migration)
#        tot_resid_m = 0
#        tot_resid_f = 0
#        for area in self.residuals_m:
#            tot_resid_m += sum(self.residuals_m[area][-1])
#            tot_resid_f += sum(self.residuals_f[area][-1])
#        self.mig_m.append(tot_resid_m)
#        self.mig_f.append(tot_resid_f)

    def residual_graph(self, filename, start_year, proj_pop_m, proj_pop_f, nat_pops_m, nat_pops_f):
        """Graph the total difference in size of projected subnation and
        expected national populations.
        proj_pop_m/f are dictionaries of subnational populations for all projected areas and years
        nat_pops_m/f are the national populations of men and women.
        Uses R to build the graph, the R script would look something like this:

        d <- read.csv('Desktop/temp.csv')
        plot(x=Year, y=ExpectedPop, type='o', ylim=c(0,60000), col='blue', lty='dashed')
        points(ProjectedPop, type='o', col='red', lty='dotted')
        points(Residual, type='o', lty='solid')
        legend(x='bottomright',legend=c('Expected','Projected', 'Residual'), 'Total population (thousands of people)', lty=c('dashed', 'dotted', 'solid'), col=c('blue', 'red', 'black'))
        """
        
        # Work out number of projected years by looking at the pop matrix from any area
        tot_years = len(proj_pop_m[self.areas[0]]) # Nearly random area, first area in list of areas
        #tot_years -= 5# TODO  read in more national data so don't need to subtract 5 here.

        projected_pop = [0.0 for i in range(tot_years)] # Population size each year
        expected_pop = [0.0 for i in range(tot_years)] #

        # Count total subnational population for each year (males+females of all ages)
        for year in range(tot_years):
            for area in self.areas:
                for people_m, people_f in izip(proj_pop_m[area][year], proj_pop_f[area][year]):
                    projected_pop[year]+=(people_m+people_f)
            #print "PROJECTED", year, area, projected_pop[year]


        # Count total expected national population for each year
        for year in range(tot_years):
            j=year#+start_year# (index into national data - will start some years before projection starts)
            for people_m, people_f in izip(nat_pops_m[j], nat_pops_f[j]):
                expected_pop[year]+=(people_m+people_f)
            #print "EXPECTED", year, area, expected_pop[year]

        # Calculate residuals
        residuals = [e-p for e,p in izip(expected_pop, projected_pop)]

        # Write residual data and graph
        file = filename+".pdf" # for graph
        datafile = filename+".csv" # for data
        print "Will write residual graph to file",file,"and data to",datafile

        resid_txt = [] # Text for data (csv) file
        resid_txt.append("Year, ExpectedPop, ProjectedPop, Residual\n")
        for year, (e,p,r) in enumerate(izip(expected_pop, projected_pop, residuals)):
            self._append(resid_txt, year,",",e,",",p,",",r,"\n")

        with open(datafile, 'w') as f:
            f.write(''.join(resid_txt))


        # * Graph *
        pdf_f = robjects.r('pdf')
        pdf_f(file=file)

        # Format data as required by R
        yr = robjects.IntVector([i for i in range(len(expected_pop))])
        p = robjects.FloatVector(projected_pop)
        e = robjects.FloatVector(expected_pop)
        r = robjects.FloatVector(residuals)

        yrange=robjects.IntVector([min(expected_pop+projected_pop+residuals),max(expected_pop+projected_pop+residuals)])

        plot_f = robjects.r('plot')
        points_f = robjects.r('points')
        legend_f = robjects.r('legend')

        plot_f(x=yr, y=e, type='o', col='blue', lty='dashed', ylim=yrange, xlab='Year', ylab='Population (*1000 people)' )
        points_f(p, type='o', col='red', lty='dotted')
        points_f(r, type='o', col='black', lty='solid')
        legend_f(x='bottomright',legend=robjects.StrVector(['Expected','Projected', 'Residual']), \
            lty=robjects.StrVector(['dashed', 'dotted', 'solid']), col=robjects.StrVector(['blue', 'red', 'black']))

        # Write the pdf
        robjects.r('dev.off')()



    def cc_tables(self, file, start_year, cc_m, cc_f):
        """Generate graphs of expected and predicted components of change.
        Pass in the expected components of change info and the year that the
        projection started (so that the correct year cc data is used).
        Components of change input data should be a list with an entry for
        each year and then a list with these items for that year:
        StartPop, Births, Deaths, Natural change, Migration, Total change, EndPop
        """

        print "Writing components of change data to",file

        text = [] # Data (table) to write
        text.append("Year,"\
            "BirthMProj,BirthFProj,BirthMExp,BirthFExp,"\
            "DeathMProj,DeathFProj,DeathMExp,DeathFExp,"\
            "MigMProj,MigFProj,MigMExp,MigFExp"\
            "\n")
        for i in range(len(self.births_f)):
            j= i+start_year # (index into cc data)
            self._append(text,i,",",\
                self.births_m[i],",",self.births_f[i],",",cc_m[j][1],",",cc_f[j][1],",",\
                self.deaths_m[i],",",self.deaths_f[i],",",cc_m[j][2],",",cc_f[j][2],",",\
                self.mig_m[i],",",self.mig_f[i],",",cc_m[j][4],",",cc_f[j][4],"\n")

        with open(file,'w') as f:
            f.write(''.join(text))


    def _append(self,list,*items):
        """Convenience funtion for appending items to a list. All items are
        converted to string objects before being added"""
        for item in items:
            list.append(str(item))