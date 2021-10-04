import traceback
import logging

import base64
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str, force_text
from binascii import Error as BinasciiError


def find_in_dic_or_list(self, key, dic_or_list, default_value=None):
    if isinstance(dic_or_list, dict):
        if key in dic_or_list:
            return dic_or_list[key], True
        else:
            for k, v in dic_or_list.iteritems():
                if isinstance(v, dict):
                    found_val, is_found = self.find_in_dic(key, v)
                    if is_found:
                        return found_val, True
            return default_value, False

    elif isinstance(dic_or_list, list):
        for v in dic_or_list:
            if isinstance(v, dict):
                found_val, is_found = self.find_in_dic(key, v)
                if is_found:
                    return found_val, True
        return default_value, False

    return default_value, False


class Base64EncodeDecode():
    @staticmethod
    def urlsafe_base64_encode(s):
        """
        Encodes a bytestring in base64 for use in URLs, stripping any trailing
        equal signs.
        """
        return base64.urlsafe_b64encode(s).rstrip(b'\n=')

    @staticmethod
    def urlsafe_base64_decode(s):
        """
        Decodes a base64 encoded string, adding back any trailing equal signs that
        might have been stripped.
        """
        s = force_bytes(s)
        try:
            return base64.urlsafe_b64decode(s.ljust(len(s) + len(s) % 4, b'='))
        except (LookupError, BinasciiError) as e:
            raise ValueError(e)

    @staticmethod
    def decode_string(user, value):
        '''
        To decode the url
        '''
        decoded_string = urlsafe_base64_decode(value).decode()
        if user.email == decoded_string.split(',')[0]:
            data = {
                'error':False,
                'message': decoded_string.split(',')[1]
            }
        else:
            data = {
                'error':True,
                'message': 'Error in url'
            }
        return data