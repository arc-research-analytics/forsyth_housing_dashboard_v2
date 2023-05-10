import streamlit as st
from PIL import Image
import pandas as pd
import geopandas as gpd
import plotly.express as px
import pydeck as pdk
from millify import millify
from millify import prettify

# customize
st.set_page_config(
    page_title='Housing Dashboard', 
    layout="wide",
    page_icon=":house:",
    )

# the custom css lives here:
hide_default_format = """
        <style>
            .reportview-container .main footer {visibility: hidden;}    
            #MainMenu, header, footer {visibility: hidden;}
            section.main > div:has(~ footer ) {
            padding-bottom: 5px;}
            div.block-container{padding-top:1.5rem;}
            [data-testid="stMetricValue"] {
                color: #FF8966;
                font-size: 30px;
                font-weight:500;
                text-align: center;
                }
            [data-testid="stMetricLabel"] {
                color: #022B3A;
                font-weight:900;
                text-align: center;
                }
        </style>
       """

st.markdown(hide_default_format, unsafe_allow_html=True)

# sidebar variables vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

st.sidebar.markdown(f"<h3 style='text-align:center;color:#FFFFFF;font-style:italic;'>Filter housing data by:</h3>", unsafe_allow_html=True)

# all the years available for selection
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

# square footage slider
sq_footage = st.sidebar.select_slider(
    'Home size (SF):',
    options=['<1000',1000,2500,5000,'>5000'],
    value=('<1000','>5000')
)

# sub-geography slider
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

im = Image.open('content/logo.png')
col1, col2, col3 = st.sidebar.columns([1,1,1])
col2.write("")
col2.image(im, width=80)

# sidebar variables ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

@st.cache_data
def load_tab_data():
    # load the data
    df = pd.read_csv('Geocoded_Final_Joined.csv', thousands=',', keep_default_na=False)

    # clean up the data
    df.rename(columns={
        'Year':'year_sale'
    }, inplace=True)
    df['GEOID'] = df['GEOID'].astype(str)
    df['unique_ID'] = df['Address'] + '-' + df['Sale Date'].astype(str) + '-' + df['price_number'].astype(str)
    df = df[['Square Ft', 'year_sale', 'price_sf','GEOID','Sub_geo','unique_ID']]

    # return this item
    return df

def filter_data():
    df = load_tab_data()

    # year filter
    if years[0] != years[1]:
        filtered_df = df[(df['year_sale'] >= years[0]) & (df['year_sale'] <= years[1])]
    else:
        filtered_df = df[df['year_sale'] == years[0]]

    # home size filter
    if sq_footage[0] == sq_footage[1]:
        st.error("Please select unique slider values for home size.")
    elif ((sq_footage[0] == '<1000') & (sq_footage[1] != '>5000')):
        filtered_df = df[df['Square Ft'] <= sq_footage[1]]
    elif ((sq_footage[0] != '<1000') & (sq_footage[1] == '>5000')):
        filtered_df = df[df['Square Ft'] >= sq_footage[0]]
    elif ((sq_footage[0] == '<1000') & (sq_footage[1] == '>5000')):
        filtered_df = filtered_df #i.e., don't apply a filter
    else:
        filtered_df = df[(df['Square Ft'] >= sq_footage[0]) & (df['Square Ft'] <= sq_footage[1])]

    # filter by sub-geography (if applicable)
    if geography_included == 'Sub-geography':
        filtered_df = filtered_df[filtered_df['Sub_geo'].isin(sub_geo)]

    return filtered_df


df = filter_data()

st.dataframe(df, use_container_width=True)
st.write(df.shape)
st.write(f"first year: {years[0]}, second year: {years[1]}")


