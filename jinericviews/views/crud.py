'''
Created on Apr 6, 2010

@author: brianjinwright
'''
import sys
from urllib import urlencode

from base import BaseView, get_app_label,\
get_model_kind, get_view_name

from jinericviews.forms import ActionForm, HiddenActionForm
from jinericviews.filters import BaseFilter
from jinericviews.utils.url import url_encode_list

#from django.template import loader, RequestContext
from django.http import HttpResponseRedirect
from django.core.exceptions import ImproperlyConfigured
from django.conf.urls.defaults import url, patterns, include
#from django.shortcuts import render_to_response

from google.appengine.ext.db.djangoforms import ModelForm, ModelFormMetaclass

from google.appengine.ext import db
from google.appengine.ext.db import polymodel
#from django.views.generic.list_detail import object_list
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse
from django.http import Http404

__all__ = [
    'GenericViewError',
    'ReadView',
    'redirect',
    'get_model_and_form_class',
    'CreateUpdateView',
    'JinericAdmin'
    ]
class GenericViewError(Exception):
    '''
    Generic Exception Class for JinericViews
    '''
    
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value) 

class ReadView(BaseView):
    '''
    Multi-action JinericView that handles reading, 
    filtering, and actions on objects. 
    
    @param paginate_by: How many objects to show per page
    @param template_object_name: The prefix for the template object
    @param allow_empty: Do you want to allow an empty queryset?
    @param create_view: Name of the create view url pattern
    @param update_view: Name of the update view url pattern
    @param delete_view: Name of the delete view url pattern
    @param action_view: Name of the action view url pattern
    @param action_complete_view: Name of the action complete view url pattern
    @param read_view: Name of the read view url pattern
    @param read_no_page_view: Name of the read no page view url pattern
    @param list_filters: List of BaseFilter objects to use on the filters section
    @param list_display: The attributes to show on the read view
    @param actions: The actions to use.
    '''
    
    paginate_by = 10
    template_object_name = 'object'
    allow_empty = True
    create_view = None
    update_view = None
    delete_view = None
    action_view = None
    action_complete_view = None
    read_view = None
    read_no_page_view = None
    list_filters = tuple()
    list_display = tuple()
    actions = None
    def __init__(self,model):
        self.model = model
        self.model_kind = get_model_kind(self.model)
        self.model_kind_lower = self.model_kind.lower()
        if not self.app_label:
            self.app_label = get_app_label(self.model)
    def __call__(
        self,
        request,
        page=1,
        extra_context={},
        action='read',
        **kwargs):
        #Check Authorization and if it is an HttpResponseRedirect redirect
        auth = self.check_auth(request)
        if isinstance(auth, HttpResponseRedirect):
            return auth
        
        page = int(page)
        queryset = self.get_queryset(request)
        extra_context = self.prepare_context(request,queryset,page,extra_context,action)
        return self.get_response(request,extra_context,action)
    
    def get_template(self,action='read'):
        tl = []
        
        if action in ('read','read_no_page'):
            if self.app_label:
                tl.insert(0, 'jinericviews/%s/read-view.html' % self.app_label)
            tl.append('jinericviews/read-view.html')
        if action in ('action','action-complete'):
            if self.app_label:
                tl.insert(0, 'jinericviews/%s/action-view.html' % self.app_label)
            tl.append('jinericviews/action-view.html')
        return self.template or tl
    
    def get_queryset(self,request):
        '''
        @summary: This method returns a the base 
        queryset used for the view. 
        @param request: Django request object.
        '''
        if not self.model:
            raise ValueError('You must specify a model')
        return self.model.all()
    
    def get_read_url(self):
        '''
        @summary: Returns the url patterns 
        for the read views.
        '''
        urlpatterns = patterns('',
            url(r'^%s/$' % (self.model_kind),
                self,
                name='%s_%s_read_no_page' % (self.app_label,self.model_kind)),
            url(r'^%s/(?P<page>\d+)/$' % (self.model_kind),
                self,
                name='%s_%s_read' % (self.app_label,self.model_kind)),
            url(r'^%s/action/$' % (self.model_kind),
                self,
                kwargs={'action':'action'},
                name='%s_%s_action' % (self.app_label,self.model_kind)),
            url(r'^%s/action/complete/$' % (self.model_kind),
                self,
                kwargs={'action':'action-complete'},
                name='%s_%s_action_complete' % (self.app_label,self.model_kind)),
        )
        
        return urlpatterns
    read_url = property(get_read_url)
    
    def get_filters(self,request,queryset):
        filter_list = list()
        selected_entries = dict()
        selected_filters = dict()
        for filter in self.list_filters:
            if isinstance(filter, BaseFilter):
                filter_ins = filter(request,queryset)
                filter_list.append(filter_ins.get('filter_obj',None))
                selected_entries.update(filter_ins.get('selected_entries',dict()))
                selected_values = filter_ins.get('selected_values',None)
                
                if selected_values:
                    selected_filters.update({filter.filter:selected_values})
        
        return {'filter_list':filter_list,
                'selected_filters':selected_filters,
                'selected_entries':url_encode_list(selected_entries)}
        
                
    def prepare_context(self,request,queryset,page,extra_context,action):
        
        for i in ('create','update','delete','read','read_no_page','action','action_complete'):
            if not getattr(self, '%s_view' % i, None):
                setattr(
                    self,
                    '%s_view' % i, 
                    get_view_name(
                        self.model,
                        i,
                        self.model_kind_lower,
                        self.app_label
                        )
                    )
        
        ac = None
        gg = dict()
        tt = []
        extra_context.update({'read_view':self.read_view,
                    'create_view':reverse(self.create_view),
                    'update_view':self.update_view,
                    'delete_view':self.delete_view,
                    'action_view':reverse(self.action_view),
                    'action_complete_view':reverse(self.action_complete_view),
                    'model_kind':self.model_kind,
                    'actions':self.actions
                    })
        if self.actions and isinstance(self.actions, list):
            ac = [('','- - - - - - - - - - - - - - - - -')]
            tt = [(i.name,i.description) for i in self.actions]
            for i in self.actions:
                gg.update({i.name:i})

            ac.extend(tt)
            rk = [(i.key(),i) for i in queryset]

        
        
        if action == 'action':
            if request.method == 'POST':
                action_form = HiddenActionForm(
                    request.POST,
                    request.FILES
                    )
                extra_context.update(dict(main_header='Action Confirmation'))
                action_form.fields.get('action',None).choices = ac
                action_form.fields.get('records',None).choices = rk
                
                if action_form.is_valid():
                    act = action_form.cleaned_data.get('action',None)
                    confirm_msg = gg.get(act).confirm_message
                    extra_context.update(dict(main_header=confirm_msg))
                    recs = action_form.cleaned_data.get('records',None)
                    recs = [db.get(i) for i in recs]
                    extra_context.update(
                        dict(
                            recs=recs,
                            form_action=reverse(self.action_complete_view
                                                )
                            )
                        )
                else:
                    extra_context.update(dict(form_action=reverse(self.action_view)))

            else:
                raise Http404
            
            extra_context.update(dict(action_form=action_form))
            return self.get_context(request,extra_context)
        
        
        if action == 'action-complete':
            if request.method == 'POST':
                action_form = HiddenActionForm(
                    request.POST,
                    request.FILES
                    )
                extra_context.update(dict(main_header='Action Confirmation'))
                action_form.fields.get('action',None).choices = ac
                action_form.fields.get('records',None).choices = rk
                
                if action_form.is_valid():
                    recs = action_form.cleaned_data.get('records')            
                    act = action_form.cleaned_data.get('action')
                    if act in gg:
                        act_class = gg.get(act)
                        acc = act_class()
                        return acc(request,self.read_no_page_view,recs)
                        
                    else:
                        raise Http404
                else:
                    extra_context.update(dict(form_action=reverse(self.action_view)))
            else:
                raise Http404
                
            return self.get_context(request,extra_context)
        
        if action == 'read':
            if self.actions:
                action_form = ActionForm()
                action_form.fields.get('action',None).choices = ac
                action_form.fields.get('records',None).choices = rk
                extra_context.update(dict(action_form=action_form))

            #Filters
            if self.list_filters:
                get_filters = self.get_filters(request, queryset)
                filters = get_filters.get('filter_list',None)
                selected_entries = get_filters.get('selected_entries',None)
                selected_filters = get_filters.get('selected_filters',dict())
                if len(selected_filters) > 0:
                    for k,v in selected_filters.iteritems():
                        queryset = queryset.filter("%s in"% k,v)
                
                if len(filters) > 0:
                    extra_context.update(dict(list_filters=filters,selected_entries=selected_entries))
                    
            
            if request.GET.get('view_all','false') == 'true':
                extra_context.update({
                    '%s_list' % self.template_object_name: queryset,
                    'is_paginated': False,
                    'list_display':self.list_display,
                    'main_header': '%s Information' % (self.model_kind),
                    'total_records':queryset.count,
                })
                if not self.allow_empty and len(queryset) == 0:
                    raise Http404
                return self.get_context(request,extra_context)
            
            #Pagination
            
            paginator = Paginator(queryset, self.paginate_by)
            if self.paginate_by:
                paginator = Paginator(queryset, self.paginate_by, allow_empty_first_page=self.allow_empty)
            try:
                page_number = int(page)
            except ValueError:
                if page == 'last':
                    page_number = paginator.num_pages
                else:
                    # Page is not 'last', nor can it be converted to an int.
                    raise Http404
            try:
                page_obj = paginator.page(page_number)
            except InvalidPage:
                page_obj = paginator.page(1)
            
            extra_context.update({
                '%s_list' % self.template_object_name: page_obj.object_list,
                'list_display':self.list_display,
                'is_paginated': paginator.num_pages > 1,
                'results_per_page': self.paginate_by,
                'has_next': paginator.page < paginator.num_pages - 1,
                'has_previous': paginator.page > paginator.num_pages + 1,
                'total_records':paginator._get_count,
                'app_label':self.app_label,
                'page': page,
                'next': page + 1,
                'previous': page - 1,
                'read_no_page_view':reverse(self.read_no_page_view),
                'num_pages': paginator.num_pages,
                'pages': paginator._get_page_range,
                'main_header': '%s Information' % (self.model_kind)
            })
            if not self.allow_empty and len(queryset) == 0:
                raise Http404
            return self.get_context(request,extra_context)
    
def redirect(post_save_redirect, obj):
    """
    Returns a HttpResponseRedirect to ``post_save_redirect``.

    ``post_save_redirect`` should be a string, and can contain named string-
    substitution place holders of ``obj`` field names.

    If ``post_save_redirect`` is None, then redirect to ``obj``'s URL returned
    by ``get_absolute_url()``.  If ``obj`` has no ``get_absolute_url`` method,
    then raise ImproperlyConfigured.

    This function is meant to handle the post_save_redirect parameter to the
    ``create_object`` and ``update_object`` views.
    """
    if post_save_redirect:
        return HttpResponseRedirect(post_save_redirect % obj.key())
    elif hasattr(obj, 'get_absolute_url'):
        return HttpResponseRedirect(obj.get_absolute_url())
    else:
        raise ImproperlyConfigured(
            "No URL to redirect to.  Either pass a post_save_redirect"
            " parameter to the generic view or define a get_absolute_url"
            " method on the Model.")
def get_model_and_form_class(model, form_class):
    """
    Returns a model and form class based on the model and form_class
    parameters that were passed to the generic view.

    If ``form_class`` is given then its associated model will be returned along
    with ``form_class`` itself.  Otherwise, if ``model`` is given, ``model``
    itself will be returned along with a ``ModelForm`` class created from
    ``model``.
    """

    if form_class:
        return form_class._meta.model, form_class
    if model:
        # The inner Meta class fails if model = model is used for some reason.
        tmp_model = model
        # TODO: we should be able to construct a ModelForm without creating
        # and passing in a temporary inner class.
        
        if issubclass(model,polymodel.PolyModel):
            class Meta:
                model = tmp_model
                exclude = ['_class']
        else:
            class Meta:
                model = tmp_model
        class_name = model.__name__ + 'Form'
        form_class = ModelFormMetaclass(
            class_name,
            (ModelForm,),
            {'Meta': Meta}
            )
        return model, form_class
    raise GenericViewError(
        "Generic view must be called with either a model or"
        " form_class argument.")
    
class CreateUpdateView(BaseView):
    form_class = None
    post_create_redirect = None
    post_create_append_key = False
    post_update_redirect = None
    post_update_append_key = False
    post_delete_redirect = None
    post_delete_append_key = False
    delete_view = None
    read_no_page_view = None
    def __init__(self,model):
        self.model = model
        self.model_kind = get_model_kind(self.model)
        if not self.app_label:
            self.app_label = get_app_label(self.model)
                    
    
    def __call__(
        self,
        request,
        action='create',
        extra_context={},
        update_object = None,
        object_key = None,
        **kwargs):
        

        auth = self.check_auth(request)
        if isinstance(auth, HttpResponseRedirect):
            return auth
        extra_values = self.get_extra_values(request)
        extra_context = self.prepare_context(
            request,
            extra_context,
            extra_values,
            action,
            update_object,
            object_key)
        return self.get_response(request,extra_context,action) 
    
    def get_extra_values(self,request):
        pass
    
    def get_template(self,action='create'):
        tl = []
        if action in ('create','update'):
            if self.app_label:
                tl.insert(0, 'jinericviews/%s/create-update-view.html' % self.app_label)
            tl.append('jinericviews/create-update-view.html')
        if action == 'delete':
            if self.app_label:
                tl.insert(0,'jinericviews/%s/delete-view.html' % self.app_label)
            tl.append('jinericviews/delete-view.html')
        return self.template or tl
    
    def get_create_url(self):
        
        urlpatterns = patterns('',
            url(r'^%s/add/$' % (self.model_kind),
                self,
                name='%s_%s_create' % (self.app_label,self.model_kind)),
        )
        
        return urlpatterns
    create_url = property(get_create_url)
    
    def get_update_url(self):
        urlpatterns = patterns('',
            url(r'^%s/update/(?P<object_key>[-\w]+)/$' % (self.model_kind),
                self.__call__,
                name='%s_%s_update' % (self.app_label,self.model_kind),
                kwargs={'action':'update'}
                ),
        )
        
        return urlpatterns
    update_url = property(get_update_url)
    
    def get_delete_url(self):
        urlpatterns = patterns('',
            url(r'^%s/delete/(?P<object_key>[-\w]+)/$' % (self.model_kind),
                self.__call__,
                name='%s_%s_delete' % (self.app_label,self.model_kind),
                kwargs={'action':'delete'}
                ),
        )
        
        return urlpatterns
    
    delete_url = property(get_delete_url)
    
    def check_update_perm(self,request):
        pass
    
    def check_create_perm(self,request):
        pass
    
    def check_delete_perm(self,request):
        pass
    
    def get_object_det(self,request,action,update_object,object_key):
        if update_object != None:
            obj_det = update_object
        elif object_key:
            obj_det = db.get(object_key)
        if hasattr(obj_det, '__unicode__'):
            ms = obj_det.__unicode__()
        else:
            ms = '%s Object' % (self.model_kind)
        if action == 'update': 
            main_header = 'Update %s' % (ms)
        if action == 'delete':
            main_header = 'Delete %s?' % ms
        return {'main_header':main_header,'obj_det':obj_det}
    
    def redirect(
        self,
        request,
        action,
        new_object=None,
        ):
        if action == 'create':
            post_action_redirect = self.post_create_redirect
            post_action_append_key = self.post_create_append_key
        if action == 'update':
            post_action_redirect = self.post_update_redirect
            post_action_append_key = self.post_update_append_key
        if action == 'delete':
            post_action_redirect = self.post_delete_redirect
            post_action_append_key = self.post_delete_append_key
            
        if not post_action_redirect:
            try:
                post_action_redirect = reverse(
                    '%s_%s_read_no_page' % (self.app_label,self.model_kind.lower()))
            except:
                try:
                    post_action_redirect = reverse('%s_%s_update' % \
                        (self.app_label,self.model_kind.lower()),args=[new_object.key()])
                except:
                    raise ValueError('Please specify a post_save_redirect')
                    
        if post_action_redirect and post_action_append_key and action != None:
            return HttpResponseRedirect(
                post_action_redirect + str(new_object.key()))
            
        if post_action_redirect and not post_action_append_key:
            return HttpResponseRedirect(post_action_redirect)
        
        elif hasattr(new_object, 'get_absolute_url'):
            return HttpResponseRedirect(
                new_object.get_absolute_url()
                )           
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to.  Either pass a post_create_redirect,"
                " post_update_redirect, or a post_delete_redirect"
                " parameter to the generic view or define a get_absolute_url"
                " method on the Model.")
            
    def prepare_context(
        self,
        request,
        extra_context,
        extra_values,
        action,
        update_object,
        object_key
        ):
        """
        Generic object-creation function.
    
        Templates: ``<app_label>/<model_name>_form.html``
        Context:
            form
                the form for the object
        """
        
        model, form_class = get_model_and_form_class(
            self.model,
            self.form_class
            )
        
        extra_context.update(dict(model_kind=self.model_kind))
        if not self.delete_view:
            self.delete_view = "%s_%s_delete" % (self.app_label,self.model_kind.lower())
        if not self.read_no_page_view:
            self.read_no_page_view = "%s_%s_read_no_page" % (self.app_label,self.model_kind.lower())
        extra_context.update({'delete_view':self.delete_view,
                              'read_no_page_view':reverse(self.read_no_page_view)})
        if action == 'create':
            self.check_create_perm(request)
            extra_context.update(
                    {'main_header':'Create New %s' % (self.model_kind)}
                )
        if action == 'delete':
            self.check_delete_perm(request)
            form = None
            gdet = self.get_object_det(request, action, update_object, object_key)
            obj_det = gdet.get('obj_det',None)
            extra_context.update(
                {'main_header':gdet.get('main_header','')})
        
        if action == 'update':
            self.check_update_perm(request)
            gdet = self.get_object_det(request, action, update_object, object_key)
            obj_det = gdet.get('obj_det',None)
            extra_context.update(
                {'main_header':gdet.get('main_header',''),
                 'i':obj_det.key()})
            
        if request.method == 'POST':
            if action == 'delete':
                db.delete(obj_det)
                return self.redirect(request, action, self.model_kind)
            if action == 'create':
                form = form_class(
                    request.POST,
                    request.FILES
                    )
            if action == 'update':
                form = form_class(
                    request.POST,
                    request.FILES,
                    instance=obj_det
                    )
            if action in ('update','create'):    
                if form.is_valid():                
                    new_object = form.save(commit=False)
                
                    if extra_values and len(extra_values) > 0:
                        for k, v in extra_values.iteritems():
                            setattr(new_object, k, v)
                    new_object.save()
                    return self.redirect(request, action, new_object)
        else:
            if action == 'create':
                form = form_class()
            elif action == 'update':
                form = form_class(
                    instance=obj_det
                    )
            
                
        if form:            
            extra_context.update(dict(form=form))
        extra_context.update(dict(action=action,app_label=self.app_label))
        return self.get_context(request,extra_context)        



class JinericAdmin(object):
    #Generic Options
    read_template = None
    create_template = None
    update_template = None
    login_required = False
    app_label = None
    create_view_class = CreateUpdateView
    read_view_class = ReadView
    update_view_class = CreateUpdateView
    delete_view_class = CreateUpdateView
    
    #Read Options
    allow_empty = False
    paginate_by = 10
    template_object_name = 'object'
    create_view = None
    update_view = None
    read_view = None
    read_no_page_view = None
    list_filters = tuple()
    list_display = tuple()
    actions = None
    #Create Update Options
    form_class = None
    post_create_redirect = None
    post_create_append_key = False
    post_update_redirect = None
    post_update_append_key = False
    
    def __init__(self,model):
        self.model = model
    
    def get_read_view(self):
        rv = self.read_view_class(self.model)
        if self.read_template:
            setattr(rv, 'template', self.read_template)
        if self.login_required:
            setattr(rv, 'login_required', self.login_required)
        if self.app_label:
            setattr(rv, 'app_label', self.app_label)
        if self.allow_empty:
            setattr(rv, 'allow_empty', self.allow_empty)
        if self.paginate_by:
            setattr(rv, 'paginate_by', self.paginate_by)
        if self.template_object_name:
            setattr(rv, 'template_object_name',self.template_object_name)
        if self.create_view:
            setattr(rv, 'create_view', self.create_view)
        if self.update_view:
            setattr(rv, 'update_view', self.update_view)
        if self.read_view:
            setattr(rv, 'read_view', self.read_view)
        if self.read_no_page_view:
            setattr(rv, 'read_no_page_view', self.read_no_page_view)
        if self.list_filters:
            setattr(rv, 'list_filters', self.list_filters)
        if self.actions:
            setattr(rv, 'actions', self.actions)
        if self.list_display:
            setattr(rv, 'list_display', self.list_display)
        return rv
    rv = property(get_read_view)
    
    def get_create_view(self):
        cv = self.create_view_class(self.model)
        if self.create_template:
            setattr(cv, 'template', self.create_template)
        if self.login_required:
            setattr(cv, 'login_required', self.login_required)
        if self.app_label:
            setattr(cv, 'app_label', self.app_label)
        if self.form_class:
            setattr(cv, 'form_class', self.form_class)
        if self.post_create_redirect:
            setattr(cv, 'post_create_redirect', self.post_create_redirect)
        if self.post_create_append_key:
            setattr(cv, 'post_create_append_key', self.post_create_append_key)
        return cv    
    cv = property(get_create_view)
    
    def get_update_view(self):
        uv = self.update_view_class(self.model)
        if self.update_template:
            setattr(uv, 'template', self.update_template)
        if self.login_required:
            setattr(uv, 'login_required', self.login_required)
        if self.app_label:
            setattr(uv, 'app_label', self.app_label)
        if self.form_class:
            setattr(uv, 'form_class', self.form_class)
        if self.post_update_redirect:
            setattr(uv, 'post_update_redirect', self.post_update_redirect)
        if self.post_update_append_key:
            setattr(uv, 'post_update_append_key', self.post_update_append_key)
        return uv    
    uv = property(get_update_view)
    
    def get_delete_view(self):
        dv = self.delete_view_class(self.model)
        if self.update_template:
            setattr(dv, 'template', self.update_template)
        if self.login_required:
            setattr(dv, 'login_required', self.login_required)
        if self.app_label:
            setattr(dv, 'app_label', self.app_label)
        if self.form_class:
            setattr(dv, 'form_class', self.form_class)
        if self.post_update_redirect:
            setattr(dv, 'post_update_redirect', self.post_update_redirect)
        if self.post_update_append_key:
            setattr(dv, 'post_update_append_key', self.post_update_append_key)
        return dv    
    dv = property(get_delete_view)
    
    def get_urls(self):
        urlpatterns = patterns('',
            url(r'^', include(self.cv.create_url)),
            url(r'^', include(self.uv.update_url)),
            url(r'^', include(self.dv.delete_url)),
            url(r'^', include(self.rv.read_url)),
        )
        
        return urlpatterns
    
    urls = property(get_urls)