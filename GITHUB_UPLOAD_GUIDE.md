# GitHub 업로드 가이드

## 1. GitHub에서 새 저장소 생성
1. https://github.com 에 접속하여 pond75jnu 계정으로 로그인
2. "New repository" 버튼 클릭
3. Repository name: SVCMON
4. Description: 전남대학교 웹사이트 모니터링 시스템
5. Public 또는 Private 선택
6. "Create repository" 클릭

## 2. 로컬에서 원격 저장소 연결 및 푸시
```bash
# 현재 디렉토리: D:\MyRepos\SVCMON
git remote add origin https://github.com/pond75jnu/SVCMON.git
git branch -M main
git push -u origin main
```

## 3. 보안 확인사항 ✅
- ✅ .env 파일은 .gitignore에 의해 제외됨
- ✅ .env.example 파일로 환경변수 템플릿 제공
- ✅ 데이터베이스 연결 정보는 환경변수로 분리
- ✅ SECRET_KEY도 환경변수로 분리
- ✅ 민감한 정보가 하드코딩되지 않음

## 4. 다른 개발자들을 위한 설정 안내
새로운 개발자가 프로젝트를 클론한 후:
1. `.env.example`을 `.env`로 복사
2. `.env` 파일에서 실제 데이터베이스 정보 입력
3. 가상환경 생성 및 패키지 설치
4. 마이그레이션 실행

이렇게 하면 보안이 유지되면서도 협업이 가능합니다.
