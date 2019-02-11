from camnode.workers import app


@app.task(name="honeycomb-send-data")
def send_data(assignment_id, parent_data_point_id, data, callback=None):
    pass
