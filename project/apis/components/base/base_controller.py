import json
import sys
import logging
import os
import traceback

from django.conf import settings

from datetime import datetime, timedelta, date
from django.db import DataError
from django.forms.models import model_to_dict
from rest_framework.parsers import MultiPartParser, FileUploadParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework import serializers


from apis.common.utilities.function_utility import getMethodHandler
from celery.exceptions import ImproperlyConfigured

from project.constants_status import HTTP_500_INTERNAL_SERVER_ERROR, INTERNAL_WARNING_1004_DATA_NOT_FOUND, \
    INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE, INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR, get_error_message



class BaseController(GenericAPIView):

    def __init__(self):
        self.manager = None
        self.api_manager = None
        self.data_source = "FILE"

    def get_serializer_class(self, request=None, params=None, **kwargs):
        if self.serializer_class :
            return self.serializer_class
        else:
            return serializers.Serializer

    def event_after_dispatch(self, request, *args, **kwargs):
        return kwargs

    '''
        Description:  If you want to customized default behavior, then you can override dispatch method in your Controller.
            signature of this method is same as GenericAPIView
        Parameters:  
            1. request : Request object. 
            2. *args  : list of parameters. 
            3. **kwargs :  dic of parameters. 
        Returns:    None
        Exception:  None
    '''
    def dispatch(self, request, *args, **kwargs):
        skip_change_in_dispatch = kwargs.get('skip_change_in_dispatch', False)
        if not skip_change_in_dispatch:
            additional_params = kwargs.get('additional_params', {})
            additional_params['logged_in_user'] = request.user
            additional_params['request'] = request

            if 'pk' in kwargs and kwargs['pk']==None:
                pk = kwargs.pop('pk')
            else:
                pk = kwargs['pk'] if 'pk' in kwargs and kwargs['pk'] else None

            request_data = self.get_request_data_dic(request, pk, **kwargs)

            if pk == None and 'id' in request_data['request_params']  and (request_data['service_method'] == 'retrieve' or request_data['service_method'] == 'delete'):
                kwargs['pk'] = request_data['request_params']['id']
            
            additional_params.update(request_data)
            kwargs['additional_params'] = additional_params
            # kwargs['service_method'] = kwargs.get('service_method')
        updated_kwargs = self.event_after_dispatch(request, *args, **kwargs)
        return super(BaseController, self).dispatch(request, *args, **updated_kwargs)

    '''
        Description: this method collect request data using request.data and request.query_params
        Parameters:  
            1. request : Request object. 
        Returns:    Dic of request data
        Exception:  None
    '''
    def get_query_params(self, request):
        try:
            query_params = request.data
        except Exception as e1:
            try:
                query_params = request.query_params
            except Exception as e2:
                query_params = {}

        return query_params

    '''
        Description: this method collect request data using request.body
        Parameters:  
            1. request : Request object. 
        Returns:    Dic of request data
        Exception:  None
    '''
    def get_request_body_params(self, request):
        body_unicode = request.body.decode('utf-8')
        content = json.loads(body_unicode)
        if content:
            return content
        else:
            return {}

    '''
        Description: this method collect request data using request.GET
        Parameters:  
            1. request : Request object. 
        Returns:    Dic of request data
        Exception:  None
    '''
    def get_request_param_dic(self, request):
        request_params = {}
        param_dic = request.GET
        for key,value in param_dic.items():
            if value and ( type(value) is list or type(value) is tuple) and len(value)==1:
                request_params[key] = value[0]
            else:
                request_params[key] = value
        return request_params

    '''
        Description: This method is an event, give you a chance to add/remove/modify request data, after feached all request data
        Parameters:  
            1. request : Request object. 
            2. pk : Prymary key's value pased in request.
            3. request_data : request's data .
        Returns:    Dic of request data
        Exception:  None
    '''
    def after_request_data_dic(self, request, pk=None, request_data={}):
        return request_data

    '''
        Description: This method is used for collect data from request, usinf differnt methods 
            e.g. get_query_params(), get_request_body_params(), get_request_param_dic()  
        Parameters:  
            1. request : Request object. 
            2. pk_value : Prymary key's value pased in request.
            3. **kwargs :  dic of parameters.
        Returns:    Dic of request data
        Exception:  None
    '''
    def get_request_data_dic(self, request, pk_value = None, **kwargs):
        request_data={}
        try:
            params_count = 0
            request_params = {}
            fields = None
            if 'fields' in kwargs:
                fields = kwargs.pop('fields')

            if 'service_method' in kwargs:
                service_method = kwargs.pop('service_method')
            else:
                if request.method == 'GET':
                    service_method = 'list'
                elif request.method == 'POST':
                    service_method = 'create'
                elif request.method == 'DELETE':
                    service_method = 'delete'
                else:
                    service_method = 'update'

            request_data['logged_in_user'] = request.user
            request_data['query_params'] = self.get_query_params(request)
            params_count = params_count + len(request_data['query_params'])

            try: # if request.method == 'GET':
                params_count = params_count + len(request.GET)
                request_params.update(self.get_request_param_dic(request))  # request.GET) #request_params.update(**(request.GET)) #request_data.update(request.GET)
                request_data['data_source'] = request.GET.get("data_source", 'FILE').upper()
                request_data['service_method'] = request.GET.get("service_method", service_method) #'list')
                request_data['fields'] = request.GET.get("fields", fields)
            except Exception as e2:
                pass

            try: #elif request.method == 'POST':
                params_count = params_count + len(request.POST)
                request_params.update(request.POST) #request_data.update(request.POST)

                body_unicode = request.body.decode('utf-8')
                if body_unicode:
                    content = json.loads(body_unicode)
                    if content:
                        if type(content) is list or type(content) is tuple:
                            params_count = params_count + 1
                            request_params['LIST_OF_PARAMS'] = content
                        else:
                            params_count = params_count + len(content)
                            request_params.update(content)  # request_data.update(content)

                    request_data['data_source'] = request.POST.get("data_source", 'FILE').upper()
                    request_data['service_method'] = request.POST.get("service_method", service_method) #'create')
            except Exception as e2:
                pass

            try: # else:
                body_unicode = request.body.decode('utf-8')
                if body_unicode:
                    content = json.loads(body_unicode)
                    if content:
                        params_count = params_count + len(content)
                        request_params.update(content) #request_data.update(content)

                    request_data['data_source'] = content.get("data_source", 'FILE').upper()
                    request_data['service_method'] = content.get("service_method", service_method) #'update')
            except Exception as e2:
                if request.method == 'POST':
                    try:
                        pass
                    except Exception as e3:
                        pass

            if 'service_method' in request_params:
                request_data['service_method'] = request_params.pop('service_method')

            request_data['request_params'] = request_params

            if pk_value == None:
                if 'id' in request_params and request_params['id'] == None:
                    pk_value = request_params.pop('id')
                else:
                    pk_value = request_params['id'] if 'id' in request_params and request_params['id'] else None

            if pk_value:
                if request_data['service_method'] == 'list' and params_count == 1 :
                    request_data['service_method'] = "retrieve"
                # elif request_data['service_method'] == 'create' and params_count == 1:
                #     request_data['service_method'] = "delete"
                elif request_data['service_method'] == 'create':
                    request_data['service_method'] = "update"

            self.service_method = request_data['service_method']
        except Exception as e:
            logging.info("Path: apis/common/components/base_controller.py Class: BaseController get_request_data_dic() Error = %s:" % (str(e)))
            logging.info(traceback.format_exc())

        request_data = self.after_request_data_dic(request, pk_value, request_data)
        return request_data

    '''
        Description: This is a utility method for response formatter 
        Parameters:  
            1. result_data : data return from Managers
            2. status_code : status_code for response
            3. response_code :  response_code for response
            4. response_message :  response_message for response
            5. error_info :  error_info for response
            6. other_data_info :  some other data for response
            7. direct_data_provided :  False for customize argument (result_data)
        Returns:    Dic of request data
        Exception:  None
    '''
    def data_wrapper_response(self, result_data=None, status_code=None,
                                    response_code=None, response_message=None,
                                    error_info={}, other_data_info = None,
                                    result_data_move_into_result = True): #   auto_restructure_result_data = True ): # direct_data_provided == False
        if status_code and status_code in [200, 201, 202, 204]:
            status = True
        else:
            status = False

        if result_data_move_into_result == True:
            result_data =  {'result': result_data}
        if response_code:
            result_data['response_code'] = response_code
        if response_message:
            result_data['response_message'] = response_message
        elif response_code:
            result_data['response_message'] = get_error_message(response_code)
        if other_data_info:
            result_data.update(other_data_info)

        data = {
            'status': status,
            'status_code': status_code,
            'data': result_data,
            'errors': error_info
        }
        return Response(data, status=status_code)

    '''
        Description: This parse, formate and validate data using Serializer 
        Parameters:  
            1. request : data return from Managers
            2. instance : object of Model (at the time of Edit)
            3. partial :  is_partial update
            4. is_validated_data :  is data validated required 
        Returns:    Dic of request data
        Exception:  None
    '''
    def get_serializer_data(self, request, request_data=None, instance=None, partial=False, is_validated_data = True, many=False, cls_serializer=None):
        from django.core.files.uploadedfile import TemporaryUploadedFile
        try:
            try:
                if request_data:
                    request_data = request_data.copy()
                else:
                    request_data = request.data.copy()
            except Exception as e:
                ordinary_dict={}
                for key, value in request.data.items():
                    if type(value) == TemporaryUploadedFile:
                        ordinary_dict[key] = value
                    else:
                        ordinary_dict[key] = value
                from django.http import QueryDict
                request_data = QueryDict('', mutable=True)
                request_data.update(ordinary_dict)

            model_fields = self.manager.model_fields()

            args=[]
            kwargs={}
            kwargs['data'] = request_data
            if many == False:
                for key in list(request_data.keys()):
                    if not str(key) in model_fields and key == 'service_method':
                        del request_data['service_method']
                if instance:
                    kwargs['instance']=instance
            else:
                kwargs['many'] = True
                if instance:
                    kwargs['instance'] = instance
            if cls_serializer:
                # serializer_context = { 'request': self.request, 'format': self.format_kwarg, 'view': self }
                kwargs['context'] =  self.get_serializer_context()
                serializer = cls_serializer(*args, **kwargs)
            else:
                serializer = self.get_serializer(*args, **kwargs)


            if is_validated_data:
                serializer.is_valid(raise_exception=True)

            return serializer.validated_data
        except serializers.ValidationError as ve:
            raise serializers.ValidationError(ve.detail)
        except Exception as e:
            logging.info("Path: apis/common/components/base_controller.py get_serializer_data() Error = %s:" % (str(e)))
            logging.info(traceback.format_exc())

    '''
        Description: This method is use for data validation
        Parameters:  
            1. request : data return from Managers
            2. serializer : instance/class of Serializer  
        Returns:    Boolean
        Exception:  None
    '''
    def validate_data(self, request, serializer = None, is_raise_exception = True):
        if serializer == None:
            serializer = self.get_serializer(data=request.data)
        return serializer.is_valid(raise_exception=is_raise_exception)


    '''
        HTTP Service provider functions configuration e.i. post, get, put etc.
        If "service_method" not found in Request-Params then "GET", "POST" and "PUT" methods will assumed 
        'list', 'create' and 'update' value of "service_method" param.   
    '''
    def get(self, request, *args, **kwargs):
        return self.common_method(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.common_method(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.common_method(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.common_method(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return self.common_method(request, *args, **kwargs)


    '''
        Description: This method call actual service method based on request's type or request's parameter 'service_method'
        Parameters:  
            1. request : data return from Managers
            2. *args : list of params
            3. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def common_method(self, request, *args, **kwargs):
        try:
            params = kwargs.pop('additional_params')
            service_method_name = "service_" + params['service_method'].lower()

            is_method_exist, handler = getMethodHandler(self, service_method_name)
            # handler = getattr(self, service_method_name, self.http_method_not_allowed)
            if is_method_exist:
                return handler(request, params, *args, **kwargs)
            else:
                is_method_exist, handler = getMethodHandler(self, "service")
                # handler = getattr(self, "service", self.http_method_not_allowed)
                if is_method_exist:
                    return handler(request, params, *args, **kwargs)
                else:
                    raise ImproperlyConfigured("Method named 'service' not found in class '%s'." % (type(self).__name__))

        except serializers.ValidationError as ve:
            logging.info("Path: apis/common/components/base_controller.py common_method() ValidationError = %s:" % (str(ve)))
            logging.info(traceback.format_exc())
            raise serializers.ValidationError(ve.detail)
        except DataError as de:
            logging.info("Path: apis/common/components/base_controller.py common_method() DataError = %s:" % (str(de)))
            logging.info(traceback.format_exc())
            raise serializers.ValidationError({'data_error': '#' + str(de.args[0])+ ': ' + de.args[1]})
        except ValueError as ve:
            logging.info("Path: apis/common/components/base_controller.py common_method() DataError = %s:" % (str(ve)))
            logging.info(traceback.format_exc())
            raise serializers.ValidationError({'error': '#Message: ' + ve.args[0]})
        except Exception as e:
            logging.info("Path: apis/common/components/base_controller.py common_method() Error = %s:" % (str(e)))
            logging.info(traceback.format_exc())
            raise serializers.ValidationError({'error': str(e)})

            # return self.data_wrapper_response(result_data=[],
            #                                   response_code=INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR,
            #                                   status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            #                                   error_info={"error_description": str(e)})

    '''
        Description: This is default service_method
        Parameters:  
            1. request : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service(self, request,  params, *args, **kwargs):
        raise NotImplemented()

    '''
        HTTP default/common Implementation for actual service-functions e.i. 
        service_create, service_update, service_delete etc.
    '''
    def service_save_or_update(self, request, params=None, *args, **kwargs):

        request_params = params['request_params']
        pk_field_name = self.manager.get_pk_field_name()
        if 'id' in request_params or 'pk' in kwargs or pk_field_name in request_params:
            return self.service_update(request, params, *args, **kwargs)
        else:
            return self.service_create(request, params, *args, **kwargs)

    '''
        Description: HTTP default service_method for retrieve data Implementation 
        Parameters:  
            1. request : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def obj_to_response(self, obj, request, params=None, *args, **kwargs):
        cls_serializer  = self.get_serializer_class(request=request, params=params, **kwargs)
        if obj:
            serializer_context = params if params else {}
            result_data = cls_serializer(obj, context=serializer_context).data # self.serializer_class(obj).data
            response_code = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            response_message = "Retrieved object successfully."
            response_status = status.HTTP_200_OK # status.HTTP_202_ACCEPTED
        else:
            result_data = {}
            response_code = INTERNAL_WARNING_1004_DATA_NOT_FOUND
            response_message = "Not found."
            response_status = status.HTTP_404_NOT_FOUND

        return self.data_wrapper_response(result_data=result_data, response_code=response_code, response_message=response_message, status_code=response_status)

    def service_retrieve(self, request, params=None, *args, **kwargs):
        obj = self.manager.retrieve(kwargs['pk'], params, **kwargs)
        return  self.obj_to_response(obj, request, params=params, *args, **kwargs)


    '''
        Description: HTTP default service_method for retrieve data Implementation 
        Parameters:  
            1. request : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service_create(self, request, params=None, *args, **kwargs):
        if 'request_params' in params and 'LIST_OF_PARAMS' in params['request_params']:
            service_data = self.get_serializer_data(request, many=True)
            obj = []
            for service_data_item in service_data:
                obj.append(self.manager.create(params, **service_data_item))

            data_list = {}
            cls_serializer = self.get_serializer_class(request=request, params=params, **kwargs)
            data_list['count'] = len(obj)
            data_list['data'] =  cls_serializer(obj, context=params, many=True).data  # self.serializer_class(obj).data

            response_code = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            response_message = "%s New object(s) created successfully." % (data_list['count'])
            return self.data_wrapper_response(result_data=data_list,
                                              response_code=response_code,
                                              response_message=response_message,
                                              status_code=status.HTTP_200_OK)
        else:
            service_data = self.get_serializer_data(request)
            obj = self.manager.create(params, **service_data)

            cls_serializer = self.get_serializer_class(request=request, params=params, **kwargs)
            result_data = cls_serializer(obj,  context=params ).data # self.serializer_class(obj).data

            response_code = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            response_message = "New object created successfully."

            return self.data_wrapper_response(result_data=result_data, response_code=response_code, response_message=response_message, status_code=status.HTTP_200_OK)  # status.HTTP_202_ACCEPTED)

    '''
        Description: HTTP default service_method for update data Implementation 
        Parameters:  
            1. request : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service_update(self, request, params=None, *args, **kwargs):
        pk_field_name = self.manager.get_pk_field_name()
        pk_field_vlaue = None
        if 'pk' in kwargs:
            pk_field_vlaue = kwargs.get('pk', None)
        elif params and ( 'request_params' in params )  and  pk_field_name in params['request_params']:
            request_params = params['request_params']
            pk_field_vlaue = request_params.get(pk_field_name, None)

        if pk_field_vlaue:
            instance = self.manager.retrieve(id_value=pk_field_vlaue, params=params, **kwargs)    #self.Model.objects.get(pk=pk_field_vlaue)
            # print(request.data)
            
            service_data = self.get_serializer_data(request, instance=instance, partial=True)
            
            updated_rows = self.manager.update(pk=pk_field_vlaue, params= params, *args,**service_data)
            obj = self.manager.retrieve(id_value=pk_field_vlaue, params=params, **kwargs)
            # result_data = model_to_dict(obj)
            result_data = self.serializer_class(obj).data
            response_code = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            response_message = "%s object(s) updated successfully." % (updated_rows)  # 1 row(s) affected
        else:
            pass

        return self.data_wrapper_response(result_data=result_data, response_code=response_code, response_message=response_message, status_code=status.HTTP_200_OK) # status.HTTP_202_ACCEPTED)

    def get_default_param_dic(self, request, params=None, *args, **kwargs):
        datetime_now = datetime.now()
        return {
            'created_on': datetime_now,
            'updated_on': datetime_now,
            'created_by_id': request.user.id,
            'updated_by_id': request.user.id
        }

    def save_or_update(self, request, request_data, obj_manager=None, cls_serializer=None, params=None, only_create=False, *args, **kwargs):
        pk_field_vlaue = request_data.get("id", None)
        updated_rows = 0
        new_rows = 0
        if not obj_manager:
            obj_manager = self.manager
        if pk_field_vlaue:
            if only_create==False:
                instance = obj_manager.retrieve(id=pk_field_vlaue, params=params, **kwargs)
                if 'created_on' in request_data:
                    request_data.pop('created_on')
                if 'created_by_id' in request_data:
                    request_data.pop('created_by_id')
                service_data = self.get_serializer_data(request, request_data=request_data, instance=instance, partial=True,
                                                        cls_serializer=cls_serializer)
                updated_rows = obj_manager.update(pk=pk_field_vlaue, params=params, *args, **service_data)
            obj = obj_manager.retrieve(id=pk_field_vlaue, params=params, **kwargs)
        else:
            service_data = self.get_serializer_data(request, request_data=request_data, cls_serializer=cls_serializer)
            obj = obj_manager.create(params, **service_data)
            new_rows = 1
        return updated_rows, new_rows, obj

    '''
        Description: HTTP default service_method for delete data Implementation 
        Parameters:  
            1. request : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service_delete(self, request, params=None, *args, **kwargs):
        result_data_dic =  self.destroy_or_delete_without_response(request, params, *args, **kwargs)
        return self.data_wrapper_response(result_data=result_data_dic['result_data'], response_code=result_data_dic['response_code'],
                                          response_message=result_data_dic['response_message'],
                                          status_code=status.HTTP_200_OK)  # status.HTTP_202_ACCEPTED)

    def service_destroy(self, request, params=None, *args, **kwargs):
        return self.service_delete(request, params, *args, **kwargs)

    def destroy_or_delete_without_response(self, request,  params=None, *args, **kwargs):
        pk_field_name = self.manager.get_pk_field_name()
        pk_field_vlaue = None
        if 'pk' in kwargs:
            pk_field_vlaue = kwargs.get('pk', None)
        elif params and ( 'request_params' in params )  and  pk_field_name in params['request_params']:
            request_params = params['request_params']
            pk_field_vlaue = request_params.get(pk_field_name, None)

        result_data_dic = {'result_data': {}, 'updated_rows':0, 'response_code': INTERNAL_WARNING_1004_DATA_NOT_FOUND, 'response_message': "No data found for delete"}
        if pk_field_vlaue:
            instance = self.manager.retrieve(id_value=pk_field_vlaue, params=params, **kwargs)
            result_data = self.serializer_class(instance).data
            result_data_dic['result_data']=result_data

            updated_rows = self.manager.delete(pk_field_vlaue, params, **kwargs) #.update(pk=pk_field_vlaue, **service_data)
            result_data_dic['updated_rows'] = updated_rows[0]

            result_data_dic['response_code'] = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            result_data_dic['response_message'] = "%s object(s) deleted successfully." % (updated_rows[0])  # 1 row(s) affected
        else:
            pass
        return result_data_dic


    '''
        Description: Helper method for, HTTP default service_method for list data Implementation 
        Parameters:  
            1. data_list : data return from Managers
            2. cls_serializer : class of serializer
            3. params: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service_list_response(self, data_list, cls_serializer=None, params={}):
        other_data_info = {}
        if not data_list:
            data_list = {'data': data_list, 'count': 0}

        if data_list:
            if cls_serializer== None:
                result_data = data_list
                if 'data' not in data_list or 'count' not in data_list:
                    data_list = {'data': data_list, 'count': len(data_list)}

            if data_list['data']:
                if cls_serializer:
                    serializer_context = params
                    result_data = cls_serializer(data_list['data'], context=serializer_context, many=True).data
                other_data_info['count'] = data_list['count']

                if 'pagination' in data_list and data_list['pagination']:
                    page_info = data_list['page_info']
                    other_data_info['next_url'] = page_info.pop('next_url')
                    other_data_info['previous_url'] = page_info.pop('previous_url')
                    other_data_info['page_info'] = page_info

                if 'error_info' in data_list and data_list['error_info']:
                    other_data_info['error_info'] = data_list['error_info']

                response_code = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
                response_message = "Retrieved " + str(data_list['count']) + " object(s) successfully."
                response_status = status.HTTP_200_OK # status.HTTP_202_ACCEPTED
            else:
                result_data = {}
                if 'error_info' in data_list and data_list['error_info']:
                    other_data_info['error_info'] = data_list['error_info']
                response_code = INTERNAL_WARNING_1004_DATA_NOT_FOUND
                response_message = "Not found."
                response_status = status.HTTP_200_OK # status.HTTP_202_ACCEPTED

            # return result_data, response_code, response_message, response_status, other_data_info

            response_data_dic = {'result_data': result_data, 'other_data_info': other_data_info,
                                 'response_code': response_code, 'response_message': response_message,
                                 'response_status': response_status}
            return response_data_dic

    def to_response(self, request, data_list, params=None, cls_serializer=None, without_serializer=False, *args, **kwargs):
        if without_serializer==False and cls_serializer==None:
            cls_serializer = self.get_serializer_class(request=request, params=params, **kwargs)
        result_data_dic = self.service_list_response(data_list, cls_serializer, params)

        return self.data_wrapper_response(result_data=result_data_dic['result_data'], response_code=result_data_dic['response_code'],
                                          response_message=result_data_dic['response_message'], status_code=result_data_dic['response_status'],
                                          other_data_info=result_data_dic['other_data_info'])

    def event_api_list_filters(self):
        pass
    '''
        Description: HTTP default service_method for list data Implementation 
        Parameters:  
            1. data_list : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service_list(self, request, params=None, *args, **kwargs):
        manager = self.api_manager if params.get('data_source', "File").upper() == 'API' else self.manager
        data_list = manager.list(params, **kwargs)
        return self.to_response(request, data_list, params, *args, **kwargs)


    '''
        Description: HTTP default service_method for create or update data Implementation 
        Parameters:  
            1. data_list : data return from Managers
            2. params : Parameters
            3. *args : list of params
            4. **kwargs: dic of params
        Returns:    Response
        Exception:  None
    '''
    def service_save(self, request,  *args, **kwargs):
        pk_field_name =  self.Model._meta.pk.name
        pk_field_vlaue = request.data.get(pk_field_name, None)
        if pk_field_vlaue:
            instance = self.Model.objects.get(pk=pk_field_vlaue)
            service_data = self.get_serializer_data(request, instance=instance, partial=True)
            updated_rows = self.Model.objects.filter(pk=pk_field_vlaue).update(**service_data)
            obj = self.Model.objects.get(pk=pk_field_vlaue)
            result_data = model_to_dict(obj)
            response_code =INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            response_message = "%s object(s) updated successfully." % (updated_rows)  # 1 row(s) affected
            return self.data_wrapper_response(result_data=result_data, response_code=response_code, response_message=response_message, status_code=status.HTTP_200_OK )# status.HTTP_202_ACCEPTED)
        else:
            return self.service_create(self, request, *args, **kwargs)

    def get_param_for_manager_call(self, params, service_method=None, fields=None, **kwargs):
        list_params = {'logged_in_user': params['logged_in_user'], 'request': params['request'], 'query_params': {},
                       'data_source': params['data_source'], 'service_method': params['service_method'],
                       'fields': params['fields']}
        if service_method:
            list_params['service_method']= service_method
        if fields:
            list_params['fields']= fields
        if kwargs:
            request_params = {}
            request_params.update(kwargs)
            list_params['request_params']=request_params
        return list_params

    def get_request_param_value(self, param_name, params={}, *args, **kwargs):
        default_value = kwargs.get('default_value', None)
        first_item = kwargs.get('only_first_item', None)
        if kwargs.get('request_params', None):
            request_params = kwargs.get('request_params', None)
        else:
            request_params = params.get('request_params', {})

        param_value = request_params.get(param_name, default_value)
        if first_item and type(param_value) == list:
            param_value = param_value[0]

        return param_value

    def get_pk_param_value(self, params={}, *args, **kwargs):
        pk_field_name = self.manager.get_pk_field_name()
        pk_field_vlaue = None
        if 'pk' in kwargs:
            pk_field_vlaue = kwargs.get('pk', None)
        elif params and ('request_params' in params) and pk_field_name in params['request_params']:
            pk_field_vlaue = self.get_request_param_value(param_name=pk_field_name, params=params, *args, **kwargs)
        return pk_field_vlaue

    def update_request_params(self, params, param_key, param_updated_value):
        request_params = params.get('request_params', {})
        request_params[param_key]=param_updated_value
        params['request_params'] = request_params
        return params

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


class FileUploaderController(BaseController):
    parser_classes = (MultiPartParser, FileUploadParser,)


    def __init__(self):
        super(FileUploaderController, self).__init__()

    def event_fetch_file_path(self, request, dir_name = settings.TEMPORARY_UPLOAD_DIR, params=None, *args, **kwargs):
        file_path = dir_name # "/temp/%s/"%(dir_name)
        return settings.BASE_DIR + file_path

    def event_fetch_file_name(self, request, given_file_name, file_extension, params=None, *args, **kwargs):
        return given_file_name

    def get_or_create_path(self, request, params=None, *args, **kwargs):
        try:
            file_path = self.event_fetch_file_path(request, params=params, *args, **kwargs)
            if not os.path.exists(file_path):
                oldmask = os.umask(000)
                os.makedirs(file_path, 0o777)
                os.umask(oldmask)
            return  file_path
        except Exception as e:  # OSError as e:
            logging.info("Path: apis/common/views.py  Class: Multiuploader Error = %s:" % (str(e)))
            logging.info(traceback.format_exc())
            raise Exception(str(e))

    def get_uploaded_file(self, request, params=None, param_name='file', *args, **kwargs):
        up_file = request.FILES[param_name]
        return up_file

    def save_uploaded_file(self, request, params=None, param_name='file', *args, **kwargs):
        result_dic = {}
        if request.FILES:
            try:
                result_dic = {}
                up_file = request.FILES[param_name]
                file_extension = os.path.splitext(str(up_file))[1]
                file_name = self.event_fetch_file_name(request, given_file_name = up_file.name, file_extension= file_extension, params=params, *args, **kwargs)
                result_dic.update({'files' : [{ 'uploaded_file_name': up_file.name, 'file_size': up_file.size, 'file_name': file_name, 'file_name_alias': up_file.name, 'file_extension': file_extension, 'content_type': up_file.content_type}]})
                result_dic.update({'file_names_csv' : file_name})
                result_dic.update({'file_names_alias_csv': up_file.name})
                destination = open(self.get_or_create_path(request) + file_name , 'wb+')
                for chunk in up_file.chunks():
                    destination.write(chunk)
                response_code = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
            except Exception as e:
                response_code = INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR
                logging.info("Path: apis/common/views.py  Class: Multiuploader Error = %s:" % (str(e)))
                logging.info(traceback.format_exc())
            response_message = get_error_message(response_code)
        else:
            response_code = INTERNAL_WARNING_1004_DATA_NOT_FOUND
            response_message = 'No file found for upload.' #get_error_message(response_code)
            result_dic.update({'files': [], 'file_names_csv': ''})

        result_dic.update({'response_message': response_message, 'response_code': response_code})
        return result_dic

    def service_create(self, request, params=None, *args, **kwargs):
        result_dic = self.save_uploaded_file(request, params=params, param_name='file', *args, **kwargs)
        if result_dic:
            response_code = result_dic.pop('response_code',"")
            response_message = result_dic.pop('response_message',"")

            response_status = status.HTTP_200_OK  # status.HTTP_202_ACCEPTED
            return self.data_wrapper_response(result_data=result_dic, response_code=response_code,
                                              response_message=response_message, status_code=response_status)
        else:
            obj = None
            return self.obj_to_response(obj, request, params=params, *args, **kwargs)
