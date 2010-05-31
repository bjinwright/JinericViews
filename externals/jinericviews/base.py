'''
Created on Apr 6, 2010

@author: brianjinwright
'''
import sys
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.http import HttpResponseRedirect
from google.appengine.api import users
#from crud import ReadView, CreateUpdateView, JinericAdmin
from google.appengine.ext.db import polymodel

def get_model_kind(model):
    '''
    @summary: Returns the string name of the model.
    @param model: Model instance
    '''
    if issubclass(model,polymodel.PolyModel):
        model_kind = model.class_name().lower()
    else:
        model_kind = model.kind().lower()
    return model_kind
def get_app_label(model):
    '''
    @summary: Returns the closest module name as the "app_label"
    @param model: Model instance
    '''
    model_module = sys.modules[model.__module__]
    app_label = model_module.__name__.split('.')[-2]
    return app_label
def get_view_name(model,view_type,model_kind=None,app_label=None):
    '''
    @summary: Returns the viewname for use with Django's reverse function.
    @param model: Model instance
    @param view_type: Type of view (ex. read, create, delete, and update). No spaces.
    '''
    if model_kind and app_label:
        return '%s_%s_%s' % (app_label,model_kind,view_type)
    if not isinstance(view_type, str):
        raise ValueError("view_type must be a string")
    model_kind = get_model_kind(model)
    app_label = get_app_label(model)
    return '%s_%s_%s' % (app_label,model_kind,view_type)
class BaseView(object):
    """Base Generic View"""
    template = None
    login_required = False
    app_label = None
    def __call__(self,request,extra_context={},**kwargs):
        auth = self.check_auth(request)
        if isinstance(auth, HttpResponseRedirect):
            return auth
        extra_context = self.prepare_context(request, extra_context)
        return self.get_response(request,extra_context)
    def prepare_context(self,request,extra_context):
        return self.get_context(request, extra_context)
    def get_context(self,request,extra_context):
        dictionary = dict()
        for key, value in extra_context.items():
            if callable(value):
                dictionary[key] = value()
            else:
                dictionary[key] = value
        return dictionary
    def check_auth(self,request):
        if self.login_required and not users.get_current_user():
            return HttpResponseRedirect(
                users.create_login_url(
                    request.path
                    )
                )
        else:
            return None
    
    def get_template(self,action):
        tl = []
        if self.app_label:
            tl.insert(0, 'jinericviews/%s/base-view.html')
        tl.append('jinericviews/base-view.html')
        return self.template or tl
    
    def get_response(self,request,extra_context,action=None):
        """
        Render a given template with any extra URL 
        parameters in the context as
        ``{{ params }}``.
        """
        if isinstance(extra_context, HttpResponseRedirect):
            return extra_context
        return render_to_response(
            self.get_template(action),
            extra_context,
            context_instance=RequestContext(request)
            )
        
#class HomeView(BaseView):
#    def __init__(self,views):
#        self.views = views
#    def prepare_context(self,request,extra_context):
#        if isinstance(self.views, dict):
#            for k,v in self.views.iteritems():
#                if isinstance(v, ReadView):
#                    viewname = get_view_name(v.model, 'read')
#                    
#                    
#        else:
#            raise ValueError("Views argument should be a dictionary")