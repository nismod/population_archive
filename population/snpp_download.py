import os.path
import json
import pandas as pd
import requests
import ukcensusapi.Nomisweb as Api

# England SNPP by gender by SYOA from UKCensusAPI
cache_dir = "./raw_data"
data_api = Api.Nomisweb(cache_dir)

# need to do this in 2 batches as entire table has >1000000 rows
table_internal = "NM_2006_1" # 2014-based SNPP
query_params = {
  "gender": "1,2",
  "c_age": "101...191",
  "MEASURES": "20100",
  "date": "latest", # 2014-based
  "projected_year": "2014...2027",
  "select": "geography_code,projected_year_name,gender,c_age,obs_value",
  "geography": "1946157057...1946157382"
}
snpp_e = data_api.get_data(table_internal, query_params)

query_params["projected_year"] = "2028...2039"
snpp_e = snpp_e.append(data_api.get_data(table_internal, query_params))
# make age actual year
snpp_e.C_AGE = snpp_e.C_AGE - 101

#print(snpp_e.head())


# Wales
wales_raw = cache_dir + "/snpp_w.csv"
if os.path.isfile(wales_raw): 
  snpp_w = pd.read_csv(wales_raw)
else:
  fields = ['Area_AltCode1','Year_Code','Data','Gender_Code','Age_Code','Area_Hierarchy','Variant_Code']
  # StatsWales is an OData endpoint, so select fields of interest
  url = "http://open.statswales.gov.wales/dataset/popu5099?$select={}".format(",".join(fields))
  # use OData syntax to filter P (persons), AllAges (all ages), Area_Hierarchy 596 (LADs)
  url += "&$filter=Gender_Code ne 'P' and Area_Hierarchy eq 596 and Variant_Code eq 'Principal'"
  # 
  data = []
  while True:
    print(url)
    r = requests.get(url)
    r_data = r.json()
    data += r_data['value']
    if "odata.nextLink" in r_data:
      url = r_data["odata.nextLink"]
    else:
      break
  snpp_w = pd.DataFrame(data)

  # Remove unwanted and rename wanted columns
  snpp_w = snpp_w.drop(["Area_Hierarchy", "Variant_Code"], axis=1)
  snpp_w = snpp_w.rename(columns={"Age_Code": "C_AGE", 
                                  "Area_AltCode1": "GEOGRAPHY_CODE",
                                  "Data": "OBS_VALUE", 
                                  "Gender_Code": "GENDER", 
                                  "Year_Code": "PROJECTED_YEAR_NAME"})
  # Remove all but SYOA and make numeric 
  snpp_w = snpp_w[(snpp_w.C_AGE!="AllAges") & (snpp_w.C_AGE!="00To15") & (snpp_w.C_AGE!="16To64") & (snpp_w.C_AGE!="65Plus")]
  snpp_w.loc[snpp_w.C_AGE=="90Plus", "C_AGE"] = "90"
  snpp_w.C_AGE = pd.to_numeric(snpp_w.C_AGE)

  # convert gender to census convention 1=M, 2=F
  snpp_w.GENDER = snpp_w.GENDER.map({"M": 1, "F": 2})

  snpp_w.to_csv(wales_raw, index=False)

#print(snpp_w.head())

snpp_ew = snpp_e.append(snpp_w, ignore_index=False)
assert(len(snpp_ew) == 26*2*91*348) # 348 LADs x 91 ages x 2 genders x 26 years
# Scotland https://www.nrscotland.gov.uk/files//statistics/population-projections/snpp-2014/detailed/pop-proj-scot-areas-14-det-tab-ca-year.zip
# (1 csv per gender per year)

# Niron https://www.nisra.gov.uk/sites/nisra.gov.uk/files/publications/SNPP14-LGD14-SYA-1439.xlsx
# (1 worksheet per LAD equivalent)