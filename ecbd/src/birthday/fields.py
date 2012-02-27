# -*- coding: utf-8 -*-
import logging
from django.forms.fields import CharField
from django.core import validators
from django.core.exceptions import ValidationError
from djangotoolbox import fields


class ListFormField(CharField):
    """
    Form field para ListField
        
    Los valores se almacenan en la base de datos como una lista
    de strings, y se muestran en el form como una cadena
    de valores separados por coma.        

    """

    def __init__(self,  *args, **kwargs):
        super(ListFormField, self).__init__(*args, **kwargs)
        
    def to_python(self, value):
        """
        Convierte una lista separada por coma
        a una lista de strings
        """
        if value in validators.EMPTY_VALUES:
            return []
        if isinstance(value, (list, tuple)):
            return value
        value = super(CharField, self).to_python(value.strip())
        try:
            items = value.rstrip(',').split(',')
            value = [item.strip() for item in items]
        except (ValueError, TypeError):
            raise ValidationError(self.error_messages['invalid'])
        return value
    
    def prepare_value(self, value):
        """
        Convierte la lista almacenada a un
        string separado por comas

        """
        if value is None or value == []:
            return ''
        if isinstance(value, basestring):
            return super(ListFormField, self).prepare_value(value)
        return ','.join(value)
    

class ListField(fields.ListField):
    """
    Clase auxiliar para definir un formfield

    """
    def formfield(self, **kwargs):
        defaults = {'form_class': ListFormField}
        defaults.update(kwargs)
        return super(ListField, self).formfield(**defaults)  
