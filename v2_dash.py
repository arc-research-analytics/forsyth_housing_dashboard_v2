import streamlit as st
from PIL import Image
import pandas as pd
import geopandas as gpd
import plotly.express as px
import pydeck as pdk
from millify import millify
from millify import prettify
from datetime import date

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
            #MainMenu, footer {visibility: hidden;}
            section.main > div:has(~ footer ) {
                padding-bottom: 1px;
                padding-left: 20px;
                padding-right: 20px;
                padding-top: 10px;}
            span[data-baseweb="tag"] {
                background-color: #022B3A 
                }
            div[data-testid="metric-container"] {
                text-align: left;
                color: #022B3A;
                }
            div.stActionButton{visibility: hidden;}
        </style>
       """

st.markdown(hide_default_format, unsafe_allow_html=True)

# sidebar variables vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

st.sidebar.markdown(f"<h3 style='text-align:center;color:#FFFFFF;font-style:italic;'>Filter housing data by:</h3>", unsafe_allow_html=True)
st.sidebar.write("")

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
    st.markdown(f"<h2 style='color:#022B3A'>Forsyth County Housing Trends | {years[0]} - {years[1]}</h2>", unsafe_allow_html=True)
else:
    st.markdown(f"<h2 style='color:#022B3A'>Forsyth County Housing Trends | {years[0]} only</h2>", unsafe_allow_html=True)

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
col2.write("")
col2.write("")
col2.write("")
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
    df = df[['Square Ft','year_sale','year_blt','price_sf','GEOID','Sub_geo','unique_ID', 'Sale Date']]

    # return this item
    return df

init_df = load_tab_data()

def filter_data():
    df = init_df

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

filtered_df = filter_data()[0]
grouped_df = filter_data()[1]

# colors to be used in the mapping functions
custom_colors = [
    '#97a3ab',
    '#667883',
    '#37505d',
    '#022b3a'
    ]

# convert the above hex list to RGB values
custom_colors = [tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) for h in custom_colors]

def mapper():

    # tabular data
    df = grouped_df

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

    if map_view == '2D':

        # create map intitial state
        initial_view_state = pdk.ViewState(
            latitude=34.207054643497315,
            longitude=-84.10535919531371, 
            zoom=9.6, 
            max_zoom=12, 
            min_zoom=8,
            pitch=0,
            bearing=0,
            height=560
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
            get_fill_color='choro_color',
            get_line_color=[0, 0, 0, 255],
            line_width_min_pixels=1
        )
    else:
        initial_view_state = pdk.ViewState(
            latitude=34.307054643497315,
            longitude=-84.10535919531371, 
            zoom=9.2, 
            max_zoom=12, 
            min_zoom=8,
            pitch=45,
            bearing=0,
            height=560
            )
        geojson = pdk.Layer(
        "GeoJsonLayer",
        joined_df,
        pickable=True,
        autoHighlight=True,
        highlight_color = [255, 255, 255, 90],
        opacity=0.5,
        stroked=False,
        filled=True,
        wireframe=False,
        extruded=True,
        get_elevation='unique_ID * 50',
        get_fill_color='choro_color',
        get_line_color='choro_color',
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

def charter():
    # go read the dataaaaa
    df = filtered_df

    # create columns extracting just the month and year from the 'Sale Date' column
    df['year'] = pd.DatetimeIndex(df['Sale Date']).year
    df['month'] = pd.DatetimeIndex(df['Sale Date']).month
    df['year-month'] = df['year'].astype(str) + '-' + df['month'].astype(str)

    # group by 'year-month' to provide a monthly summary of the filtered sales
    df_grouped = df.groupby('year-month').agg({
        'price_sf':'median',
        'month':pd.Series.mode,
        'year':pd.Series.mode,
        }).reset_index()

    # sort the data so that it's chronological
    df_grouped = df_grouped.sort_values(['year', 'month'])

    fig = px.line(
        df_grouped, 
        x="year-month", 
        y=df_grouped['price_sf'],
        labels={
            'year-month':'Time Period'
            })
      
    # modify the line itself
    fig.update_traces(
        mode="lines",
        line_color='#022B3A',
        hovertemplate=None
        )

    # update the fig
    fig.update_layout(
        title_text='Monthly Price per SF', 
        title_x=0.05, 
        title_y=0.93,
        title_font_color="#FFFFFF",
        yaxis = dict(
            title = None,
            tickfont_color = '#022B3A',
            tickfont_size = 14,
            tickformat = '$.0f',
            showgrid = False
            ),
        xaxis = dict(
            linecolor = "#022B3A",
            linewidth = 1,
            tickfont_color = '#022B3A',
            title = None,
            tickformat = '%b %Y',
            dtick = 'M3'
            ),
        height=530,
        hovermode="x unified")

    # add shifting vertical lines
    year_start = {
        2018:'2018-1',
        2019:'2019-1',
        2020:'2020-1',
        2021:'2021-1',
        2022:'2022-1'
    }

    return fig


col1, col2, col3 = st.columns([2,0.2,2])
map_view = col2.radio(
            'Map view:',
            ('2D', '3D'),
            index=0
            )


col1.pydeck_chart(mapper(), use_container_width=True)

# kpi's
df_metric = filter_data()[0]

with col3:
    subcol1, subcol2, subcol3 = st.columns([1, 1, 1])
    subcol1.metric("median home price:", 65)
    subcol2.metric("total sales:", "5,000")
    subcol3.metric("median vintage:", 2017)




# line chart
col3.plotly_chart(charter(), use_container_width=True, config = {'displayModeBar': False})





if map_view == '2D':
    col1.markdown("<span style='color: #022B3A'><b>Note:</b> Darker shades of Census tracts represent higher sales prices per SF for the selected time period.</span>", unsafe_allow_html=True)
else:
    col1.markdown("<span style='color: #022B3A'><b>Note:</b> Shift + click to change map pitch & angle. Darker shades of Census tracts represent higher sales prices per SF for the selected time period. Greater sales volume represented by 'taller' census tracts.</span>", unsafe_allow_html=True)





