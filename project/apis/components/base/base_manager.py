import logging
import traceback
import uuid

from django.apps import apps
from django.db.models import Subquery
from django.core.paginator import Paginator

from apis.common.utils import find_in_dic_or_list, Base64EncodeDecode
from django.db import connection, transaction

class BaseManager(object):

    def __init__(self):
        pass

    @staticmethod
    def getManagerName():
        raise NotImplemented()

    def getErrorInfo(self, errors_info = {}, error_code='UNKNOWN_ERROR', description='An unknown error has occurred , Please contact your customer care', error_no=1):
        err_no=0
        if errors_info and isinstance(errors_info, dict):
            if not 'errors' in errors_info:
                errors_info['errors'] = []
            if not 'error_no' in errors_info:
                errors_info['error_no'] = 0
        else:
            errors_info = {'errors': [], 'error_no':0}

        errors = errors_info['errors']
        err_no = int(errors_info['error_no'])

        if error_code:
            if not description:
                description = " "
            errors.append({'error_code': error_code, 'description': description})
            errors_info['errors'] = errors
            if err_no<error_no:
                errors_info['error_no'] = error_no
        return errors_info

    def server_side_validation(self, params_pk, params=None, **kwargs):
        return True

    def retrive(self, pk, params=None, **kwargs):
        raise NotImplemented()

    def fetch(self, params=None, **kwargs): # def fetch(self, *args, **kwargs):
        raise NotImplemented()

    def exists(self, params=None, **kwargs): # def exists(self, *args, **kwargs):
        raise NotImplemented()

    def save_or_update(self, params=None, *args, **kwargs):
        raise NotImplemented()

    def create(self, params=None, **kwargs):
        raise NotImplemented()

    def update(self, pk, params=None, **kwargs):
        raise NotImplemented()

    def delete(self, pk, params):
        raise NotImplemented()

    def get_additional_params(self, params = {}, request_params=None, **kwargs):
        return params

    '''
        Description: This is utility method, which will combine all category of parameters.
        Parameters: 
            1. request_params (Dic): It contains different types of data e.g. 'query_params', 'request_params', 'logged_in_user'.  
        Returns:    Dic of combined all category of parameters  
        Exception:  None
    '''
    def get_all_request_params(self, request_params=None, **kwargs):
        params = {}
        # request_params = request_params.copy() if request_params else {}
        for key in ['query_params', 'request_params', 'logged_in_user', 'additional_parameters']:
            if key in request_params and request_params[key]:
                if isinstance(request_params[key], dict):
                    params.update(request_params[key])
                else:
                    params[key] = request_params[key]
        return self.get_additional_params(params=params, request_params=request_params, **kwargs)




class BaseModelManager(BaseManager):
    '''
        Description: Common Functionality for all Managers at the time of object initialization.
            In this method, common_manager also assign, where you can write common code related to your Business-Logic
            or any Database related code without Managers.
        Parameters:
            app_name (String): Name of App
            model_name (String): Name of Model in the App
        Returns: None
        Exception: None
    '''
    def __init__(self, app_name, model_name):
        self.context = {}
        if app_name==None or model_name == None:
            self.Model = None
        else:
            self.Model = apps.get_model(app_name, model_name)
        
        try:
            from apis.common.managers import CommonManager
            if not isinstance(self, CommonManager):
                from apis.components.factories.managers_factory import ManagersFactory
                self.common_manager = ManagersFactory.get_instance().get_common_manager()
            else:
                self.common_manager = None
        except Exception as e:
            self.common_manager = None
            logging.info("Path apis/common/components/base_manager.py  Class: BaseModelManager Method: __init__  Error: %s"%(str(e)))
            logging.info(traceback.format_exc())

    @staticmethod
    def get_first_occurrence(dictionary: dict, key: str):
        value_found = None
        for k, v in dictionary.items():
            if key in dictionary:
                return dictionary[key]
            elif isinstance(v, dict):
                value_found = BaseModelManager.get_first_occurrence(v, key)

        if isinstance(value_found, list):
            return value_found[0]
        else:
            return value_found

    def get_dic_item(self, obj_dic, key, default_value = None, do_trim=False):
        dic_item = obj_dic.get(key, default_value)
        if do_trim:
            dic_item = dic_item.strip() if dic_item else dic_item
        return dic_item

    '''
        Description: implementation of this method in all Managers is mandatory. This method return unique names of 
            your Manager, this name used for register/retrieve your Manager into/from Manager-Factory.
        Parameters:None
        Returns: (String) Unique-Names of your Manager
        Exception: None
    '''
    @staticmethod
    def get_manager_name():
        raise NotImplemented()

    def is_int(self, val):
        try:
            if type(val) == int:
                return True
            else:
                if val.is_integer():
                    return True
                else:
                    return False
        except Exception as e:
            return False

    def execute_raw_query(self, raw_query, list_of_column_index = None):
        with connection.cursor() as cursor:
            cursor.execute(raw_query)
            exclude_sql = cursor.fetchall()
            # if list_of_column_index == None:
            #     pass
            # elif type(list_of_column_index) is list or type(list_of_column_index) is tuple:
            #     list_of_column_values = []
            #     if len(exclude_sql)>1:
            #         for row in exclude_sql:
            #             list_of_column_values.append([row[k] for k in list_of_column_index])
            #     else:
            #         row = exclude_sql
            #         list_of_column_values.append([row[k] for k in list_of_column_index])
            #     return list_of_column_values
            # elif self.is_int(list_of_column_index): # Fetch only first column
            #     if len(exclude_sql)>1:
            #         list_of_column_values = [int(k[list_of_column_index]) for k in exclude_sql]
            #     else:
            #         list_of_column_values =[exclude_sql[0][list_of_column_index]]
            #     return list_of_column_values
            if list_of_column_index: # Fetch only first column (as a prymary key)
                if len(exclude_sql)>1:
                    list_of_column_values = [int(k[0]) for k in exclude_sql]
                else:
                    list_of_column_values =[exclude_sql[0][0]]
                return list_of_column_values
            return exclude_sql

    '''
        Description: This method return all fields of Model bind with Manager
        Parameters:None
        Returns: List<String>
        Exception: None
    '''
    def model_fields(self):
        model_fields = []
        for field in self.Model._meta.fields:
            model_fields.append(field.name)
        return model_fields

    '''
        Description: This method return select query ("Select * FROM table_name") of Model bind with Manager
        Parameters:None
        Returns: String
        Exception: None
    '''
    def get_native_select_query(self, fields=None, where_close = ""):
        table_name = self.Model._meta.db_table
        if fields:
            return "SELECT " + fields + " FROM " + table_name + " " + where_close
        else:
            return "SELECT * FROM " + table_name + " " + where_close

    '''
        Description: This method return select query ("Select * FROM table_name") of Model bind with Manager
        Parameters:None
        Returns: String
        Exception: None
    '''

    def execute_native_query(self, raw_query ):
        result = None
        try:
            with connection.cursor() as cursor:
                cursor.execute(raw_query);
                result = cursor.fetchall()
            return result
        except self.Model.DoesNotExist:
            return None

    '''
        Description: This method return select query ("Select * FROM table_name") of Model bind with Manager
        Parameters:None
        Returns: String
        Exception: None
    '''
    def execute_update_native_query(self, raw_query):
        result = None
        try:
            with connection.cursor() as cursor:
                cursor.execute(raw_query)
                connection.commit()
            return result
        except self.Model.DoesNotExist:
            return None

    def execute_raw_query_with_model(self, raw_query, raw_count_query=None, app_name=None, model_name=None, RowSqlModel=None):
        if RowSqlModel:
            LocalModel = RowSqlModel
        else:
            LocalModel = self.get_model(app_name, model_name)

        return LocalModel.objects.raw(raw_query, raw_count_query)

    '''
        Description: This method return primary field-name of Model bind with Manager
        Parameters:None
        Returns: String
        Exception: None
    '''
    def get_pk_field_name(self):
        pk_field_name = self.Model._meta.pk.name
        return pk_field_name

    def get_model(self, app_name=None, model_name=None):
        if app_name == None and model_name == None:
            LocalModel = self.Model
        elif app_name == None or model_name == None:
            raise ValueError("Invalid arguments (app_name and model_name)")
        else:
            LocalModel = apps.get_model(app_name, model_name)

        return LocalModel

    def get_model_fields(self, app_name=None, model_name=None, obj_entity_model=None):
        if obj_entity_model:
            LocalModel = obj_entity_model
        else:
            LocalModel = self.get_model(app_name, model_name)

        return [f.name for f in LocalModel._meta.get_fields()]


    def get_manager_param_dict(self, **kwargs):
        request_params = { }
        if kwargs:
            for key, value in kwargs.items():
                if value:
                    request_params[key] = value
        v_params = {}
        v_params['request_params'] = request_params
        return v_params

    '''
        Description: This method use for parsing nested data-dic which will used in Serializer. 
        Parameters:
            kwargs (**): data which will parse
        Returns: 
            1. data-dic of outer object
            2. data-dic of inner object
        Exception: None
    '''
    def parse_nested_obj_dic(self, **kwargs):
        service_data = {}
        nested_obj_dic = {}
        for key, value in kwargs.items():
            if isinstance(value, dict):
                nested_obj_dic[key] = kwargs[key]
            else:
                service_data[key] = kwargs[key]

        return service_data, nested_obj_dic

    '''
        Description: This method return Manager's object, based on provided search_key.
            Remember that, generally this search_key is a name of nested field in Serializer
        Parameters: None
        Returns:    object of Manager
        Exception:  None
    '''
    def get_manager(self, search_key):
        from apis.components.factories.managers_factory import ManagersFactory
        manager = ManagersFactory.get_instance().get_manager(managerName=search_key)
        return manager

    '''
        Description: This is a service-method use for retrieve data from database based on different-criteria. 
        Parameters: 
            1. id_value (int): if value of id_value provied then Id based database-query will execute.
            2. params (Dic): Controller can share additional data in this dictionary.
            3. kwargs (**):  additional parameters for search data
        Returns:    single object or None (if not found in Database)
        Exception:  None
    '''
    def retrieve(self, id_value=None, params=None, **kwargs):
        try:
            if id_value:
                obj = self.Model.objects.filter(id = id_value)

                return obj[0] if obj else None
            else:
                obj = self.Model.objects.get(**kwargs)
                return obj
        except self.Model.DoesNotExist:
            return None

    '''
        Description: This service-method is similar to "retrieve" but it may be return list of one or more result.
        Parameters:  
            1. params (Dic): Controller can share additional data in this dictionary.
            2. kwargs (**):  additional parameters for search data
        Returns:    List of objects
        Exception:  None
    '''
    def fetch(self, params=None, **kwargs): # def fetch(self, *args, **kwargs):
        lst_obj = self.Model.objects.filter(**kwargs)
        return lst_obj
        # queryset = self.Model.objects.filter(**kwargs)
        # return self.queryset_sorting(queryset, query_params=params, method='list', **kwargs)

    '''
        Description: This service-method checks whether data exist in data or not.
        Parameters:  
            1. params (Dic): Controller can share additional data in this dictionary.
            2. kwargs (**):  additional parameters for search data
        Returns:    True or False
        Exception:  None
    '''
    def exists(self, params=None, **kwargs): # def exists(self, *args, **kwargs):
        return self.Model.objects.filter(**kwargs).exists()

    def event_before_save(self, params=None, *args, **kwargs):
        return params, args, kwargs
    '''
        Description: This service-method create or update the Model.
        Parameters:  
            1. params (Dic): Controller can share additional data in this dictionary.
            2. args (*): Controller can share additional list of parameters in this.
            3. kwargs (**):  additional parameters for search data
        Returns:    object of Model
        Exception:  None
    '''
    def save_or_update(self, params=None, *args, **kwargs):
        service_data, nested_obj_dic = self.parse_nested_obj_dic(**kwargs)
        if nested_obj_dic:
            for key, value in nested_obj_dic.items():
                manager = self.get_manager(key)
                inner_obj = manager.save(params=params, **value)
                service_data[key] = inner_obj
            params, args, updated_service_data = self.event_before_save(params, *args, **service_data)
            obj = self.save(params, *args, **updated_service_data)
        else:
            params, args, updated_kwargs = self.event_before_save(params, *args, **kwargs)
            if 'id' in updated_kwargs:
                rows_updated = self.update(updated_kwargs['id'], params, *args, **updated_kwargs)
                obj = self.Model(**updated_kwargs)
            else:
                obj = self.create(params, *args, **updated_kwargs)

        return obj

    def event_before_create(self, params=None, *args, **kwargs):
        return params, args, kwargs

    '''
        Description: This service-method create/Insert the Model into database.
        Parameters:  
            1. params (Dic): Controller can share additional data in this dictionary. 
            2. kwargs (**):  additional parameters for search data
        Returns:    object of Model
        Exception:  None
    '''
    def create(self, params=None, *args, **kwargs):
        
        service_data, nested_obj_dic = self.parse_nested_obj_dic(**kwargs)
        if nested_obj_dic:
            for key, value in nested_obj_dic.items():
                manager = self.get_manager(key)
                inner_obj = manager.create(params=params, **value)
                service_data[key] = inner_obj
            params, args, updated_service_data = self.event_before_create(params, *args, **service_data)
            obj = self.Model.objects.create(**updated_service_data)
        else:
            params, args, updated_kwargs = self.event_before_create(params, *args, **kwargs)
            obj = self.Model.objects.create(**updated_kwargs)

        return obj

    def event_before_update(self, pk, params=None, *args, **kwargs):
        return params, args, kwargs

    '''
        Description: This service-method update the Model into database.
        Parameters:  
            1. pk (int): prymary-key's value, used to retrieve object of Model from database. 
            2. params (Dic): Controller can share additional data in this dictionary. 
            2. kwargs (**):  key-value data for update value in database
        Returns:    no of rows updated in database
        Exception:  None
    '''
    def update(self, pk, params=None, *args, **kwargs):
        params, args, updated_kwargs = self.event_before_update(pk, params, *args, **kwargs)
        # self.Model(**updated_kwargs)
        updated_rows = self.Model.objects.filter(id = pk).update(**updated_kwargs)
        # updated_rows = self.Model.objects.get(id=pk).update(**updated_kwargs)
        return updated_rows

    def update_object(self, pk, params=None, *args, **kwargs):
        params, args, updated_kwargs = self.event_before_update(pk, params, *args, **kwargs)
        # self.Model(**updated_kwargs)
        updated_rows = self.Model.objects.filter(id = pk).update(**updated_kwargs)
        return  self.Model.objects.get(id = pk), updated_rows


    '''
        Description: This service-method update the Model into database.
        Parameters:  
            1. id_value (int): prymary-key's value, used to retrieve object of Model from database for deletion. 
            2. params (Dic): Controller can share additional data in this dictionary. 
            3. kwargs (**):  additional parameters for search objects of Model from database for deletion. 
        Returns:    no of rows deleted from database
        Exception:  None
    '''
    def delete(self, id_value=None, params=None, **kwargs):
        if id_value:
            return self.Model.objects.filter(id = id_value).delete()
        elif kwargs:
            return self.Model.objects.filter(**kwargs).delete()

    '''
        Description: This utility-method add filters(include/exclude) on queryset without Manager.
        Parameters:  
            1. db_model (object):object of Model. 
            2. include_params (Dic): include filters parameters. 
            3. exclude_params (Dic): exclude filters parameters. 
            4. kwargs (**):  additional parameters for search objects of Model from database. 
        Returns:    no of rows deleted from database
        Exception:  None
    '''
    def filter_on_model(self, db_model, include_params={}, exclude_params={}, **kwargs):
        if include_params:
            lst_queryset = db_model.objects.filter(**include_params)
        elif kwargs:
            lst_queryset = db_model.objects.filter(**kwargs)
        else:
            lst_queryset = db_model.objects.all()

        if exclude_params:
            lst_queryset = lst_queryset.exclude(**exclude_params)

        return lst_queryset

    '''
        Description: This utility-method add filters(include/exclude) on Model bind with Manager.
        Parameters:  
            1. include_params (Dic): include filters parameters. 
            2. exclude_params (Dic): exclude filters parameters. 
            3. kwargs (**):  additional parameters for search objects of Model from database. 
        Returns:    no of rows deleted from database
        Exception:  None
    '''
    def filter(self, include_params={}, exclude_params={}, **kwargs):
        return self.filter_on_model( db_model=self.Model, include_params=include_params, exclude_params=exclude_params, **kwargs)

    '''
        Description: This demo-method to show how to add filter (named 'xyz'). you can replace 'xyz' with your filter name
        Parameters:  
            1. value (String): filter with this value. 
            2. queryset : filter will add on this queryset
            3. request_params(Dic): Controller/Manager can share additional data in this dictionary. 
        Returns:    queryset after add filter
        Exception:  None
    '''
    def filter_xyz(self, value, queryset, request_params=None):
        return queryset

    '''
        Description: This is will call before all filters, you can say this is first filter method.
        Parameters:   
            1. queryset : filter will add on this queryset
            2. request_params(Dic): Controller/Manager can share additional data in this dictionary. 
        Returns:    queryset after add filter
        Exception:  None
    '''
    def filter_startfiltering(self,  queryset, request_params=None):
        if request_params:
            filter_session_key = uuid.uuid1()
            request_params['filter_session_key'] = filter_session_key
            self.context[filter_session_key] = {}
        return queryset

    '''
        Description: This is will call after all filters, you can say this is lst filter method.
        Parameters:   
            1. queryset : filter will add on this queryset
            2. request_params(Dic): Controller/Manager can share additional data in this dictionary. 
        Returns:    queryset after add filter
        Exception:  None
    '''
    def filter_endfiltering(self, queryset, request_params=None):
        return queryset

    '''
        Description: This is will call after all filters, you can handel sorting in this method.
        Parameters:   
            1. queryset : filter will add on this queryset
            2. query_params (Dic): you can provides order_by fields in this dictionary. 
            3. method (String): when this method auto call, can you be identified by your service_method name.
            4. kwargs (**):  additional parameters for search objects of Model from database. (Not used till Now)
        Returns:    queryset  
        Exception:  None
    '''
    def queryset_sorting(self, queryset, query_params=None, method='list', **kwargs):
        if 'order_by' in query_params:
            for order_by in query_params['order_by'].split(','):
                queryset = queryset.order_by(order_by)
        return queryset

    def event_before_filter(self, name, value, queryset, request_params=None):
        if name not in ['order_by', 'service_method', 'fields', 'page', 'page_size', 'logged_in_user', 'filter_session_key']:
            return queryset
        else:
            return None
    #def filter_domain_name(self, value, queryset, request_params=None):
    def clear_filter_session(self, query_params):
        try:
            if 'filter_session_key' in query_params:
                filter_session_key = query_params['filter_session_key']
                if filter_session_key in self.context:
                    del (self.context[filter_session_key])
        except Exception as e:
            pass
    def apply_filters(self, queryset, query_params=None, method='list', select_related_fields=[], **kwargs):
        filter_dict = {}
        try:
            queryset = self.filter_startfiltering(queryset, request_params=query_params)
            if query_params:
                for query_param_key in query_params.keys() :
                    q = self.event_before_filter(name=query_param_key, value=query_params[query_param_key], queryset=queryset, request_params=query_params)
                    if q : #query_param_key not in ['order_by', 'service_method', 'page', 'page_size', 'logged_in_user']:
                        queryset = q
                        if hasattr(self.__class__, 'filter_%s' % (query_param_key)) and \
                                callable(getattr(self.__class__, 'filter_%s' % (query_param_key))):
                            queryset = getattr(self, 'filter_%s' % (query_param_key))(query_params[query_param_key], queryset, query_params)
                        # else:
                        #     filter_dict[query_param_key] = query_params[query_param_key]

                if filter_dict:
                    queryset = queryset.filter(**filter_dict)

            queryset = self.filter_endfiltering(queryset, request_params=query_params)

            queryset = self.queryset_sorting(queryset, query_params=query_params, method=method, **kwargs)
            self.clear_filter_session(query_params)
            return queryset
        except Exception as e:
            self.clear_filter_session(query_params)
            e.args = (e.args if e.args else tuple()) + ('Error in filters',)
            raise    # re-raise current exception


    '''
        Description: This is utility method, which will actual implantation of filters.
        Parameters: 
            1. query_params (Dic): you can provides order_by fields in this dictionary. 
            2. method (String): when this method auto call, can you be identified by your service_method name.
            3. select_related_fields (List): parameters for Model.objects.select_related()
            4. kwargs (**):  additional parameters for search objects of Model from database. (Not used till Now)
        Returns:    queryset  
        Exception:  None
    '''
    def get_queryset(self, query_params=None, method='list', select_related_fields=[], **kwargs):
        if select_related_fields:
            queryset = self.Model.objects.select_related(select_related_fields)
        else:
            queryset = self.Model.objects.all()
        return self.apply_filters(queryset, query_params, method, select_related_fields, **kwargs)


    def log_sql(self, queryset, msg=' ==> ', params=None, **kwargs):
        try:
            msg_query = ""
            if 'service_method' in params:
                msg_query = msg_query + 'params[service_method]: %s' % (params['service_method'])
            if 'service_method' in kwargs:
                msg_query = msg_query + '    kwargs[service_method]: %s' % (kwargs['service_method'])
            sql_query = str(queryset.query)
            sql_parts = sql_query.split("FROM")
            del (sql_parts[0])
            sql_query = "FROM".join(sql_parts)
            # sql_query = sql_query.split("FROM")[1]
            if msg:
                msg_query = msg_query + ' '+ msg + ' SELECT * FROM ' + sql_query
            else:
                msg_query = msg_query + ' ==> SELECT * FROM ' + sql_query
            logging.info(msg_query)
        except Exception as e:
            pass

    '''
        Description: This is a service-method use for retrieve list of data (with pagination data) from database 
            based on different-criteria. 
        Parameters:  
            1. params (Dic): Controller can share additional data in this dictionary.
            2. kwargs (**):  additional parameters for search data
        Returns:    list of object
        Exception:  None
    '''
    def list_by_queryset(self, queryset, query_params):
        if 'page_size' in query_params or 'page' in query_params :
            items_per_page = int(query_params.get('page_size', 10))
            current_page = int(query_params.get('page', 1))

            paginator = Paginator(queryset, items_per_page)
            page = paginator.page(current_page)
            objects = page.object_list  # len(paginator(current_page).object_list

            total_count = paginator.count #(items_per_page * current_page + 1) + len(objects) #paginator(current_page).object_list)
            previous_url = False
            next_url = False
            if (current_page * items_per_page) < total_count:
                next_url = True
            if current_page > 1:
                previous_url = True

            result= {
                    'page_info' : { 'num_pages': paginator.num_pages,
                                    'start_count': items_per_page * (current_page-1)+1 ,
                                    # start_value = (int(query_params.get('page')) * page_size) - page_size
                                    'end_count': (items_per_page * (current_page-1))+1 + len(objects), #(items_per_page * current_page + 1) + len(paginator(current_page).object_list)
                                    # end_value = start_value + page_size
                                    'current_page': current_page,
                                    'items_per_page': items_per_page,
                                    'next_url': next_url,
                                    'previous_url':previous_url
                                   },
                    'data' : objects, # result_data = queryset[start_value:end_value]
                    'count': total_count,
                    'pagination': True
                    }
        else:
            result = { 'count': len(queryset), 'data': queryset, 'pagination': False }
            # data = [model_to_dict(model_row) for model_row in queryset]

        return result

    def get_raw_query_params(self, params=None, **kwargs):
        dict_params = { 'raw_query': None,
                        'raw_count_query': None,
                        'app_name': None,
                        'model_name': None,
                        'fields': None }
        return dict_params

    def row_query_filters(self, raw_query_params, params=None, **kwargs):
        return ""

    def build_raw_sql(self, raw_query_params, params=None, **kwargs):
        return raw_query_params.get('raw_query', None)

    def build_raw_sql_with_filters(self, raw_query_params, params=None, **kwargs):
        base_raw_query = self.build_raw_sql(raw_query_params=raw_query_params, params=params, **kwargs)
        if base_raw_query:
            base_raw_query = base_raw_query + " " + self.row_query_filters(raw_query_params=raw_query_params, params=params, **kwargs)
        # print("build_raw_sql_with_filters --> raw_query: ", base_raw_query)
        return base_raw_query


    '''
    Please do not delete it, This is a Sample override function "build_raw_sql_model_info"
    
    def build_raw_sql_model_info(self, raw_query_params, params=None, **kwargs):
		sql_cols = "id, field_1, field_2, field_3," 

		raw_query_params['fields'] = [field.strip() for field in sql_cols.split(",")]
		raw_query_params['app_name'] = 'quotationapis'
		raw_query_params['model_name'] = "QuotationListingModel"

		# raw_query_params['Model'] = self.get_model(raw_query_params['app_name'], raw_query_params['model_name'])
		# raw_query_params['fields'] = self.get_model_fields(obj_entity_model=raw_query_params['Model'])		 

		return raw_query_params
    '''

    def build_count_raw_sql(self, raw_query_params, base_raw_query=None, params=None, **kwargs):
        return raw_query_params.get('raw_count_query', None)

    def get_row_query_model_info(self, raw_query_params, params=None, **kwargs):
        tmp_raw_query_params = dict(raw_query_params)
        if kwargs.get('model_name', None):
            tmp_raw_query_params['model_name'] = kwargs.get['model_name']
        elif tmp_raw_query_params.get('model_name', None) == None:
            tmp_raw_query_params['model_name'] = self.Model._meta.model_name

        if kwargs.get('app_name', None):
            tmp_raw_query_params['app_name'] = kwargs.get['app_name']
        elif tmp_raw_query_params.get('app_name', None) == None:
            tmp_raw_query_params['app_name'] = self.Model._meta.app_label

        LocalModel = apps.get_model(tmp_raw_query_params['app_name'], tmp_raw_query_params['model_name'])
        tmp_raw_query_params['fields'] = self.get_model_fields(obj_entity_model=LocalModel)
        tmp_raw_query_params['Model']= LocalModel

        return tmp_raw_query_params

    def set_order_by_in_row_query(self, raw_query_params, base_raw_query, sql_cols, params=None, **kwargs):
        raw_query_params['raw_query'] = 'SELECT %s FROM (%s) AS t ORDER BY id DESC ' % ( sql_cols, raw_query_params['raw_query'])
        raw_query_params['raw_count_query'] = self.build_count_raw_sql(raw_query_params, base_raw_query=base_raw_query, params=params, **kwargs)
        return raw_query_params

    def get_queryset_by_row_query(self, params=None, **kwargs):
        raw_query_params = self.get_raw_query_params(params=params, **kwargs)
        base_raw_query = self.build_raw_sql_with_filters(raw_query_params=raw_query_params, params=params, **kwargs)
        raw_query_params['raw_query'] = base_raw_query

        if kwargs.get('use_row_query', False) or base_raw_query:
            raw_query_params['raw_query'] = base_raw_query

            if hasattr(self.__class__, 'build_raw_sql_model_info' ) and callable(getattr(self.__class__, 'build_raw_sql_model_info' )):
                raw_query_params = getattr(self, 'build_raw_sql_model_info' )(raw_query_params, params, **kwargs)
                if raw_query_params.get('Model', None)==None:
                    LocalModel = apps.get_model(raw_query_params['app_name'], raw_query_params['model_name'])
                    raw_query_params['Model'] = LocalModel
            else:
                raw_query_params = self.get_row_query_model_info(raw_query_params, params=None, **kwargs)

            LocalModel = raw_query_params.pop('Model', None)
            sql_cols = ','.join(raw_query_params['fields'])


            # raw_query_params['raw_query'] = 'SELECT %s FROM (%s) AS t ORDER BY id DESC ' % (sql_cols, raw_query_params['raw_query'])
            # raw_query_params['raw_count_query'] = self.build_count_raw_sql(raw_query_params, base_raw_query=base_raw_query, params=params, **kwargs)
            raw_query_params = self.set_order_by_in_row_query(raw_query_params, base_raw_query, sql_cols, params=params, **kwargs)
            if raw_query_params['raw_count_query'] == None:
                raw_query_params['raw_count_query'] = 'SELECT count(*) FROM (%s) AS t ' % (base_raw_query)

            # print("Final Row SQL :: ", raw_query_params.get('raw_query', None))
            queryset = self.execute_raw_query_with_model(raw_query=raw_query_params.get('raw_query', None),
                                                         raw_count_query=raw_query_params.get('raw_count_query', None),
                                                         RowSqlModel = LocalModel)
                                                         # app_name=raw_query_params.get('app_name', None),
                                                         # model_name=raw_query_params.get('model_name', None))
            return queryset
        else:
            return None

    def list(self, params=None, **kwargs):
        query_params = self.get_all_request_params(request_params=params, **kwargs)
        # raw_query_params = self.build_raw_sql(raw_query_params=self.get_raw_query_params(params=params, **kwargs),
        #                                  params=params, **kwargs)
        # if raw_query_params and raw_query_params.get('raw_query', None):
        #     queryset = self.execute_raw_query_with_model(raw_query = raw_query_params.get('raw_query', None) , raw_count_query=raw_query_params.get('raw_count_query', None), app_name=raw_query_params.get('app_name', None), model_name=raw_query_params.get('model_name', None))
        # else:
        #     queryset = self.get_queryset(query_params=query_params, method='list', **kwargs)

        kwargs['service_method'] = kwargs.get('service_method', params.get('service_method', 'list') if params else 'list')

        queryset = self.get_queryset_by_row_query(params=params, **kwargs)
        if queryset==None:
            queryset = self.get_queryset(query_params=query_params, method='list', **kwargs)

        return self.list_by_queryset(queryset, query_params)


    def list_old(self, params=None, **kwargs):
        query_params = self.get_all_request_params(request_params=params, **kwargs)
        raw_query_params = self.build_raw_sql(raw_query_params=self.get_raw_query_params(params=params, **kwargs),
                                         params=params, **kwargs)
        if raw_query_params and raw_query_params.get('raw_query', None):
            queryset = self.execute_raw_query_with_model(raw_query = raw_query_params.get('raw_query', None) , raw_count_query=raw_query_params.get('raw_count_query', None), app_name=raw_query_params.get('app_name', None), model_name=raw_query_params.get('model_name', None))
        else:
            queryset = self.get_queryset(query_params=query_params, method='list', **kwargs)

        return self.list_by_queryset(queryset, query_params)

    '''
        Description: This is utility method, which will combine all category of parameters.
        Parameters:
            1. request_params (Dic): It contains different types of data e.g. 'query_params', 'request_params', 'logged_in_user'.
        Returns:    Dic of combined all category of parameters
        Exception:  None
    '''

    def decrypt_id(self, id_value, request_params=None):
        logged_in_user = find_in_dic_or_list('logged_in_user')

        if id_value:
            if isinstance(id_value, (int, float, complex)) and not isinstance(id_value, bool):
                decode_response = id_value
            elif id_value.isdigit():
                decode_response = id_value
            else:
                decode_response = Base64EncodeDecode.decode_string(logged_in_user, id_value)
        else:
            decode_response = id_value

        return decode_response

    '''
        Description: This is utility method, which will combine all category of parameters.
        Parameters:
            1. request_params (Dic): It contains different types of data e.g. 'query_params', 'request_params', 'logged_in_user'.
        Returns:    Dic of combined all category of parameters
        Exception:  None
    '''

    def get_sql_execute(self, query):
        count = 0
        cursor = connection.cursor() #MySQLdb.cursors.DictCursor)
        # query = "SELECT * FROM  fcl_commodity_type WHERE id = %s" % (fcl_commodity.id)
        cursor.execute(query)
        # return cursor.fetchall()
        # for row in cursor.fetchall():

        desc = cursor.description
        # return [ dict(zip([col[0] for col in desc], row)) for row in cursor.fetchall()]
        rows = cursor.fetchall()
        count = len(rows)

        data_list = {}
        data_list['data'] = [dict(zip([col[0] for col in desc], row)) for row in rows]
        data_list['count'] = count

        return data_list

    def get_request_params(self, params, default_value={}, **kwargs):
        return params.get('request_params',default_value)

    def is_request_param_exist(self, params, param_name, request_params=None, raise_error=False, error_msg= "Missing mandatory parameter(s)."):
        if request_params == None:
            request_params = self.get_request_params(params)
        if param_name in request_params:
            return True
        elif raise_error:
            raise ValueError(error_msg)
        else:
            return False

    def get_request_param_value(self, params, param_name, default_value=None, request_params=None, raise_error=False, error_msg= "Missing mandatory parameter(s)."):
        if request_params == None:
            request_params = self.get_request_params(params)
        # return request_params.get(param_name, default_value)
        if param_name in request_params:
            return request_params.get(param_name, default_value)
        elif raise_error:
            raise ValueError(error_msg)
        else:
            return default_value


    def get_query_common_params(self, params, **kwargs):
        query_params = {}
        try:
            query_common_params = {'logged_in_user': params['logged_in_user'], 'request': params['request'], 'query_params': {},
                                   'data_source': params['data_source'], 'service_method': params['service_method'], 'fields': params['fields']}
            query_params.update(query_common_params)
            if kwargs:
                query_params.update(kwargs)
            return query_params
        except Exception as e:
            logging.info("Path apis/common/components/base_manager.py  Class: BaseModelManager Method: get_query_common_params(...)  Error: %s"%(str(e)))
            logging.info(traceback.format_exc())
            return query_params

    def to_boolean_value(self, value):
        if value:
            bool_value = False
            if isinstance(value, str):
                value = value.strip().upper()
                bool_value = True if value=="1" or value =="TRUE" or value=="YES" else False
            elif value==1 or value==True:
                bool_value = True
            return bool_value
        else:
            return value

    def to_date_range(self, value): # created_on
        if value:
            created_on = value.split('-')

            created_on_start_split = created_on[0].strip().split('/')
            created_on_end_split = created_on[1].strip().split('/')

            created_on_start = created_on_start_split[2] + '-' + created_on_start_split[0] + '-' + created_on_start_split[1]
            created_on_end = created_on_end_split[2] + '-' + created_on_end_split[0] + '-' + created_on_end_split[1]

            return [created_on_start, created_on_end]
        return []

    def validate_parameter(self, param_name, param_value, validate_failed_list=[], params=None, is_raise_exception=True, **kwargs):
        validate = { 'is_validate': True, 'validate_msg': None }
        if not param_value:
            validate['is_validate'] = False
            validate['validate_msg'] = param_name + " is a mandatory parameter."
        return validate


    def validate_mandatory_parameters(self, params=None, is_raise_exception=True, *args, **kwargs):
        parameters = {'error_message': None, 'errors': []}
        mandatory_parameter = []
        validate_failed_list = []
        data = {}
        if args and len(args)>0:
            request_params = params.get('request_params',{})
            for param_name in args:
                param_name = str(param_name).replace(" ", '')
                param_value = request_params.get(param_name, kwargs.get(param_name, None))
                data[param_name] = param_value
                validate = self.validate_parameter(param_name=param_name, param_value=param_value, validate_failed_list=validate_failed_list, params=params, is_raise_exception=is_raise_exception, **kwargs)
                if not validate.get('is_validate', False):
                    mandatory_parameter.append(param_name)
                    validate_failed_list.append({ param_name: validate})
            if len(mandatory_parameter)>0:
                    if len(mandatory_parameter)>1:
                        mandatory_parameter_csv = ", ".join(mandatory_parameter)
                        errors_message = mandatory_parameter_csv + " are mandatory parameters"
                    else:
                        errors_message = mandatory_parameter[0] + " is mandatory parameter"
                    if is_raise_exception:
                        raise ValueError(errors_message)
                    else:
                        parameters['error_message'] = errors_message

        parameters['errors'] = validate_failed_list
        parameters['data'] = data
        return parameters

    def split_date_range(self, date_range):
        # created_on_range = ['08/03/2021 ', ' 09/08/2021']
        arr_date_range = date_range.split('-')
        created_on_start_split = arr_date_range[0].strip().split('/')
        created_on_end_split = arr_date_range[1].strip().split('/')

        created_on_start = created_on_start_split[2] + '-' + created_on_start_split[0] + '-' + created_on_start_split[1]
        created_on_end = created_on_end_split[2] + '-' + created_on_end_split[0] + '-' + created_on_end_split[1]

        return [created_on_start, created_on_end]



class OneToManyRelationshipModelManager(BaseModelManager):

    def __init__(self, app_name, linked_table_model_name, linked_right_model_name,
                       linked_model_left_field_name, linked_model_right_field_name ):
        super(OneToManyRelationshipModelManager, self).__init__(app_name, linked_table_model_name)

        self.linkedTableModel = None if linked_right_model_name == None else apps.get_model(app_name, linked_right_model_name)
        self.linked_model_left_field_name = linked_model_left_field_name if linked_model_left_field_name else None
        self.linked_model_right_field_name = linked_model_right_field_name if linked_model_right_field_name else None

    def delete_link_table_row(self, objLinkedLeftModel, objLinkedRightModel, params=None, **kwargs):
        left_model_ids = []
        right_model_ids = []
        kwargs = {}

        if type(objLinkedRightModel) is list or type(objLinkedRightModel) is tuple:
            for item in objLinkedRightModel:
                item_id = item if isinstance(item, int) else (int(item) if isinstance(item, str) else item.id)
                right_model_ids.append(item_id)
        else:
            item = objLinkedRightModel
            if isinstance(item, str) and ',' in item:
                right_model_ids = [int(i.lstrip()) for i in item.split(',')]
            else:
                item_id = item if isinstance(item, int) else (int(item) if isinstance(item, str) else item.id)
                right_model_ids.append(item_id)

        if type(objLinkedLeftModel) is list or type(objLinkedLeftModel) is tuple:
            for item in objLinkedLeftModel:
                item_id = item if isinstance(item, int) else (int(item) if isinstance(item, str) else item.id)
                left_model_ids.append(item_id)
        else:
            item = objLinkedLeftModel
            if isinstance(item, str) and ',' in item:
                left_model_ids = [int(i.lstrip()) for i in item.split(',')]
            else:
                item_id = item if isinstance(item, int) else (int(item) if isinstance(item, str) else item.id)
                left_model_ids.append(item_id)


        kwargs[self.linked_model_left_field_name + '_id__in'] = left_model_ids #objLinkedLeftModel if isinstance(objLinkedLeftModel, int) else ( int(objLinkedLeftModel) if isinstance(objLinkedLeftModel, str) else objLinkedLeftModel.id )
        kwargs[self.linked_model_right_field_name + '_id__in'] = right_model_ids #objLinkedRightModel if isinstance(objLinkedRightModel, int) else ( int(objLinkedRightModel) if isinstance(objLinkedRightModel, str) else objLinkedRightModel.id )
        res_tuple = self.linkedTableModel.objects.filter(**kwargs).delete()
        return res_tuple[0]


    def save_link_table(self, objLinkedLeftModel, objLinkedRightModelList=[], params=None, **kwargs):
        default_param_dic = params.get('default_param_dic', None)
        existing_right_model_ids = []
        to_be_deleted_ids = []
        kwargs={}
        kwargs[self.linked_model_left_field_name + '_id'] = objLinkedLeftModel.id
        linked_objects = self.linkedTableModel.objects.filter(**kwargs).values()
        del_rows = 0
        no_change_rows = 0
        new_rows = 0
        for obj in linked_objects:
            found = False
            for item in objLinkedRightModelList:
                item_id = item if isinstance(item, int) else ( int(item) if isinstance(item, str) else item.id )
                if obj[self.linked_model_right_field_name + '_id'] == item_id:
                    found = True
                    break
            if found == False:
                to_be_deleted_ids.append(obj['id'])
            else:
                existing_right_model_ids.append(obj[self.linked_model_right_field_name + '_id'])
                no_change_rows = no_change_rows + 1
        if to_be_deleted_ids:
            del_rows = self.linkedTableModel.objects.filter(id__in= to_be_deleted_ids).delete()
            del_rows = len(to_be_deleted_ids)
        for item in objLinkedRightModelList:
            item_id = item if isinstance(item, int) else ( int(item) if isinstance(item, str) else item.id )
            found = False
            for existing_id in existing_right_model_ids:
                if item_id == existing_id:
                    found = True
                    break
            if found == False:
                updated_kwargs = {}
                if default_param_dic:
                    updated_kwargs.update(default_param_dic)
                updated_kwargs[self.linked_model_left_field_name + '_id'] = objLinkedLeftModel.id
                updated_kwargs[self.linked_model_right_field_name + '_id'] = item_id
                obj = self.linkedTableModel.objects.create(**updated_kwargs)
                new_rows = new_rows + 1

        kwargs = {}
        kwargs[self.linked_model_left_field_name + '_id'] = objLinkedLeftModel.id
        linked_objects = self.linkedTableModel.objects.filter(**kwargs).values()
        return new_rows, del_rows, no_change_rows, linked_objects

    def event_before_filter(self, name, value, queryset, request_params=None):
        # print("name: ", name)
        if name in ['order_by', 'service_method', 'fields', 'page', 'page_size', 'logged_in_user', 'list_method_name', 'list_method_name', 'fetch_clients']:
            return None
        if request_params.get('list_method_name', None) == 'right_model_list' and not ( name.startswith("both_model") or name.startswith("right_model") ):
            return None
        if request_params.get('list_method_name', None) == 'left_model_list' and not ( name.startswith("both_model") or name.startswith("left_model")  or name =="right_model_pk" ):
            return None

        return queryset

    '''
        Funtion: To fetch list of Clients(User Summary) with linked object info
        Relation bet ween Client & Linked Object is Meany-to-One
        Filter: filter_user_id(...)
        client_detail_list
    '''
    def right_model_list(self, params=None, **kwargs):
        query_params = self.get_all_request_params(request_params=params, **kwargs)
        query_params['list_method_name'] = 'right_model_list'
        if 'left_model_pk' in query_params:
            query_params.pop('left_model_pk')

        queryset_linked_model = self.linkedTableModel.objects.all()
        queryset_linked_model = self.apply_filters(queryset_linked_model, query_params=query_params, method='list', **kwargs)

        return self.list_by_queryset(queryset_linked_model, query_params)

    '''
        Funtion: To fetch list of Linked objects with set of Clients(User Summary)
        Relation between Linked Object & Client is One-to-Meany
        Filter: filter_user_id(...)
        linked_object_list
    '''
    def left_model_list(self, params=None, **kwargs):
        query_params = self.get_all_request_params(request_params=params, **kwargs)
        if query_params.get('directly_call_list', False):
            queryset = self.get_queryset(query_params=query_params, method='list', **kwargs)
        else:
            query_params['list_method_name'] = 'left_model_list'
            # if 'right_model_pk' in query_params:
            #     query_params['left_model_pk'] = query_params.pop('right_model_pk')
            queryset_linked_model = self.linkedTableModel.objects.all()
            queryset_linked_model = self.apply_filters(queryset_linked_model, query_params=query_params, method='list', **kwargs)

            if 'right_model_pk' in query_params:
                query_params.pop('right_model_pk')
            if 'list_method_name' in query_params:
                query_params.pop('list_method_name')

            queryset = self.get_queryset(query_params=query_params, method='list', **kwargs)
            '''
                SELECT C.id,  C.company_name 
                FROM company_detail 
                WHERE C.id IN (SELECT V0.company_detail_id FROM company_detail_user_link V0 
                               WHERE V0.company_detail_id IN (SELECT U0.company_detail_id FROM company_detail_user_link U0 WHERE U0.user_detail_id IN (80, 62, 79)))
            '''
            queryset = queryset.filter(id__in=Subquery(queryset_linked_model.values(self.linked_model_left_field_name+'_id')))

        return self.list_by_queryset(queryset, query_params)


    '''
        Filter to fetch list of client (of given Linked Object's id)
        i.e.  linked_objects_field_name = company_detail_id
    '''
    def filter_left_model_pk(self, value, queryset, request_params=None):
        if value:
            kwargs = {}
            if ',' in value:
                company_ids = []
                value = value.replace(" ", "")
                value = value.strip()
                for param in value.split(','):
                    if param:
                        company_ids.append(param)
                kwargs[self.linked_model_left_field_name + '_id__in'] = company_ids
                #queryset = queryset.filter(company_detail_id__in=company_ids)
            else:
                kwargs[self.linked_model_left_field_name + '_id'] = value
                # queryset = queryset.filter(company_detail_id=value)
            queryset = queryset.filter(**kwargs)
        return queryset

    '''
    SQL: SELECT L.id, L.company_detail_id, L.user_detail_id 
         FROM company_detail_user_link AS L
         WHERE L.company_detail_id IN (SELECT U0.company_detail_id FROM company_detail_user_link U0 WHERE U0.user_detail_id IN (80, 62, 79))
     
    '''
    def filter_right_model_pk(self, value, queryset, request_params=None):
        if value:
            kwargs_user_detail = {}
            kwargs_linked_objects = {}
            subquery_field_name = self.linked_model_left_field_name + '_id__in'
            if ',' in value:
                user_ids = []
                value = value.replace(" ", "")
                value = value.strip()
                for param in value.split(','):
                    if param:
                        user_ids.append(param)
                kwargs_user_detail[self.linked_model_right_field_name + '_id__in']=user_ids
                #field_name = self.linked_model_left_field_name + '_id__in'
            else:
                kwargs_user_detail[self.linked_model_right_field_name + '_id'] = value

            links_queryset = self.linkedTableModel.objects.filter(**kwargs_user_detail)
            kwargs_linked_objects[subquery_field_name] = Subquery(links_queryset.values(self.linked_model_left_field_name + '_id'))
            queryset = queryset.filter(**kwargs_linked_objects)
        return queryset



