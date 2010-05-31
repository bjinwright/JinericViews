'''
Created on May 23, 2010

@author: brianjinwright
'''
from django import forms

class ActionForm(forms.Form):
    action = forms.ChoiceField()
    records = forms.ChoiceField(widget=forms.SelectMultiple)