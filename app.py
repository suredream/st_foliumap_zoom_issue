# TODO
# - upload from csvfile
# - upload to google sheet
# https://github.com/avrabyt/YouTube-Tutorials/blob/main/Streamlit-Python/Streamlit_GoogleSheets_Automation/main.py
# - join parcel boundary
# - get the lat/lon from the parcel boundary

import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
from st_aggrid import AgGrid, GridUpdateMode, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder
import glob
import leafmap.foliumap as leafmap


@st.cache_data
def data_upload(file):
    df = pd.read_csv(file)
    return df

df = data_upload("demo.csv")
gd = GridOptionsBuilder.from_dataframe(df)
gd.configure_pagination(enabled=True)
gd.configure_default_column(editable=True, groupable=True)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Click on the row to see the location on the map")
    gd.configure_selection(selection_mode="single", use_checkbox=True)
    gridoptions = gd.build()
    grid_table = AgGrid(
        df,
        gridOptions=gridoptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=600,
        allow_unsafe_jscode=True,
        # enable_enterprise_modules = True,
        theme="balham",
    )

    sel_row = grid_table["selected_rows"]
    st.subheader("Output")
    # try:
    #     st.write(sel_row[0])
    # except:
    #     pass

with col2:
    try:
        lat, lon = sel_row[0]["lat"], sel_row[0]["lon"]
        m = leafmap.Map(
            layers_control=False,
            center=[lat, lon],
            zoom=24,
            # scroll_wheel_zoom=True,
            # toolbar_ctrl=False,
            # data_ctrl=False,
        )
        m.add_basemap("SATELLITE")
        m.to_streamlit()
    except:
        pass