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


class ProjectionComponent():
    """Superclass for components of population projection (e.g. birth)"""
    
    def project(self, *args):
        """Project the given population forward one year and return the
        new population. Arguments are things like previous populations,
        the exact requirements will depend on the sub class."""
        return inPop

    # A scenario for fert/mort/mig models to use (initialised by PopProjection)
    scenario = []