import solara
from solara.components.file_drop import FileInfo
from solara import Reactive, reactive
import leafmap
import os
from typing import Union
from ipywidgets import widgets
import copy
import json
from shapely.geometry import shape
import shapely, shapely.wkt
import pandas as pd
import datetime, time
from typing import Dict, List, Tuple, Any
from io import BytesIO, StringIO
# from utils import calculate_acre
from IPython.display import HTML, display
from ipywidgets import HTML
from IPython.display import display

import base64

APP_VERSION = "v20240119"
APP_DESC = f"Boundary Squad Widget ({APP_VERSION}): jun.xiong@bayer.com"
BUTTON_KWARGS = dict(color="primary", text=True, outlined=True)
sources = ["Enrollement", "ShrinkWrap"]#, "LastSubmit"]

class State:
    zoom = reactive(20)
    center = reactive((20, 0))
    enroll_wkt = reactive(None)
    algo_wkt = reactive(None)
    last_wkt = reactive(None)
    df = reactive(pd.DataFrame({}))
    # timelapse_boundary = reactive(pd.DataFrame({}))
    # s2_image_path = solara.reactive("1.jpg")
    # cdl_image_path = solara.reactive("1.jpg")
    edit_time = reactive(0.)
    version_list = reactive([''])
    download = reactive('')
    download_name = reactive('')
    disableDownload = reactive(True)
    reviewer = reactive('')

def wkt_to_featurecollection(wkt: str) -> Dict[str, Any]:
    geom = shapely.wkt.loads(wkt)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": geom.__geo_interface__,
            }
        ],
    }

def radio_button_row(labels: List[str], padding: str = "0px 0px 0px 5px") -> Tuple[widgets.HBox, List[widgets.Checkbox]]:
    box = [
        widgets.Checkbox(
            False,
            description=w,
            indent=False,
            layout=widgets.Layout(width="100px", padding=padding),
        )
        for w in labels
    ]
    return widgets.HBox(box), box


def widget_droplist(options: List[str], desc: str, width: str = "270px", padding: str = "0px 0px 0px 5px", **kwargs) -> widgets.Dropdown:
    return widgets.Dropdown(
        options=[""] + options,
        description=desc,
        style={"description_width": "initial"},
        layout=widgets.Layout(width=width, padding=padding),
        **kwargs,
    )

def add_widgets(m: leafmap.Map, padding:str="0px 0px 0px 5px") -> None:
    style = {"description_width": "initial"}

    # call backs
    def upload_field_uuid(event):
        field_sel.options = [''] + sorted(State.df.value['field_uuid'].values.tolist())
        output.outputs = ()

    def change_field(change):
        State.disableDownload.set(True)
        # remove previous layers
        try:
            m.remove_layer(m.find_layer("Footprint"))
            m.remove_layer(m.find_layer("Footprint2"))
        except:
            pass
        # m.remove_layer(m.find_layer("Footprint3"))
        # reset version
        version_selector.value = ""

        # reset classes
        for box in nonag_class_checkbox:
            box.value = False
        is_similar_check.value = False

        if not change.new: 
            return
        row = State.df.value[State.df.value.field_uuid == change.new].iloc[0]

        m.add_geojson(
            wkt_to_featurecollection(row["Enrollment_WKT"]),
            layer_name="Footprint",
            info_mode=None,
            zoom_to_layer=True,
            # hover_style={'opacity':0.9},
            style_callback=lambda feat: {
                "color": "red",
                "opacity": 0.9,
                "hover_style": {"opacity": 0.9},
            },
        )
        m.add_geojson(
            wkt_to_featurecollection(row["ShrinkwrapV2_WKT"]),
            info_mode=None,
            layer_name="Footprint2",
            style_callback=lambda feat: {"color": "blue", "opacity":0.9},
        )
        # m.add_geojson(
        #     wkt_to_featurecollection(row["LastSubmit_WKT"]),
        #     info_mode=None,
        #     layer_name="Footprint3",
        #     style_callback=lambda feat: {"color": "green", "opacity":0.9},
        # )
        geom = shapely.wkt.loads(row["Enrollment_WKT"])
        m.zoom_to_bounds(geom.bounds)

        State.reviewer.set(row["Reviewer"])
        State.enroll_wkt.set(row["Enrollment_WKT"])
        State.algo_wkt.set(row["ShrinkwrapV2_WKT"])
        # State.last_wkt.set(row["LastSubmit_WKT"])
        # State.s2_image_path.set("preview.jpg")
        # State.cdl_image_path.set("preview.jpg")

        # skip for deployed version
        # State.s2_image_path.set(f"{PRE_DIR}/{change.new}/s2.jpg")
        # State.cdl_image_path.set(f"{PRE_DIR}/{change.new}/cdl.jpg")
        # ts_df = pd.read_csv(f"{PRE_DIR}/{change.new}/mask.csv")
        # State.timelapse_boundary.set(ts_df)

        output.outputs = ()
        # output.append_stdout(str(row))
        # output.append_stdout("Multi-Polygon! \nMove on in Google Earth or QGIS.")


    def select_boundary(change):
        State.disableDownload.set(True)
        layer = m.find_layer("Footprint")
        try:
            m.remove_layer(m.find_layer("Footprint2"))
            m.remove_layer(m.find_layer("Footprint3"))
        except:
            pass
        if layer is None:
            print("Error: Can not find Footprint layer")
            return

        if change.new == "Enrollement":
            selected_wkt = State.enroll_wkt.value
        elif change.new == "ShrinkWrap":
            selected_wkt = State.algo_wkt.value
        # elif change.new == "LastSubmit":
        #     selected_wkt = State.last_wkt.value
        # elif change.new == "Timelapse":
        #     timelapse_sel.options = [""] + [str(i) for i in range(16)]
        #     timelapse_sel.disabled = False
        #     return
        # else: # empty
        #     # m.remove_layer(m.find_layer("Footprint"))
        #     # m.remove_layer(m.find_layer("Footprint2"))
        #     pass
        layer.data = wkt_to_featurecollection(selected_wkt)
        draw_features = copy.deepcopy(layer.data["features"])
        for feature in draw_features:
            feature["properties"]["style"]["color"] = "green"
        m.draw_control.data = draw_features
        m.draw_features = draw_features
        State.edit_time.set(time.time())

        output.outputs = ()
        # output.append_stdout(selected_wkt)

    # def select_specifc_date(change):
    #     layer = m.find_layer("Footprint")
    #     m.remove_layer(m.find_layer("Footprint2"))

    #     idx = int(change.new)
    #     feature_collection = wkt_to_featurecollection(
    #         State.timelapse_boundary.value.iloc[idx]["mask"]
    #     )

    #     layer.data = feature_collection
    #     draw_features = copy.deepcopy(layer.data["features"])
    #     for feature in draw_features:
    #         feature["properties"]["style"]["color"] = "green"
    #     m.draw_control.data = draw_features
    #     m.draw_features = draw_features
    def export_wkt(e):
        # -1: latest saved edits
        time_sec = time.time() - State.edit_time.value
        g1 = shape(m.draw_features[-1]["geometry"])

        # save to local files.
        marked_classed = [str(box.value) for box in nonag_class_checkbox]        
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")

        # calc acreage
        enrollment_acre = calculate_acre(shapely.wkt.loads(State.enroll_wkt.value))
        algo_acre = calculate_acre(shapely.wkt.loads(State.algo_wkt.value))
        manual_acre = calculate_acre(shapely.wkt.loads(g1.wkt))

        field_uuid = field_sel.value
        out_data = dict(
            reviewer=State.reviewer.value,
            revised=formatted_time,
            field_uuid=field_uuid,
            enrollment_wkt=State.enroll_wkt.value,
            shrinkwrap_wkt=State.algo_wkt.value,
            is_similar_check=is_similar_check.value,
            Version=version_selector.value,
            # ts_no = timelapse_sel.value,
            manual_wkt=g1.wkt,
            enrollment_acre=enrollment_acre,
            algo_acre=algo_acre,
            manual_acre=manual_acre,
            marked_classed=marked_classed,
        )
        # iwith open(f"{field_uuid}.json", "w", encoding="utf-8") as f:
        #     json.dump(out_data, f, ensure_ascii=False, indent=4)
        # output.outputs = ()
        # output.append_stdout('Click "Download to local" to save.')
            
        filename = f"{field_uuid}.json"
        download_content = json.dumps(out_data)

        b64 = base64.b64encode(download_content.encode())
        payload = b64.decode()

        html_buttons = f'''<html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
        <a download="{filename}" href="data:text/csv;base64,{payload}" download>
        <button style="width: 100%" class="p-Widget jupyter-widgets jupyter-button widget-button mod-warning">{filename}</button>
        </a>
        </body>
        </html>
        '''

        html_button = html_buttons.format(payload=payload,filename=filename)
        with output:
            display(HTML(html_button))

    # widgets
    upload_button = widgets.Button(
        description="Update fieldlist", layout=widgets.Layout(width="300px")
    )
    upload_button.on_click(upload_field_uuid)

    legend_lbl = [
        widgets.Label(value=r"\(\color{" + color + "} {" + lbl + "}\)")
        for lbl, color in zip(sources, ["red", "blue", "black"])
    ]
    legend_box = widgets.HBox(legend_lbl)
    field_sel = widget_droplist([], "Field_uuid:")
    field_sel.observe(change_field, names="value")

    is_similar_check = widgets.Checkbox(False, description="Similar Enroll/Algo", indent=False, layout=widgets.Layout(width="300px", padding=padding))

    version_selector = widget_droplist(sources, "Version:")
    version_selector.observe(select_boundary, names="value")

    # timelapse_sel = widget_droplist([], "Date:", disabled=True)
    # timelapse_sel.observe(select_specifc_date, names="value")
    labelWidget = widgets.Label(value="the following non-ag classed are found:")
    row1, checkbox1 = radio_button_row(["Grass", "Shrub", "Forest"])
    row2, checkbox2 = radio_button_row(["Road", "Watergate", "Irri-Pivot"])
    row3, checkbox3 = radio_button_row(["M-practise", "Overlap", "Others"])
    nonag_class_box = widgets.VBox([row1, row2, row3])
    nonag_class_checkbox = checkbox1 + checkbox2 + checkbox3
    export_button = widgets.Button(
        description="Click 'Save' before Generate Download", layout=widgets.Layout(width="300px")
    )
    export_button.on_click(export_wkt)
    output = widgets.Output()
    
    box = widgets.VBox(
        [
            upload_button,
            field_sel,
            legend_box,
            is_similar_check, 
            version_selector,
            # timelapse_sel,
            labelWidget,
            nonag_class_box,
            export_button,
            output,
        ]
    )
    m.add_widget(box, position="topright", add_header=False)


# init leafmap object
class Map(leafmap.Map):
    def __init__(self, **kwargs):
        kwargs["toolbar_control"] = False
        super().__init__(**kwargs)
        basemap = {
            "url": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            "attribution": "Google",
            "name": "Google Satellite",
        }
        self.add_tile_layer(**basemap, shown=True)
        add_widgets(self)




@solara.component
def FileManager() -> None:
    content, set_content = solara.use_state(b"")
    filename, set_filename = solara.use_state("")
    size, set_size = solara.use_state(0)

    def load_df(data: Union[str, StringIO], filename='') -> pd.DataFrame:
        """helper to load either csvfile or BytesIO object into dataframe"""
        set_filename(filename)
        new_df = pd.read_csv(data, delimiter=",")
        # assert all(col in new_df.columns for col in ["field_uuid", "Enrollment_WKT", "ShrinkwrapV2_WKT", "LastSubmit_WKT", "Reviewer"]), 'missing required columns!'
        assert all(col in new_df.columns for col in ["field_uuid", "Enrollment_WKT", "ShrinkwrapV2_WKT"]), 'missing required columns!'
        State.df.set(new_df)
        set_size(new_df.shape[0])

    def load_demo_df(file: FileInfo= None) -> None:
        load_df('demo_data.csv', 'demo_data.csv')

    def load_file_df(file: FileInfo) -> None:
        if file:
            content = StringIO(file["file_obj"].readall().decode())
            load_df(content, file["name"])

    solara.FileDrop(
        label="Drop CSV here (`text` col required)!",
        on_file=load_file_df,
        lazy=True,
    )
    # We use solara.Column to force these two buttons to be stacked instead of side-by-side
    solara.Button(
        label="Load demo dataset",
        on_click=load_demo_df,
        **BUTTON_KWARGS,
    )
    solara.Info(f"File {filename} has rows: {size}\n")



# create main page
@solara.component
def Page() -> None:
    solara.Title(APP_DESC)
    with solara.Sidebar():
        FileManager()
        solara.Markdown("""### Instruction \n- Drag a csvfile or load the test data\n- Click "Update fieldlist
\n- Pick a field from drop_list\n- Decide which boundary source is using,\n- Manual edit if needed
\n- Mark all the non-ag classes found in the field\n- Click "Save" Button to generate download\n- Download the edits to local""")
    # with solara.lab.Tabs():
    #     with solara.lab.Tab("Boundary", icon_name="mdi-chili-hot"):
    #         # solara.Markdown(
    #         #     """- Pick a field from field_uuid droplist to get started\n- Decide which boundary source is using,\n- If manual edit is needed, do it and save afterwards\n- Mark all the non-ag classes found in the field"""
    #         # )
    Map.element(  # type: ignore
        # zoom=State.zoom.value,
        center=State.center.value,
        scroll_wheel_zoom=True,
        toolbar_ctrl=False,
        data_ctrl=False,
        height="780px",
    )
    # with solara.FileDownload(State.download.value, State.download_name.value):
    #     solara.Button("Download to local", icon_name="mdi-cloud-download-outline", color="primary", disabled=State.disableDownload.value)
        # with solara.lab.Tab("Timelapse", icon_name="mdi-timelapse"):
        #     solara.Image(State.s2_image_path.value)
        # with solara.lab.Tab("USDA/CDL", icon_name="mdi-houzz-box"):
        #     solara.Image(State.cdl_image_path.value)

if __name__ == "__main__":
    Page()
