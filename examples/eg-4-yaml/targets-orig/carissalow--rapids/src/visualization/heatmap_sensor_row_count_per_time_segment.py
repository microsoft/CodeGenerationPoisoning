import pandas as pd
import numpy as np
import plotly.express as px
from importlib import util
from pathlib import Path
import yaml

# import filter_data_by_segment from src/features/utils/utils.py
spec = util.spec_from_file_location("util", str(Path(snakemake.scriptdir).parent / "features" / "utils" / "utils.py"))
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)
filter_data_by_segment = getattr(mod,  "filter_data_by_segment")

def getRowCount(sensor_paths, sensor_names, time_segments_labels):
    sensors_row_count = pd.DataFrame()
    for sensor_path, sensor_name in zip(sensor_paths, sensor_names):
        sensor_data = pd.read_csv(sensor_path, usecols=["assigned_segments"])

        sensor_row_count = pd.DataFrame()
        if not sensor_data.empty:
            for time_segment in time_segments_labels:
                sensor_data_per_segment = filter_data_by_segment(sensor_data, time_segment)

                if not sensor_data_per_segment.empty:
                    sensor_row_count = pd.concat([sensor_row_count, sensor_data_per_segment.groupby(["local_segment"])[["local_segment"]].count().rename(columns={"local_segment": sensor_name})], axis=0, sort=False)
        sensors_row_count = pd.concat([sensors_row_count, sensor_row_count], axis=1, sort=False)
    
    sensors_row_count.index.name = "local_segment"
    sensors_row_count.index = sensors_row_count.index.str.replace(r"_RR\d+SS#", "#")
    
    return sensors_row_count

def getRowCountHeatmap(data_for_plot, pid, time_segment, html_file):

    fig = px.timeline(data_for_plot,
                        x_start="local_segment_start_datetime",
                        x_end="local_segment_end_datetime",
                        y="sensor",
                        color="scaled_value",
                        color_continuous_scale="Peach",
                        range_color=[0, 1],
                        opacity=0.7,
                        hover_data={"local_segment_start_datetime":False, "local_segment_end_datetime":False, "local_segment":True, "value":True, "scaled_value":True})

    fig.update_layout(title="Heatmap of sensor row count for " + time_segment + " segments. Pid: " + pid +". Label: " + label + "<br>y-axis shows the included sensors.<br>x-axis shows time segments.<br>z-axis (color) shows row count per sensor per segment instance.",
                xaxis=dict(side="bottom", title="Time Segments"),
                yaxis=dict(side="left", title="Sensors"),
                margin=dict(t=160))

    html_file.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    return html_file



with open(snakemake.input["participant_file"], "r", encoding="utf-8") as f:
    participant_file = yaml.safe_load(f)
label = participant_file["PHONE"]["LABEL"]

pid = snakemake.params["pid"]
sensor_names = [sensor_name.lower() for sensor_name in snakemake.params["sensor_names"]]
time_segments_type = snakemake.params["time_segments_type"]
time_segments_labels = pd.read_csv(snakemake.input["time_segments_labels"], header=0)["label"]

phone_data_yield = pd.read_csv(snakemake.input["phone_data_yield"], index_col=["local_segment"], parse_dates=["local_segment_start_datetime", "local_segment_end_datetime"]) #index_col=["local_segment_start_datetime"], 

# make sure the phone_data_yield file contains "phone_data_yield_rapids_ratiovalidyieldedminutes" and "phone_data_yield_rapids_ratiovalidyieldedhours" columns
if ("phone_data_yield_rapids_ratiovalidyieldedminutes" not in phone_data_yield.columns) or ("phone_data_yield_rapids_ratiovalidyieldedhours" not in phone_data_yield.columns):
    raise ValueError("Please make sure [PHONE_DATA_YIELD][RAPIDS][COMPUTE] is True AND [PHONE_DATA_YIELD][RAPIDS][FEATURES] contains [ratiovalidyieldedminutes, ratiovalidyieldedhours].")
phone_data_yield.loc[:, ["phone_data_yield_rapids_ratiovalidyieldedminutes", "phone_data_yield_rapids_ratiovalidyieldedhours"]] = phone_data_yield.loc[:, ["phone_data_yield_rapids_ratiovalidyieldedminutes", "phone_data_yield_rapids_ratiovalidyieldedhours"]].round(3).clip(upper=1)

sensors_row_count = getRowCount(snakemake.input["all_sensors"], sensor_names, time_segments_labels)
data_for_plot = phone_data_yield.rename(columns={"phone_data_yield_rapids_ratiovalidyieldedminutes": "ratiovalidyieldedminutes","phone_data_yield_rapids_ratiovalidyieldedhours": "ratiovalidyieldedhours"}).merge(sensors_row_count, how="left", left_index=True, right_index=True).reset_index()


if time_segments_type == "FREQUENCY":
    data_for_plot["local_segment_label"] = data_for_plot["local_segment_label"].str[:-4]
elif time_segments_type == "EVENT":
    data_for_plot["local_segment_label"] = "event"

sensor_names.extend(["ratiovalidyieldedminutes", "ratiovalidyieldedhours"])
html_file = open(snakemake.output[0], "a", encoding="utf-8")
for time_segment in set(data_for_plot["local_segment_label"]):
    if not data_for_plot.empty:
        data_for_plot_per_segment = data_for_plot[data_for_plot["local_segment_label"] == time_segment]
    if data_for_plot_per_segment.empty:
        html_file.write("There are no records of selected sensors in database for " + time_segment + " segments. Pid: " + pid + ". Label: " + label + ".<br>")
    else:
        data_for_plot_per_segment = data_for_plot_per_segment.reindex(columns=["local_segment", "local_segment_start_datetime", "local_segment_end_datetime"] + sensor_names).set_index(["local_segment", "local_segment_start_datetime", "local_segment_end_datetime"])
        # except for phone data yield sensor, scale each sensor (row) to the range of [0, 1]
        scaled_data_for_plot_per_segment = data_for_plot_per_segment.copy()
        scaled_data_for_plot_per_segment[sensor_names[:-2]] = scaled_data_for_plot_per_segment.fillna(np.nan)[sensor_names[:-2]].apply(lambda x: (x - np.nanmin(x)) / (np.nanmax(x) - np.nanmin(x)) if np.nanmax(x) != np.nanmin(x) else (x / np.nanmin(x)), axis=0)
        data_for_plot_processed = pd.concat([data_for_plot_per_segment.stack(dropna=False).to_frame("value"), scaled_data_for_plot_per_segment.stack(dropna=False).round(3).to_frame("scaled_value")], axis=1).reset_index().rename(columns={"level_3": "sensor"})
        getRowCountHeatmap(data_for_plot_processed, pid, time_segment, html_file)

html_file.close()
