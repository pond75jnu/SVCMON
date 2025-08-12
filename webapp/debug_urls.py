#!/usr/bin/env python
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'svcmon.settings')
django.setup()

from django.urls import reverse
from django.conf import settings
from django.urls.resolvers import URLResolver
from django.urls import get_resolver

def print_urls():
    """모든 URL 패턴 출력"""
    resolver = get_resolver()
    
    def get_urls(resolver, prefix=''):
        patterns = []
        for pattern in resolver.url_patterns:
            if isinstance(pattern, URLResolver):
                patterns.extend(get_urls(pattern, prefix + str(pattern.pattern)))
            else:
                patterns.append(prefix + str(pattern.pattern))
        return patterns
    
    urls = get_urls(resolver)
    endpoint_urls = [url for url in urls if 'endpoint' in url.lower()]
    
    print("엔드포인트 관련 URL 패턴:")
    for url in endpoint_urls:
        print(f"  {url}")
    
    # 특정 엔드포인트 URL 테스트
    try:
        chart_url = reverse('dashboard:endpoint_chart', args=[1])
        print(f"\n차트 페이지 URL: {chart_url}")
    except Exception as e:
        print(f"차트 URL 생성 오류: {e}")
        
    try:
        api_url = reverse('dashboard:endpoint_chart_api', args=[1])
        print(f"API URL: {api_url}")
    except Exception as e:
        print(f"API URL 생성 오류: {e}")

if __name__ == "__main__":
    print_urls()
