# import os
# from django.utils.translation import ugettext_lazy as _
# DEBUG = True
# LOCAL_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

USE_I18N = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'fm_db_20211015_1_02',
        'OPTIONS': {
            # 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER'",
            'charset': 'utf8'
        },
        'USER': 'root',
        'PASSWORD': '*******',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}









