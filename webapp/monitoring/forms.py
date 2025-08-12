from django import forms
from .models import NetworkGroup, Domain, Endpoint


# 공통 입력 필드 스타일
INPUT_CLASSES = 'mt-1 block w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 ease-in-out'
SELECT_CLASSES = 'mt-1 block w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 ease-in-out'
TEXTAREA_CLASSES = 'mt-1 block w-full px-4 py-3 border border-gray-300 rounded-lg shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 ease-in-out resize-none'


class NetworkGroupForm(forms.ModelForm):
    """망구분 폼"""
    
    class Meta:
        model = NetworkGroup
        fields = ['name', 'note']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '망구분명을 입력하세요 (예: 교내망, KT망, LG망)'
            }),
            'note': forms.Textarea(attrs={
                'class': TEXTAREA_CLASSES,
                'placeholder': '비고를 입력하세요',
                'rows': 3
            })
        }


class DomainForm(forms.ModelForm):
    """도메인 폼"""
    
    class Meta:
        model = Domain
        fields = ['network_group', 'domain', 'site_name', 'owner_name', 'owner_contact', 'is_active', 'note']
        widgets = {
            'network_group': forms.Select(attrs={'class': SELECT_CLASSES}),
            'domain': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '도메인을 입력하세요 (예: www.jnu.ac.kr)'
            }),
            'site_name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '사이트명을 입력하세요'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '담당자명을 입력하세요'
            }),
            'owner_contact': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '담당자 연락처를 입력하세요 (예: 062-530-0000, abc@jnu.ac.kr)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
            'note': forms.Textarea(attrs={
                'class': TEXTAREA_CLASSES,
                'placeholder': '비고를 입력하세요',
                'rows': 3
            })
        }


class EndpointForm(forms.ModelForm):
    """엔드포인트 폼"""
    
    class Meta:
        model = Endpoint
        fields = [
            'domain', 'url', 'note', 'poll_interval_sec', 'is_enabled'
        ]
        widgets = {
            'domain': forms.Select(attrs={'class': SELECT_CLASSES}),
            'url': forms.URLInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'URL을 입력하세요 (예: https://www.jnu.ac.kr/main.do)'
            }),
            'note': forms.Textarea(attrs={
                'class': TEXTAREA_CLASSES,
                'placeholder': '비고를 입력하세요',
                'rows': 3
            }),
            'poll_interval_sec': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': '호출주기(초)를 입력하세요 (기본: 300)',
                'min': 30,
                'max': 3600
            }),
            'is_enabled': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'domain': '상위 도메인',
            'url': 'URL',
            'note': '비고',
            'poll_interval_sec': '호출 주기 (초)',
            'is_enabled': '활성 상태',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['poll_interval_sec'].initial = 300
        
        # 도메인 선택 시 망구분 정보도 표시하도록 수정
        domain_choices = []
        for domain in Domain.objects.select_related('network_group').all():
            label = f"{domain.domain} ({domain.site_name}) - {domain.network_group.name}"
            domain_choices.append((domain.id, label))
        
        self.fields['domain'].choices = [('', '도메인을 선택하세요')] + domain_choices


class BulkSettingsForm(forms.Form):
    """일괄 설정 폼 (개선된 버전)"""
    
    ACTION_CHOICES = [
        ('enable', '활성화'),
        ('disable', '비활성화'),
        ('update_interval', '폴링 간격 변경'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': SELECT_CLASSES,
            'id': 'id_action'
        }),
        label='작업 선택'
    )
    
    endpoints = forms.ModelMultipleChoiceField(
        queryset=Endpoint.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        label='대상 엔드포인트'
    )
    
    poll_interval_sec = forms.IntegerField(
        min_value=30,
        max_value=3600,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': '새로운 폴링 간격(초)',
            'id': 'id_poll_interval_sec'
        }),
        label='폴링 간격 (초)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        poll_interval_sec = cleaned_data.get('poll_interval_sec')
        
        if action == 'update_interval' and not poll_interval_sec:
            raise forms.ValidationError('폴링 간격 변경을 선택한 경우 새로운 간격을 입력해야 합니다.')
        
        return cleaned_data


class CloneNetworkGroupForm(forms.Form):
    """망구분 복제 폼 (개선된 버전)"""
    
    source_network_group = forms.ModelChoiceField(
        queryset=NetworkGroup.objects.all(),
        widget=forms.Select(attrs={'class': SELECT_CLASSES}),
        label='복제할 망구분'
    )
    
    new_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': '새로운 망구분명을 입력하세요'
        }),
        label='새로운 망구분명'
    )
    
    copy_domains = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        label='도메인도 함께 복제'
    )
    
    copy_endpoints = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        label='엔드포인트도 함께 복제'
    )
    
    def clean_new_name(self):
        new_name = self.cleaned_data['new_name']
        if NetworkGroup.objects.filter(name=new_name).exists():
            raise forms.ValidationError('이미 존재하는 망구분명입니다.')
        return new_name
