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

import rpy2.robjects as robjects # for calling R to make population pyramids
from rpy2.robjects.packages import importr # for importing the required r library
import rpy2.rlike.container as rlc # for ordered dictionaries



__author__="nick"
__date__ ="$Jul 6, 2011 8:41:40 AM$"

class PopPyramid():
    def __init__(self, male_popn, female_popn):
        """Takes populations in the form of dictionaries with areas as the keys.
        Each dict entry is a matrix of People objects by year (first dimension)
        and age group (second dimension)"""

        self.male_pop = male_popn
        self.female_pop = female_popn

        assert set(self.male_pop)==set(self.female_pop), "The keys in the female "+\
            "and male populations are different"
        # TODO check input is as expected


    def pop_table(self, file=None, make_negative=False, single_area=None):
        """Print a table of the population in 'population pyramid' form.
        Optional 'file' argument is a string saying where to write the table to
        (rather than printing by default).
        Optional 'make negative' argument says whether or not to make counts of
        males printed as negatives (easier to graph)
        'single_area' says to draw the pyramid for one area (e.g. 00DA). If this
        None then separate pyramids are drawn for all areas. If this is the string
        'NATIONAL' then a single national pyramid is created."""

        # Build up a string for printing or writing
        strl = []

        areas = self.male_pop.keys()
        if single_area != None:
            assert single_area in self.male_pop.keys(), "The given area "+single_area+\
                " is not an area key"
            print "Just producing a population table for area", single_area
            areas = [single_area]

        for area in areas:
            self._append(strl, "Area ", area ,"\n")

            # Do the header
            self._append(strl, "Age,")
            for year in range(len(self.male_pop[area])):
                self._append(strl, "Yr"+str(year)+"Male,", "Yr"+str(year)+"Female,")
            self._append(strl,"\n")

            # Now do the data
            for age in range(len(self.male_pop[area][0])):
                for year in range(len(self.male_pop[area])):
                    male_count= self.male_pop[area][year][age]
                    female_count = self.female_pop[area][year][age]
                    if make_negative:
                        male_count*=-1
                    self._append(strl, age, ",",male_count, ",", female_count)
                self._append(strl, "\n")
            
            self._append(strl, "\n")

        if file is None:
            print ''.join(strl)
        else:
            print "Writing population pyramid data to",file
            with open(file, 'w') as f:
                f.write(''.join(strl))
        
        return

    def pop_graph(self, file, single_area=None, one_year=False):
        """Draws a population pyramid using the pyramid() function in the R
        epicalc library.
        'one_year' true means only print the a pyramid for the final year (this
        can be called repeatedly to draw pyramids while a projection is running,
        rather than having to wait until the end
        'single_area' says to draw the pyramid for one area (e.g. 00DA). If this
        None then separate pyramids are drawn for all areas. If this is the string
        'NATIONAL' then a single national pyramid is created."""

        epicalc = importr('epiDisplay') # Import the epicalc library

        areas = self.male_pop.keys()
        if single_area != None:
            print "Just writing pop pyramids for area", single_area
            assert single_area in self.male_pop.keys() or single_area == "NATIONAL", \
                    "The given area "+str(single_area)+"is not an area key"
            areas = [single_area]                    

        # (Note: 'areas' isn't really used at the moment, it's here to
        # allow multiple areas to be passed in the single_area argument in the future)

        # Might need an area to use as an index into the population dictionaries (this
        # happens when creating a NATIONAL pyramid). Doesn't matter which area is chosen,
        # all areas will have same number of years / age groups. Just has to be a valid key.
        an_area = self.male_pop.keys()[0]

        for area in areas:

            years = [] # The years to draw a pyramid for
            if one_year == True:
                years = [len(self.male_pop[an_area])-1] # Array with just the last year
            else:
                years = [i for i in range(len(self.male_pop[an_area]))] # Array with all available years

            for year in years:
            
                # Make a R data frame to use as input to te pyramid() function
                row_names = ["Age"+str(i) for i in range(len(self.male_pop[an_area][0]))] # Column is age group

                fem_list = [] # lists of num. male/femals for each age
                mal_list = []
                
                if area == "NATIONAL":
                    # Collate all data to make one national pyramid. One element for each age group count
                    mal_list = [0 for age in range(len(self.male_pop[an_area][0]))]
                    fem_list = [0 for age in range(len(self.male_pop[an_area][0]))]
                    for age in range(len(self.male_pop[an_area][0])):
                        for ar in self.male_pop.keys():
                            fem_list[age] += self.female_pop[ar][year][age]
                            mal_list[age] += self.male_pop[ar][year][age]
                    
#                    # Now append list of males/females to 
#                    for age in range(len(self.male_pop[an_area][0])):
#                        fem_list.append(collate_f[age])
#                        mal_list.append(collate_m[age])
                    
                else: # Otherwise just collate all age groups for this area    
                    for age in range(len(self.male_pop[area][0])):
                        fem_list.append(self.female_pop[area][year][age])
                        mal_list.append(self.male_pop[area][year][age])

                # Use the OrdDict constructor to guarantee order of the columns
                od = rlc.OrdDict([
                    ('Male', robjects.FloatVector(mal_list)),
                    ('Female', robjects.FloatVector(fem_list))
                    ])

                dataf = robjects.DataFrame(od)
                dataf.rownames = robjects.StrVector(row_names)
                
                # Prepare the PDF file(s) to write to
                if file[-4:] == ".pdf":
                    file = file[:-4]
                
                filename = file+"_"+area+"_"+str(year)+".pdf"
                print "Will write pyramid to file",filename

                pdf_f = robjects.r('pdf')
                pdf_f(file=filename)

                # TODO For some reason I can't use the dataf object to make the=
                # pyramid (the call to pyramid_f(inputTable=dataf) below fails).
                # So instead have the horrible temporary fix by creating two lists
                # of individual ages and genders (this is also less accurate as I
                # only multiply counts by 100 instead of 1000 to give true num. people)
                age = []
                gender = []
                for a in range(len(self.male_pop[an_area][0])):
                    for b in range(int(self.male_pop[an_area][year][a]*100)):
                        age.append(a)
                        gender.append('M')
                for a in range(len(self.female_pop[an_area][0])):
                    for b in range(int(self.female_pop[an_area][year][a]*100)):
                        age.append(a)
                        gender.append('F')


                # Tell R about the data table
                #robjects.r.assign('dataf',dataf)
                #robjects.r('pyramid(inputTable=dataf)')

                # (This is the line that doesn't work :-( )
                #pyramid_f(inputTable=dataf)

                pyramid_f = robjects.r('pyramid')
                pyramid_f(robjects.IntVector(age), robjects.StrVector(gender))
                

                # Write the pdf
                robjects.r('dev.off')()

                del age
                del gender


    def _append(self,list,*items):
        """Convenience funtion for appending items to a list. All items are
        converted to string objects before being added"""
        for item in items:
            list.append(str(item))