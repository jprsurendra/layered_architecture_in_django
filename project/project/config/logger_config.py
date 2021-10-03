'''
Application logger configuration used in application
'''

import datetime

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        # 'default': {
        #     'level':'DEBUG',
        #     'class':'logging.handlers.RotatingFileHandler',
        #     'filename': 'logs/project_log.log',
        #     'maxBytes': 1024*1024*5, # 5 MB
        #     'backupCount': 5,
        #     'formatter':'standard',
        # },
        'default': {
            'level':'DEBUG',
            'class':'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/project_log.log',
            'when': 'midnight', # this specifies the interval
            'interval': 1, # defaults to 1, only necessary for other values
            #'backupCount': 10, # how many backup file to keep, 10 days
            'formatter':'standard', #'verbose',
        },

        'request_handler': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django_request.log',
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        },
        'background_task_handler': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': 'logs/process_tasks.log',
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter':'standard',
        },
        # 'console': {
        #     'level': 'DEBUG',
        #     # 'filters': ['require_debug_true'],
        #     'class': 'logging.StreamHandler',
        #     #'formatter': 'verbose'
        #     'formatter':'standard',
        # },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'DEBUG',
            'propagate': True
        },
        'django.request': {
            'handlers': ['request_handler'],
            'level': 'DEBUG',
            'propagate': False
        },
        'background_task.management.commands.process_tasks': {
            'handlers': ['background_task_handler'],
            'level': 'DEBUG',
            'propagate': False
        },
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'propagate': False,
        #     'level': 'DEBUG',
        # },

    }
}