import pandas as pd
import plotly.express as px
import yaml



def getPidAndLabel(participant_file_paths, pids):
    pid2label, y_axis_labels = {}, []
    for participant_file_path, pid in zip(participant_file_paths, pids):

        with open(participant_file_path, "r", encoding="utf-8") as f:
            participant_file = yaml.safe_load(f)
        label = str(participant_file["PHONE"]["LABEL"])

        pid2label[pid] = label
        y_axis_labels.append(pid + "." + label)
    return pid2label, y_axis_labels

def getPhoneDataYieldHeatmap(phone_data_yield, time, time_segment, html_file):

    if time == "RELATIVE_TIME":
        # Number of minutes after the first start date time of local segments
        phone_data_yield["local_segment_end_datetime"] = (phone_data_yield["local_segment_end_datetime"] - phone_data_yield["local_segment_start_datetime"].min()) + pd.Timestamp(2000,1,1)
        phone_data_yield["local_segment_start_datetime"] = (phone_data_yield["local_segment_start_datetime"] - phone_data_yield["local_segment_start_datetime"].min()) + pd.Timestamp(2000,1,1)

    for type in ["minutes", "hours"]:

        column_name = "phone_data_yield_rapids_ratiovalidyielded" + type

        fig = px.timeline(phone_data_yield,
                          x_start="local_segment_start_datetime",
                          x_end="local_segment_end_datetime",
                          y="y_axis_label",
                          color=column_name,
                          color_continuous_scale="Viridis",
                          range_color=[0, 1],
                          opacity=0.7,
                          hover_data={'local_segment_start_datetime':False, 'local_segment_end_datetime':False, 'local_segment':True})

        fig.update_layout(title="Heatmap of valid yielded " + type + " ratio for " + time_segment + " segments and " + time.lower().replace("_", " ") + ".<br>y-axis shows participant information (format: pid.label).<br>x-axis shows the time" + (" since their first segment" if time == "RELATIVE_TIME" else "") + ".<br>z-axis (color) shows valid yielded " + type + " ratio during a segment instance.",
                    xaxis=dict(side="bottom", title="Time Since First Segment" if time == "RELATIVE_TIME" else "Time"),
                    yaxis=dict(side="left", title="Participant information"),
                    margin=dict(t=160))

        if time == "RELATIVE_TIME":
            fig.update_layout(xaxis_tickformat="%y years %j days<br>%X")

        html_file.write(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    return html_file




pid2label, y_axis_labels = getPidAndLabel(snakemake.input["participant_files"], snakemake.params["pids"])
time_segments_type = snakemake.params["time_segments_type"] # FREQUENCY or PERIODIC or EVENT
time = snakemake.params["time"] # ABSOLUTE_TIME or RELATIVE_TIME
time_segments = pd.read_csv(snakemake.input["time_segments_file"])["label"].unique()

phone_data_yield = pd.read_csv(snakemake.input["phone_data_yield"], parse_dates=["local_segment_start_datetime", "local_segment_end_datetime"]).sort_values(by=["pid", "local_segment_start_datetime"])
if time_segments_type == "FREQUENCY":
    phone_data_yield["local_segment_label"] = phone_data_yield["local_segment_label"].str[:-4]

html_file = open(snakemake.output[0], "w", encoding="utf-8")
if phone_data_yield.empty:
    html_file.write("There is no sensor data for the sensors in [PHONE_DATA_YIELD][SENSORS].")
else:
    # Make sure the phone_data_yield file contains both "phone_data_yield_rapids_ratiovalidyieldedminutes" and "phone_data_yield_rapids_ratiovalidyieldedhours" columns
    if ("phone_data_yield_rapids_ratiovalidyieldedminutes" not in phone_data_yield.columns) or ("phone_data_yield_rapids_ratiovalidyieldedhours" not in phone_data_yield.columns):
        raise ValueError("Please make sure [PHONE_DATA_YIELD][RAPIDS][COMPUTE] is True AND [PHONE_DATA_YIELD][RAPIDS][FEATURES] contains [ratiovalidyieldedminutes, ratiovalidyieldedhours].")

    phone_data_yield.loc[:, ["phone_data_yield_rapids_ratiovalidyieldedminutes", "phone_data_yield_rapids_ratiovalidyieldedhours"]] = phone_data_yield.loc[:, ["phone_data_yield_rapids_ratiovalidyieldedminutes", "phone_data_yield_rapids_ratiovalidyieldedhours"]].round(3).clip(upper=1)
    phone_data_yield["y_axis_label"] = phone_data_yield["pid"].apply(lambda pid: pid + "." + str(pid2label[pid]))

    if time_segments_type == "EVENT":
        html_file = getPhoneDataYieldHeatmap(phone_data_yield, time, "event", html_file)
    else: # FREQUENCY or PERIODIC
        for time_segment in time_segments:
                        
            phone_data_yield_per_segment = phone_data_yield[phone_data_yield["local_segment_label"] == time_segment].copy()

            if not phone_data_yield_per_segment.empty:

                html_file = getPhoneDataYieldHeatmap(phone_data_yield_per_segment, time, time_segment, html_file)


html_file.close()
