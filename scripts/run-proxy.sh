#!/bin/sh


pip install -r requirements-test.txt
# pip install -e .

FLASK_ENV=development FLASK_APP=camnode.honeycombproxy flask run --host=0.0.0.0
