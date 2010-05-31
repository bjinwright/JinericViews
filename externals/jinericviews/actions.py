'''
Created on May 23, 2010

@author: brianjinwright
'''
from google.appengine.ext import db
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

class BaseAction(object):
    description = None
    name = None
    confirm_message = None
    def __call__(self,read_view,request,queryset):
        if not self.description:
            raise ValueError('You must specify a description')
        self.action(request, queryset)
    
    def action(self,request,queryset):
        pass
    
class DeleteAction(BaseAction):
    name = 'delete'
    description = 'Delete all selected'
    confirm_message = 'Are you sure you want '
    'to delete the following entries'
    def action(self,read_view,request,queryset):
        db.delete(queryset)
        return HttpResponseRedirect(reverse(read_view.read_url))
