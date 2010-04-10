'''
Created on Apr 6, 2010

@author: brianjinwright
'''
from django.shortcuts import render_to_response
from django.template.context import RequestContext
class BaseView(object):
    """Base Generic View"""
    template = None
    
    def __call__(self,request,extra_context=None,**kwargs):
        """
        Render a given template with any extra URL 
        parameters in the context as
        ``{{ params }}``.
        """
        dictionary = {'params': kwargs}
        for key, value in extra_context.items():
            if callable(value):
                dictionary[key] = value()
            else:
                dictionary[key] = value
        return render_to_response(
            self.template,
            dictionary,
            context_instance=RequestContext(request)
            )
    
    