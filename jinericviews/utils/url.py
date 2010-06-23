'''
Created on Jun 20, 2010

@author: brianjinwright
'''
def url_encode_list(value):
    url_var = ''
    for k,v in value.iteritems():
        
        for i in v:
            url_var += '%s=%s&' % (k,str(i))
    
    return url_var