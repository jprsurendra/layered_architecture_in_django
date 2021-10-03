import sys
import traceback
import logging

from django.shortcuts import render




# Create your views here.

def demo_function():
    try:
        print("Something....")
    except Exception as e:
        logging.info("Path: main/views.py Source: demo() Error: %s", str(e))
        logging.info(traceback.format_exc())