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
            span[data-baseweb="tag"] {
                background-color: #022B3A !important;
                }
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

# trends title 
if years[0] != years[1]:
    # st.markdown(f"<h2 style='color:#022B3A; display: inline'>Forsyth County Housing Trends |</h2><h2 style='color:#FF8966; display: inline'> {years[0]} - {years[1]}</h2>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='color:#022B3A'>Forsyth County Housing Trends | <span style='color:#FF8966'>{years[0]} - {years[1]}</span></h2>", unsafe_allow_html=True)
else:
    st.markdown(f"<h2 style='color:#022B3A'>Forsyth County Housing Trends | <span style='color:#FF8966'>{years[0]} only</span></h2>", unsafe_allow_html=True)

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

# arc logo
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
        'Year  Built':'year_blt',
        'Year':'year_sale'
    }, inplace=True)
    df['GEOID'] = df['GEOID'].astype(str)
    df['unique_ID'] = df['Address'] + '-' + df['Sale Date'].astype(str) + '-' + df['price_number'].astype(str)
    df = df[['Square Ft', 'year_sale', 'year_blt','price_sf','GEOID','Sub_geo','unique_ID']]

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

    # now group by GEOID
    grouped_df = filtered_df.groupby('GEOID').agg({
        'price_sf':'median',
        'year_blt':'median',
        'unique_ID':'count',
        }).reset_index()

    return filtered_df, grouped_df

# colors to be used in the mapping functions
custom_colors = [
    '#97a3ab',
    '#667883',
    '#37505d',
    '#022b3a'
    ]

# convert the above hex list to RGB values
custom_colors = [tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) for h in custom_colors]

def map_2D():

    # tabular data
    df = filter_data()[1]

    # read in geospatial
    gdf = gpd.read_file('Geography/Forsyth_CTs.gpkg')

    # join together the 2, and let not man put asunder
    joined_df = gdf.merge(df, left_on='GEOID', right_on='GEOID')

    # ensure we're working with a geodataframe
    joined_df = gpd.GeoDataFrame(joined_df)

    # format the column to show the price / SF
    joined_df['price_sf_formatted'] = joined_df['price_sf'].apply(lambda x: "${:.2f}".format((x)))

    # add 1,000 separator to column that will show total sales
    joined_df['total_sales'] = joined_df['unique_ID'].apply(lambda x: '{:,}'.format(x))


    # set choropleth color
    joined_df['choro_color'] = pd.cut(
            joined_df['price_sf'],
            bins=len(custom_colors),
            labels=custom_colors,
            include_lowest=True,
            duplicates='drop'
            )
    
    # create map intitial state
    initial_view_state = pdk.ViewState(
        latitude=34.207054643497315,
        longitude=-84.10535919531371, 
        zoom=9.6, 
        max_zoom=12, 
        min_zoom=8,
        pitch=0,
        bearing=0,
        height=590
    )

    geojson = pdk.Layer(
        "GeoJsonLayer",
        joined_df,
        pickable=True,
        autoHighlight=True,
        highlight_color = [255, 255, 255, 80],
        opacity=0.5,
        stroked=True,
        filled=True,
        wireframe=True,
        get_fill_color='choro_color',
        get_line_color=[0, 0, 0, 255],
        line_width_min_pixels=1
    )

    tooltip = {
            "html": "Median price per SF: <b>{price_sf_formatted}</b><br>Total sales: <b>{total_sales}</b>",
            "style": {"background": "rgba(2,43,58,0.7)", "color": "white", "font-family": "Helvetica", "text-align": "center"},
            }
    
    r = pdk.Deck(
        layers=geojson,
        initial_view_state=initial_view_state,
        map_provider='mapbox',
        map_style='road',
        tooltip=tooltip)

    return r


col1, col2, col3 = st.columns([2,0.2,2])
col1.pydeck_chart(map_2D(), use_container_width=True)
col1.markdown("<span style='color: #022B3A'><b>Note:</b> Darker shades of Census tracts represent higher sales prices per SF for the selected time period.</span>", unsafe_allow_html=True)


