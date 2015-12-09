base_dir = "data/baseline_data/"
area_lookup_file = base_dir+"sub-national/area_lookup/area_lookup.csv"
area_lookup = {}

def __read_area_lookup(self):
        #Read the list of super and sub reagions for spatial aggregation.
        #Also add hypothetical entries for Wales, Scotland and Northern Ireland
              
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

        assert len(self.area_lookup) == 9, "Should be 9 regions in lookup"+str(len(self.area_lookup))
        
       

        # Finally add wales, scot, ni. The codes match arbitrary names that I chose
        # when creating the UK subnational file (had to add hypothetical regions for the
        # other three countries)
        #self.area_lookup["Wales"] = ["WALE"]
        #self.area_lookup["Scotland"] = ["SCOT"]
        #self.area_lookup["Northern Ireland"] = ["NIRE"]
