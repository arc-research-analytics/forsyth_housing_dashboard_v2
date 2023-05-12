import streamlit as st
from PIL import Image
import pandas as pd
import geopandas as gpd
import plotly.express as px
import pydeck as pdk
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
                padding-left: 30px;
                padding-right: 30px;
                padding-top: 10px;}
            span[data-baseweb="tag"] {
                background-color: #022B3A 
                }
            div[data-testid="metric-container"] {
                text-align: left;
                color: #022B3A;
                }
            [data-testid="stMetricLabel"] {
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
    value=(2018,2020),
    help='Filter sales data by transaction year.'
)

# trends title 
if years[0] != years[1]:
    st.markdown(f"<h2 style='color:#022B3A'>Forsyth County Housing Trends | <span style='color:#FF8966'>{years[0]} - {years[1]}</span></h2>", unsafe_allow_html=True)
else:
    st.markdown(f"<h2 style='color:#022B3A'>Forsyth County Housing Trends | <span style='color:#FF8966'>{years[0]} only</span></h2>", unsafe_allow_html=True)

# square footage slider
sq_footage = st.sidebar.select_slider(
    'Home size (SF):',
    options=['<1000',1000,2500,5000,'>5000'],
    value=('<1000','>5000'),
    help="Filter sales data by reported square footage of home as reported by the tax assessor's office."
)

# sub-geography slider
geography_included = st.sidebar.radio(
    'Geography included:',
    ('Entire county','Sub-geography'),
    index=0,
    help='Defaults to entire county. Selecting "Sub-geography" will allow for a multi-select of smaller groupings throughout the county.'
)
sub_geo = ""
if geography_included == 'Sub-geography':
    sub_geo = st.sidebar.multiselect(
        'Select one or more regions:',
        ['Cumming', 'North Forsyth', 'West Forsyth', 'South Forsyth'],
        ['Cumming'],
        help='"Regions" are pre-defined groupings of Census tracts.')

# horizongal divider
st.sidebar.divider()
map_view = st.sidebar.radio(
        'Map view:',
        ('2D', '3D'),
        index=0,
        horizontal=True,
        help='Toggle to 3D for extruded polygons which show "height" based on the quantity of total sales. Note that darker Census tract shading corresponds to higher median sales price per SF.'
        )



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

    # get the columns to be used by charter
    df['year'] = pd.DatetimeIndex(df['Sale Date']).year
    df['month'] = pd.DatetimeIndex(df['Sale Date']).month
    df['year-month'] = df['year'].astype(str) + '-' + df['month'].astype(str)

    df = df[['Square Ft','year_sale','year_blt','price_sf','GEOID','Sub_geo','unique_ID', 'year', 'month', 'year-month', 'Sale Date']]

    # return this item
    return df

df_init = load_tab_data()

def filter_data():
    df = df_init

    # home size filter
    if ((sq_footage[0] == '<1000') & (sq_footage[1] != '>5000')):
        filtered_df = df[df['Square Ft'] <= sq_footage[1]]
    elif ((sq_footage[0] != '<1000') & (sq_footage[1] == '>5000')):
        filtered_df = df[df['Square Ft'] >= sq_footage[0]]
    elif ((sq_footage[0] == '<1000') & (sq_footage[1] == '>5000')):
        filtered_df = df #i.e., don't apply a filter
    elif sq_footage[0] == sq_footage[1]:
        st.error("Please select unique slider values for home size.")
    else:
        filtered_df = df[(df['Square Ft'] >= sq_footage[0]) & (df['Square Ft'] <= sq_footage[1])]

    # filter by sub-geography (if applicable)
    if geography_included == 'Sub-geography':
        filtered_df = filtered_df[filtered_df['Sub_geo'].isin(sub_geo)]

    # year filter
    if years[0] != years[1]:
        filtered_df_map_KPI = filtered_df[(filtered_df['year_sale'] >= years[0]) & (filtered_df['year_sale'] <= years[1])]
    else:
        filtered_df_map_KPI = filtered_df[filtered_df['year_sale'] == years[0]]

    # now group by GEOID
    grouped_df = filtered_df_map_KPI.groupby('GEOID').agg({
        'price_sf':'median',
        'year_blt':'median',
        'unique_ID':'count',
        }).reset_index()

    return filtered_df, grouped_df, filtered_df_map_KPI

# colors to be used in the mapping functions
custom_colors = [
    '#97a3ab',
    '#667883',
    '#37505d',
    '#022b3a'
    ]

# convert the above hex list to RGB values
custom_colors = [tuple(int(h.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) for h in custom_colors]

def mapper_2D():

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
        height=540
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

def mapper_3D():

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

    # set initial view state
    initial_view_state = pdk.ViewState(
        latitude=34.307054643497315,
        longitude=-84.10535919531371, 
        zoom=9.2, 
        max_zoom=12, 
        min_zoom=8,
        pitch=45,
        bearing=0,
        height=540
        )
    
    # create geojson layer
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
    # test chart
    df = filter_data()[0]

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
        title_text='<span style="font-size: 18px;">Median Sales Price / SF</span> <br> <span style="font-size: 14px;">Orange vertical lines show range of selected years</span>', 
        title_x=0.05, 
        title_y=0.93,
        title_font_color="#022B3A",
        yaxis = dict(
            linecolor = "#022B3A",
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
        height=510,
        hovermode="x unified")

    # add shifting vertical lines
    year_start = {
        2018:'2018-1',
        2019:'2019-1',
        2020:'2020-1',
        2021:'2021-1',
        2022:'2022-1'
    }

    year_end = {
        2018:'2018-12',
        2019:'2019-12',
        2020:'2020-12',
        2021:'2021-12',
        2022:'2022-12'
    }

    fig.add_vline(x=year_start[years[0]], line_width=2, line_dash="dash", line_color="#FF8966")
    fig.add_vline(x=year_end[years[1]], line_width=2, line_dash="dash", line_color="#FF8966")

    return fig

# define columns
col1, col2, col3 = st.columns([4,0.2,4])


if map_view == '2D':
    col1.pydeck_chart(mapper_2D(), use_container_width=True)
else:
    col1.pydeck_chart(mapper_3D(), use_container_width=True)



# kpi's
median_value = '${:,.0f}'.format(filter_data()[2]['price_sf'].median())
total_sales = '{:,.0f}'.format(filter_data()[1]['unique_ID'].sum())
med_vintage = '{:.0f}'.format(filter_data()[2]['year_blt'].median())

with col3:
    subcol1, subcol2, subcol3 = st.columns([1, 1, 1])
    subcol1.metric("Median price / SF", median_value)
    subcol2.metric("Total sales", total_sales)
    subcol3.metric("Median vintage", med_vintage)


# line chart
col3.plotly_chart(charter(), use_container_width=True, config = {'displayModeBar': False})

# arc logo
im = Image.open('content/logo.png')
with col3:
    subcol1, subcol2, subcol3, subcol4, subcol5 = st.columns([1, 1, 1, 1, 1])
    subcol4.write("Powered by")
    subcol5.image(im, width=80)


if map_view == '2D':
    with col1:
        expander = st.expander("Note")
        expander.markdown("<span style='color:#022B3A'> Darker shades of Census tracts represent higher sales prices per SF for the selected time period. Dashboard excludes non-qualified, non-market, and bulk transactions. Excludes transactions below $1,000 and homes smaller than 75 square feet. Data downloaded from Forsyth County public records on May 11, 2023.</span>", unsafe_allow_html=True)
else:
    with col1:
        expander = st.expander("Note")
        expander.markdown("<span style='color:#022B3A'>Shift + click to change map pitch & angle. Census tract 'height' representative of total sales per tract. Darker shades of Census tracts represent higher sales prices per SF for the selected time period. Dashboard excludes non-qualified, non-market, and bulk transactions. Excludes transactions below $1,000 and homes smaller than 75 square feet. Data downloaded from Forsyth County public records on May 11, 2023.</span>", unsafe_allow_html=True)
