import logging
import traceback

import json
import requests

from apis.components.base.base_manager import BaseManager

from django.conf import settings
from django.core.cache import cache


class BaseAPIManager(BaseManager):

    def __init__(self, api_name, api_method= 'POST'):
        super(BaseAPIManager, self).__init__()
        self.api_name = api_name
        self.api_method = api_method

        try:
            from apis.common.managers import CommonManager
            if not isinstance(self, CommonManager):
                from apis.components.factories.managers_factory import ManagersFactory
                self.common_manager = ManagersFactory.get_instance().get_common_manager()
            else:
                self.common_manager = None
        except Exception as e:
            self.common_manager = None
            logging.info("Path apis/components/base/base_api_manager.py  Class: BaseAPIManager Method: __init__  Error: %s"%(str(e)))
            logging.info(traceback.format_exc())


    @staticmethod
    def getManagerName():
        raise NotImplemented()

    def get_manager(self, search_key):
        from apis.components.factories.managers_factory import ManagersFactory
        manager = ManagersFactory.get_instance().get_manager(managerName=search_key)
        return manager

    def get_property_value(self, prop_value, default_value):
        if prop_value:
            return prop_value
        else:
            return default_value

    def event_modify_data_change(self, new_key, old_key, value, data_source, key_replace_dic={}, default_dic_items={}, remove_dic_items=[]):
        return value

    def modify_data_format(self, data_source, key_replace_dic={}, default_dic_items={}, remove_dic_items=[]):
        if isinstance(data_source, dict):
            for old_key, new_key in key_replace_dic.items():
                # data_source[new_key] = data_source.pop(old_key)
                data_source[new_key] = self.event_modify_data_change(new_key, old_key, data_source.pop(old_key), data_source, key_replace_dic=key_replace_dic, default_dic_items=default_dic_items, remove_dic_items=remove_dic_items)

            for key, default_value in default_dic_items.items():
                if not key in data_source:
                    data_source[key] = default_value

            for key in remove_dic_items:
                if key in data_source:
                    data_source.pop(key)

        elif isinstance(data_source, list):
            for idx, list_item in enumerate(data_source):
                data_source[idx] = self.modify_data_format(list_item, key_replace_dic, default_dic_items)

        return data_source

    def get_request_headers(self, params=None, **kwargs):
        request_headers = {
                            'authorization_code': settings.VLS_AUTH_CODE,
                            'partner_id': settings.VLS_PARTNER_ID,
                            'Content-Type': 'application/json',
                            'accept': 'application/json'
                           }
        return request_headers

    def get_api_error_info(self, api_resp):
        errors_info = {'errors': [], 'error_no': 0}
        if not api_resp['errorCodes'] == None:
            for err in api_resp['errorCodes']:
                errors_info = self.getErrorInfo(errors_info, error_code=err['errorCode'], description=err['description'], error_no=1)
        return errors_info

    def get_api_url(self, params=None, **kwargs):
        return settings.ADESSO_API_BASE_URL + self.api_name

    def event_before_request_filter(self, name, value, api_params={}, params=None, **kwargs):
        if name in ['data_source', 'order_by', 'service_method', 'fields', 'page', 'page_size', 'logged_in_user', 'filter_session_key']:
            return None
        else:
            return {name : value}

    def process_data_for_request(self, api_request_params= {}, params=None, **kwargs):
        api_params = {}
        for key, value in api_request_params.items():
            api_params_item = self.event_before_request_filter( name=key, value=value, api_params=api_params, params=params, **kwargs)
            if api_params_item:
                api_params.update(api_params_item)
        return api_params

    def handle_response_call_api(self, request_body, req_resp, params=None, **kwargs):
        from project.constants_status import UNKNOWN_ERROR_MESSAGE, INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE, \
            INTERNAL_WARNING_1004_DATA_NOT_FOUND, INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR
        resp = {}

        error_info = {"errors": [], "error_no": INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE, "error_description": None, "api_status_code": None}

        try:
            if req_resp.status_code == 200:
                error_info["api_status_code"] = req_resp.status_code
                error_info["error_no"] = INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE
                resp = req_resp.json()
                if 'false' == resp.get('success','true') and not resp['errorCodes']:
                    err_description = "Error: " + json.dumps(resp)
                    logging.info("Source: apis/components/base/base_api_manager.py, Method name: call_api(...) #140 ==>    " + err_description)
                    resp['errorCodes'] =[{"errorCode": "VLS_REQUEST_FAILED", "description": "Request cannot succeed, There are some problem on server."}]

                if resp['errorCodes']:
                    error_info["error_no"] = INTERNAL_WARNING_1004_DATA_NOT_FOUND
                    str_request_body = "RequestBody: " + json.dumps(request_body)
                    logging.info("Source: apis/components/base/base_api_manager.py, Method name: call_api(...) #146 ==>    " + str_request_body)
                    error_list = resp.get('errorCodes', [])
                    errors = []
                    for err in error_list:
                        var_err = err.get("description", UNKNOWN_ERROR_MESSAGE)
                        # if err.get("VOLUME_MISMATCH", None):
                        #     var_err = err.get("VOLUME_MISMATCH", "Unknown error") + ": " + var_err
                        errors.append(var_err)
                        err_description = "Error: " + json.dumps(err)
                        logging.info("Source: apis/components/base/base_api_manager.py, Method name: call_api(...) #155 ==>    " + err_description)
                    error_info["errors"] = errors
                elif resp.get('success', None) != 'true':
                    resp['request_body'] = request_body if request_body else ""
                    logging.info("Source: apis/components/base/base_api_manager.py, Method name: call_api(...) API response ==>    " + json.dumps(resp))

            else:
                error_info["error_no"] = INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR
                error_info["errors"] = [UNKNOWN_ERROR_MESSAGE]
                error_info["api_status_code"] = req_resp.status_code
                str_request_body = "Source: apis/components/base/base_api_manager.py, Method name: call_api(...) #164 ==>    RequestBody: " + json.dumps(request_body)
                logging.info(str_request_body)
                logging.info("Source: apis/components/base/base_api_manager.py, Method name: call_api(...) #166 ==>    req_resp.status_code: " + str(req_resp.status_code))
                # raise ValueError(error)
        except Exception as e:
            logging.error("Source: apis/components/base/base_api_manager.py, Method name: call_api(...) #169 - Error: %s:" % (str(e)))
            logging.info(traceback.format_exc())
            try:
                logging.error(" response.status_code: " + req_resp.status_code)
            except:
                logging.error(" response.status_code: ....")
            try:
                logging.error(" response.text: " + req_resp.text)
            except:
                logging.error(" response.text: ....")
            try:
                logging.error(" response.reason: " + req_resp.reason)
            except:
                logging.error(" response.reason: ....")

            error_info["error_no"] = INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR
            error_info["errors"] = [UNKNOWN_ERROR_MESSAGE]
            error_info["error_description"] = str(e)
            # raise ValueError(error)
        # resp = req_resp.json()
        resp['error_info'] = error_info
        return resp



    def call_api(self, params=None, **kwargs):
        '''
        from jiffyship.fmstatus import UNKNOWN_ERROR_MESSAGE, INTERNAL_NO_ERROR_1001_SUCCESSFULLY_DONE, \
            INTERNAL_WARNING_1004_DATA_NOT_FOUND, INTERNAL_ERROR_1000_INTERNAL_SERVER_ERROR
        resp = {}
        '''
        api_url = self.get_api_url(params=params, **kwargs)

        request_headers = self.get_request_headers(**kwargs)

        from apis.common.utilities.function_utility import isMethodExist

        if self.api_method and self.api_method.strip().upper()=='GET':
            api_params = []
            if isMethodExist(self, "get_request_param"):
                request_body = self.get_request_param(params=params, **kwargs)
            elif isMethodExist(self, "get_request_body"):
                request_body = self.get_request_body(params=params, **kwargs)
            else:
                query_params = self.get_all_request_params(request_params=params, **kwargs)
                request_body = self.process_data_for_request(api_request_params=query_params, params=params, **kwargs)
            for key, value in request_body.items():
                api_params.append((key, value))

            req_resp = requests.get(url=api_url, params=api_params, headers=request_headers, verify=False)
        else:
            if isMethodExist(self, "get_request_body"):
                request_body = self.get_request_body(params=params, **kwargs)
            else:
                query_params = self.get_all_request_params(request_params=params, **kwargs)
                request_body = self.process_data_for_request(api_request_params=query_params, params=params, **kwargs)

            req_resp = requests.post(url=api_url, json=request_body, headers=request_headers, verify=False)

        return self.handle_response_call_api(request_body, req_resp, params=None, **kwargs)


    def response_data_filter(self, data, params=None, **kwargs):
        return data

    def process_data_for_response(self, api_response, errorCodes, params=None, **kwargs):
        # response_data = []
        # return response_data
        raise NotImplemented()

    def list(self, params=None, **kwargs): # def fetch(self, *args, **kwargs):
        response_data = None
        data_dict={}

        cache_key = kwargs.get('cache_key', params.get('cache_key', params.get('request_params', {}).get('cache_key',None)))
        if cache_key:
            response_data = cache.get(cache_key, None)
            error_info =  { "errors": [], "error_no": 0 }

        if not response_data:
            resp = self.call_api(params=params, **kwargs)
            response_data = self.process_data_for_response(api_response=resp, errorCodes=resp['errorCodes'], params=params, **kwargs)
            error_info = self.get_api_error_info(resp)
            if cache_key and response_data:
                cache.set(cache_key, response_data)

        if not response_data:
            response_data = []

        response_data = self.response_data_filter(data=response_data, params=params, **kwargs)

        data_dict["data"]=response_data
        data_dict["count"]=len(response_data)
        data_dict["error_info"] = error_info #self.get_api_error_info(resp)

        return data_dict

