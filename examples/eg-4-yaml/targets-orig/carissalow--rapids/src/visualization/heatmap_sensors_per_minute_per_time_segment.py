import pandas as pd
import numpy as np
import plotly.graph_objects as go
from importlib import util
from pathlib import Path
import yaml

# import filter_data_by_segment from src/features/utils/utils.py
spec = util.spec_from_file_location("util", str(Path(snakemake.scriptdir).parent / "features" / "utils" / "utils.py"))
mod = util.module_from_spec(spec)
spec.loader.exec_module(mod)
filter_data_by_segment = getattr(mod,  "filter_data_by_segment")

def colors2colorscale(colors):
    colorscale = []
    length = len(colors)
    for i in range(length):
        if i != length - 1:
            colorscale = colorscale + [[i/(length-1), colors[i]], [(i+1)/(length-1), colors[i]]]
        else:
            colorscale.append([1, colors[i]])
    return colorscale

def getDataForPlot(phone_data_yield_per_segment):
    # calculate the length (in minute) of per segment instance
    phone_data_yield_per_segment["length"] = phone_data_yield_per_segment["timestamps_segment"].str.split(",").apply(lambda x: int((int(x[1])-int(x[0])) / (1000 * 60)))
    # extract local start datetime of the segment from "local_segment" column
    phone_data_yield_per_segment["local_segment_start_datetimes"] = pd.to_datetime(phone_data_yield_per_segment["local_segment"].apply(lambda x: x.split("#")[1].split(",")[0]))
    # calculate the number of minutes after local start datetime of the segment
    phone_data_yield_per_segment["minutes_after_segment_start"] = ((phone_data_yield_per_segment["local_date_time"] - phone_data_yield_per_segment["local_segment_start_datetimes"]) / pd.Timedelta(minutes=1)).astype("int")
    # calculate the number of sensors logged at least one row of data per minute.
    phone_data_yield_per_segment = phone_data_yield_per_segment.groupby(["local_segment", "length", "local_segment_start_datetimes", "minutes_after_segment_start"])[["sensor"]].max().reset_index()
    
    # impute missing rows with 0
    columns_for_full_index = phone_data_yield_per_segment[["local_segment_start_datetimes", "length"]].drop_duplicates(keep="first")
    columns_for_full_index = columns_for_full_index.apply(lambda row: [[row["local_segment_start_datetimes"], x] for x in range(row["length"] + 1)], axis=1)
    full_index = []
    for columns in columns_for_full_index:
        full_index = full_index + columns
    full_index = pd.MultiIndex.from_tuples(full_index, names=("local_segment_start_datetimes", "minutes_after_segment_start"))
    phone_data_yield_per_segment = phone_data_yield_per_segment.set_index(["local_segment_start_datetimes", "minutes_after_segment_start"]).reindex(full_index).reset_index().fillna(0)
    
    # transpose the dataframe per local start datetime of the segment and discard the useless index layer
    phone_data_yield_per_segment = phone_data_yield_per_segment.groupby("local_segment_start_datetimes")[["minutes_after_segment_start", "sensor"]].apply(lambda x: x.set_index("minutes_after_segment_start").transpose())
    phone_data_yield_per_segment.index = phone_data_yield_per_segment.index.get_level_values("local_segment_start_datetimes")
    return phone_data_yield_per_segment

def getSensorsPerMinPerSegmentHeatmap(phone_data_yield, pid, label, time_segment, html_file):
    if phone_data_yield.empty:
        html_file.write("There is no sensor data of " + time_segment + " segments for "  + pid + " (pid) and " + label + " (label).<br>")
    else:
        phone_data_yield.sort_index(inplace=True)
        x_axis_labels = [pd.Timedelta(minutes=x) for x in phone_data_yield.columns]
        
        fig = go.Figure(data=go.Heatmap(z=phone_data_yield.values.tolist(),
                                        x=x_axis_labels,
                                        y=phone_data_yield.index,
                                        zmin=0, zmax=16,
                                        colorscale=colors2colorscale(colors),
                                        colorbar=dict(thickness=25, tickvals=[1/2 + x for x in range(16)],ticktext=[x for x in range(16)])))
        
        fig.update_layout(title="Number of sensors with any data per minute for " + time_segment + " segments. Pid: "+pid+". Label: " + label + "<br>y-axis shows the start (date and time) of a time segment.<br>x-axis shows the time since the start of the time segment.<br>z-axis (color) shows how many sensors logged at least one row of data per minute.")
        fig["layout"].update(margin=dict(t=160))
        
        html_file.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    return



colors = ["red", "#3D0751", "#423176", "#414381", "#3F5688", "#42678B", "#42768C", "#45868B", "#4A968A", "#53A485", "#5FB57E", "#76C170", "#91CF63", "#B4DA55", "#D9E152", "#F8E755", "#DEE00F"]
pid = snakemake.params["pid"]
time_segments_type = snakemake.params["time_segments_type"]
time_segments_labels = pd.read_csv(snakemake.input["time_segments_labels"])

with open(snakemake.input["participant_file"], "r", encoding="utf-8") as f:
    participant_file = yaml.safe_load(f)
label = participant_file["PHONE"]["LABEL"]

phone_data_yield = pd.read_csv(snakemake.input["phone_data_yield"], parse_dates=["local_date_time"])
if time_segments_type == "FREQUENCY":
    phone_data_yield["assigned_segments"] = phone_data_yield["assigned_segments"].str.replace(r"[0-9]{4}#", "#")
    time_segments_labels["label"] = time_segments_labels["label"].str[:-4]
if time_segments_type == "PERIODIC":
    phone_data_yield["assigned_segments"] = phone_data_yield["assigned_segments"].str.replace(r"_RR\d+SS#", "#")
    time_segments_labels["label"] = time_segments_labels["label"].str.replace(r"_RR\d+SS$", "")

html_file = open(snakemake.output[0], "a", encoding="utf-8")
if phone_data_yield.empty:
    html_file.write("There is no sensor data for " + pid + " (pid) and " + label + " (label).")
else:
    data_for_plot = pd.DataFrame()
    for time_segment in set(time_segments_labels["label"]):
        phone_data_yield_per_segment = filter_data_by_segment(phone_data_yield, time_segment)
        if not phone_data_yield_per_segment.empty:
            data_for_plot_per_segment = getDataForPlot(phone_data_yield_per_segment)
            if time_segments_type == "EVENT":
                data_for_plot = pd.concat([data_for_plot, data_for_plot_per_segment], axis=0)
            else:
                getSensorsPerMinPerSegmentHeatmap(data_for_plot_per_segment, pid, label, time_segment, html_file)
    if time_segments_type == "EVENT":
        getSensorsPerMinPerSegmentHeatmap(data_for_plot, pid, label, "event", html_file)

html_file.close()
