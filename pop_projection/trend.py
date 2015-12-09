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


# Convenience class to look for trensds in data. Uses R.

import rpy2.robjects as robjects # for calling R to make graphs

from math import sqrt

__author__="nick"
__date__ ="$Jul 21, 2011 11:46:25 AM$"

class Trend:

    _print_trend = False
    

    def __init__(self):
        self.R = robjects.r
        pass


    def trend2d(self, matrix):
        """Take a 2D matrix and return the next predicted value for each of the rows.
        (Calls the 1D function for each row 'trend()')"""

         # Need to transpose the matrix
        to_return = []
        for year in range(len(matrix[0])):
            list = []
            for val in range(len(matrix)):
                list.append(matrix[val][year])
            to_return.append(list)

        return [self.trend(row) for row in to_return]


    def trend(self, list):
        """Use regression to estimate a trend in the data"""

        # Possible that the list contains just zeros, this would cause a
        # ZeroDivisionError
        if False not in (val==0.0 for val in list):
            return 0.0

        # Create data to pass to R
        xvals = [i for i in range(len(list))] # data for the x axis (year)
        reg = self.linreg(xvals, list)

        grad = reg[0] # Gradient
        inter = reg[1] # Intercept

        if Trend._print_trend:
            print "---------- Printing trend and 20 more values ------------"
            for val in list:
                print val
            print ".. "
            for i in range(20):
                print inter+ grad*(len(list)+i)
            print "---------- End Trend ------------"

        return inter+ grad*(len(list))


    # DEPRICATED FUNCTION: Uses R lm() function which is too slow,
    # replaced with bespoke function
    def trendR(self, list):
        """Use regression (lm function in R) to estimate a trend in the data"""

        # Create data to pass to R
        xaxis = robjects.IntVector([i for i in range(len(list))]) # data for the x axis (yearr)
        yaxis = robjects.FloatVector(list)

        # Send it to R
        self.R.assign('x',xaxis)
        self.R.assign('y',yaxis)

        #lm_f = robjects.r('lm') # the lm R function
        #fit = lm_f(formula='y~x')
        self.R('model <- lm(y~x)')

        # Get the coefficient and intercept to calculate the next value in the series
        # This is a bit messy but works, uses a combination of info from two places:
        # http://www.cyclismo.org/tutorial/R/linearLeastSquares.html
        # http://scienceoss.com/rpy-statistics-in-r-from-python/

        if Trend._print_trend:
            print "---------- Printing trend and 20 more values ------------"
            for val in list:
                print val
            print ".. "
            for i in range(20):
                print intercept + gradient*(len(list)+i)
            print "---------- End Trend ------------"


        gradient = self.R("model$coefficients[[2]]")[0]
        intercept = self.R("model$coefficients[[1]]")[0]
        
        next_val = intercept + gradient*(len(list))

        return next_val



    # Function to do linear regression, copied verbatim from
    # http://www.answermysearches.com/how-to-do-a-simple-linear-regression-in-python/124/
    def linreg(self, X, Y):
        """
        Summary
            Linear regression of y = ax + b
        Usage
            real, real, real = linreg(list, list)
        Returns coefficients to the regression line "y=ax+b" from x[] and y[], and R^2 Value
        """
        if len(X) != len(Y):  raise ValueError, 'unequal length'
        N = len(X)
        Sx = Sy = Sxx = Syy = Sxy = 0.0
        for x, y in map(None, X, Y):
            Sx = Sx + x
            Sy = Sy + y
            Sxx = Sxx + x*x
            Syy = Syy + y*y
            Sxy = Sxy + x*y
        det = Sxx * N - Sx * Sx
        a, b = (Sxy * N - Sy * Sx)/det, (Sxx * Sy - Sx * Sxy)/det
        meanerror = residual = 0.0
        for x, y in map(None, X, Y):
            meanerror = meanerror + (y - Sy/N)**2
            residual = residual + (y - a * x - b)**2
        RR = 1 - residual/meanerror
        ss = residual / (N-2)
        Var_a, Var_b = ss * N / det, ss * Sxx / det
        return a, b, RR