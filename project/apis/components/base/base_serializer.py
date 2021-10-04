import json

from rest_framework import serializers
from django.apps import apps

class BaseSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        # Instantiate the superclass normally
        super(BaseSerializer, self).__init__(*args, **kwargs)
        self.inner_fields={}

        fields = self.get_param_fields() #self.context.get('fields', None) # self.context['request'].query_params.get('fields')
        if fields:
            if type(fields) == list and len(fields) >0:
                # Drop any fields that are not specified in the `fields` argument.
                allowed = set(fields)
                existing = set(self.fields.keys())
                for field_name in existing - allowed:
                        self.fields.pop(field_name)


    def get_param_fields(self, fields = []):
        if not fields:
            fields = self.context.get('fields', [])
        if fields:
            if not type(fields) == list: #Check for JSON String
                fields=self.extract_field_param(fields)
            if not type(fields) == list and ',' in fields:
                fields = fields.split(',')
                # fields = [item.strip() for item in fields]
        if fields:
            fields_name = []
            for field_name in fields:
                if isinstance(field_name, str):
                    # fields_name.append(field_name.strip())
                    fields_name.append(self.extract_field_param(field_name.strip()))
                elif isinstance(field_name, dict):
                    self.inner_fields.update(field_name)
                else:
                    error = {'message': 'Param "fields" either String or Dictionary'}
                    raise serializers.ValidationError(error)
            fields = fields_name
        return fields

    # python list of dictionary to string json
    def extract_field_param(self, str_param_value):
        try:
            fields_name = []
            jdata = json.loads(str_param_value)
            for d in jdata:
                if isinstance(d, str):
                    fields_name.append(d.strip())
                elif isinstance(d, dict):
                    # for key, value in d.iteritems():
                    #     print(key, value)
                    self.inner_fields.update(d)
                else:
                    error = {'message': 'Param "fields" either String or Dictionary'}
                    raise serializers.ValidationError(error)
            return fields_name
        except:
            # String could not be converted to JSON
            return str_param_value

    # def to_internal_value(self, data):
    #     super(BaseSerializer, self).to_internal_value(data)
    #
    # def to_representation(self, instance):
    #     super(BaseSerializer, self).to_representation(instance)

    def fetch_list(self, app_name, model_name, **kwargs):
        db_model = apps.get_model(app_name, model_name)
        return db_model.objects.filter(**kwargs)

    def date_str_format(self, dt, on_error= ""):
        try:
            return dt.strftime("%b %d, %Y")
        except:
            return on_error
