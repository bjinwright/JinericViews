'''
Created on Jun 6, 2010
@summary: 
@author: brianjinwright
'''
from google.appengine.ext import db
from urllib import urlencode
class FilterEntryObj(object):
    def __init__(self,url_var,url_var_value,value,label,selected):
        '''
        @summary: This object record whether a 
        filter is selected, the value, the label,
        and the url variable.
        @param url_var:
        @param value:
        @param label:
        @param selected:
        '''
        self.url_var = url_var
        self.url_var_value = url_var_value
        self.label = label
        self.value = value
        self.selected = selected

class FilterObj(object):
    def __init__(self,verbose_name,entries):
        '''
        @summary: This object holds the filter info 
        like verbose name and a list of the entries.
        @param verbose_name: User-friendly version of the filter name
        @param entries: A list of the FilterEntryObj objects.
        '''
        self.verbose_name = verbose_name
        self.entries = entries
        
class BoolConverter(object):
    def __init__(self,value):
        self.value = value
    @property
    def get_item(self):
        if self.value == 'True':
            return True
        else:
            return False
    
class KeyConverter(BoolConverter):
    @property
    def get_item(self):
        try:
            return db.Key(self.value)
        except:
            return None
    
class BaseFilter(object):
    value_type = None
    def __init__(self,filter,verbose_name):
        self.filter = filter
        self.verbose_name = verbose_name
    def __call__(self,request,queryset):
        return self.get_entries(request,queryset)
    
    def get_entries(self,request,queryset):
        raise NotImplementedError()
    
    def is_selected(self,request,queryset,choice):
        gg = request.GET.getlist(self.url_var)
        tt = [self.value_type(i).get_item for i in gg]
        if choice in tt:
            return True
        return False
            
    @property
    def url_var(self):
        return "filter_%s" % \
        (self.filter)
    
class BooleanFilter(BaseFilter):
    value_type = BoolConverter
    def get_entries(self,request,queryset):
        entries = list()
        selected_values = list()
        for i in [True,False]:            
            is_selected = self.is_selected(request, queryset, i)
            url_var_value = '%s=%s' % (self.url_var,unicode(i))
            if is_selected:
                selected_values.append(i)
            entries.append(FilterEntryObj(self.url_var,url_var_value, i, i, is_selected))
        selected_entries = {self.url_var:[str(i) for i in selected_values]}
        return {'filter_obj':FilterObj(self.verbose_name, set(entries)),
                'selected_entries':selected_entries,
                'selected_values':selected_values}
    
class KeyFilter(BaseFilter):
    value_type = KeyConverter
    def get_entries(self,request,queryset):
        return self.get_filters(request,queryset)
        
    def get_filters(self,request,queryset):
        filter_list = list()
        key_list = list()
        selected_values = list()
        for i in queryset:
            #Get filtered attribute off of queryset object.
            ga = getattr(i, self.filter)
            
            if isinstance(ga, list):
                for at in ga:
                    string_key = str(at)
                    if string_key not in key_list:
                        #Append the string value to the key_list create a set of unique keys
                        key_list.append(string_key)
                        #Convert the string keys to data objects.
                        gg = db.get(at)
                        url_var_value = '%s=%s' % (self.url_var,string_key)
                        is_selected = self.is_selected(request, queryset, at)
                        if is_selected:
                            
                            selected_values.append(at)
                        filter_list.append(FilterEntryObj(self.url_var,url_var_value,string_key, gg, is_selected))
            else:
                #If the model field is not a KeyListProperty field and just a Reference Key field
                gg = db.get(ga)
                string_key = str(ga)
                url_var_value = '%s=%s' % (self.url_var,string_key)
                is_selected = self.is_selected(request, queryset, string_key)
                if is_selected:
                    selected_values.append(at)
                filter_list.append(FilterEntryObj(self.url_var,url_var_value, string_key, gg, is_selected))
        selected_entries = {self.url_var:[str(i) for i in selected_values]}
        
        return {'filter_obj': FilterObj(self.verbose_name,filter_list),
                'selected_entries':selected_entries,
                'selected_values':selected_values}