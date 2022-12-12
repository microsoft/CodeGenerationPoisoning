from flask import render_template
from app import app
from google.cloud import bigquery
client = bigquery.Client()
from flask_table import Table, Col
table_id = "birdbackpacks.birdbackpacksdataset1.sensorOne"

class ItemTable(Table):
    device = Col('Device')
    light = Col('Light')
    timestamp = Col("Timestamp")


@app.route("/")
def index():
    rows_iter = client.list_rows(table_id)

    # Specify selected fields to limit the results to certain columns.
    table = client.get_table(table_id)  # Make an API request.
    fields = table.schema[:3]  

    rows = list(rows_iter)
    items = []
    for row in rows:
        current_row = list(row.items())
        current_row_name = current_row[0][1]
        val = current_row[1][1]
        timestamp = current_row[2][1].strftime("%b %d %Y %H:%M:%S")
        items.append(dict(device=current_row_name, light = val, timestamp=timestamp))

    table = ItemTable(items, classes = ["table", "text-center"])
    return render_template("index.html", table=table)
