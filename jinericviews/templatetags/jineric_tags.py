'''
Created on May 11, 2010

@author: brianjinwright
'''
from django.template import Library
from django.template.defaultfilters import stringfilter
from django.core.urlresolvers import reverse
register = Library()

@register.filter('get_value')
def get_value(value,arg):
    if hasattr(value, arg):
        return getattr(value, arg)
    return ''

@register.filter('make_header')
@stringfilter       
def make_header(value):
    return value.replace('_',' ').title()

@register.filter('template_reverse')
def template_reverse(value,key):
#    try:
    return reverse(value, args=[key])
#    except:
#        return ''

@register.filter('remove_filter')
def remove_filter(value,arg):
    return value.replace(arg,'').replace('&&','&')
    