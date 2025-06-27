#!/bin/bash
gunicorn -w 1 -b 0.0.0.0:$PORT flask_bot_app:app