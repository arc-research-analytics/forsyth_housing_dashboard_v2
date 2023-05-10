import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
from PIL import Image
from datetime import date

# customize
st.set_page_config(
    page_title='Housing Dashboard', 
    layout="wide",
    page_icon=":house:",
    )

# sidebar variables vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

im = Image.open('content/logo.png')
col1, col2, col3 = st.sidebar.columns([1,1,1])
col2.image(im, width=80)
col2.write("")
col2.write("")

# all the quarters available for selection
years = st.sidebar.select_slider(
    'Transaction year:',
    options=[
    2018,
    2019,
    2020,
    2021,
    2022
    ],
    value=(2018,2020)
)


# vintage filter
vintage = st.sidebar.select_slider(
    'Construction vintage:',
    options=['Pre-2000',2010,2015,'Post-2020'],
    value=('Pre-2000','Post-2020')
)

# square footage filter
sq_footage = st.sidebar.select_slider(
    'Home size (SF):',
    options=['<1000',1000,2500,5000,'>5000'],
    value=('<1000','>5000')
)

# sub-geography filter
geography_included = st.sidebar.radio(
    'Geography included:',
    ('Entire county','Sub-geography'),
    index=0
)
sub_geo = ""
if geography_included == 'Sub-geography':
    sub_geo = st.sidebar.multiselect(
        'Select one or more regions:',
        ['Cumming', 'North Forsyth', 'West Forsyth', 'South Forsyth'],
        ['Cumming'])

# sidebar variables ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

@st.cache_data
def load_data():
    df = pd.read_csv('Geocoded_Final_Joined.csv', thousands=',', keep_default_na=False)

    df.rename(columns={
        'Year  Built':'year_blt',
        'Year':'year_sale'
    }, inplace=True)
    df['GEOID'] = df['GEOID'].astype(str)
    df['unique_ID'] = df['Address'] + '-' + df['Sale Date'].astype(str) + '-' + df['price_number'].astype(str)
    df = df[['Address', 'Square Ft', 'year_blt', 'Sale Date', 'year_sale', 'price_number','price_sf','GEOID','Sub_geo','unique_ID']]

    # read in geospatial
    gdf = gpd.read_file('Geography/Forsyth_CTs.gpkg')

    # join together the 2, and let not man put asunder
    joined_df = gdf.merge(df, left_on='GEOID', right_on='GEOID')
    joined_df.rename(columns={
        'Sub_geo_x':'Sub_geo',
    }, inplace=True)
    joined_df['Sale Date'] = pd.to_datetime(joined_df['Sale Date'])
    joined_df = joined_df[['GEOID',
                        #    'geometry',
                           'Sale Date',
                           'year_sale',
                           'Square Ft',
                           'year_blt',
                           'price_number',
                           'price_sf',
                           'unique_ID',
                           'Sub_geo'
                           ]]

    # return this
    return joined_df

df = load_data()

st.dataframe(df)


