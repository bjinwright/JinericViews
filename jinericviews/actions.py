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
    def __call__(self,request,read_view,keys):
        if not self.description:
            raise ValueError('You must specify a description')
        return self.action(request,read_view,keys)
    
    def action(self,request,read_view,keys):
        pass
    
class DeleteAction(BaseAction):
    name = 'delete'
    description = 'Delete all selected'
    confirm_message = 'Sure you want '\
    'to delete the following entries?'
    def action(self,request,read_view,keys):
        db.delete(keys)
        return HttpResponseRedirect(reverse(read_view))
