import traceback
import logging

from django.shortcuts import render
# Create your views here.


def error_404(request):
	'''
	It is 404 customize page.
	Use this method with handler if we need to customize page from backend.
	'''
	data = {}
	return render(request,'common/404.html', data)

def load_on_startup():
	try:
		# print("Something....")
		# raise Exception("This is a sample Exception!")

		from apis.components.factories.managers_factory import ManagersFactory
		ManagersFactory.get_instance().register_all_managers()
	except Exception as e:
		logging.info("Path: project/views.py Source: load_on_startup() Error: %s", str(e))
		logging.info(traceback.format_exc())
