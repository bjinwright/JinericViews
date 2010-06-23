'''
Created on May 23, 2010

@author: brianjinwright
'''
from django import forms

class ActionForm(forms.Form):
    action = forms.ChoiceField()
    records = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple)
    
class HiddenActionForm(forms.Form):
    action = forms.CharField(widget=forms.HiddenInput)
    records = forms.MultipleChoiceField(widget=forms.MultipleHiddenInput)