# 📧 Gmail 앱 비밀번호 설정 (5분 완성)

## ❌ 이 에러가 났다면:

```
❌ 이메일 발송 실패: Application-specific password required
```

## ✅ 해결 방법

### 1️⃣ Google 계정 2단계 인증 활성화

**링크**: https://myaccount.google.com/security

1. "Google에 로그인하는 방법" 섹션
2. **"2단계 인증"** 클릭 → 설정 진행
3. 휴대전화 번호로 인증 코드 받기 설정

### 2️⃣ 앱 비밀번호 생성

**링크**: https://myaccount.google.com/apppasswords

1. "앱 선택" → **메일** 선택
2. "기기 선택" → **기타(맞춤 이름)** 선택
3. 이름 입력: `규제준수시스템`
4. **생성** 클릭
5. **16자리 비밀번호 복사** (예: `abcd efgh ijkl mnop`)

⚠️ **주의**: 이 비밀번호는 다시 볼 수 없으니 바로 복사하세요!

### 3️⃣ .env 파일 생성

프로젝트 루트에 `.env` 파일 생성:

```bash
# .env
EMAIL_USERNAME=당신의이메일@gmail.com
EMAIL_PASSWORD=abcdefghijklmnop
```

**중요**:
- 앱 비밀번호는 **공백 없이** 16자리로 입력
- 일반 Gmail 비밀번호가 아닙니다!

### 4️⃣ 서버 재시작

```bash
python run_server.py
```

### 5️⃣ 테스트

웹에서:
1. http://localhost:8000?demo=1 접속
2. "분석 시작" 클릭
3. "📧 담당자별 체크리스트 발송" 클릭

서버 로그 확인:
```bash
tail -f server.log | grep "📧"
```

성공 시:
```
✅ 이메일 발송 성공: eunsu0613@naver.com
✅ 이메일 발송 성공: woals424@naver.com
```

## 🔐 보안 주의사항

1. `.env` 파일은 절대 Git에 올리지 마세요
2. 앱 비밀번호는 누구에게도 공유하지 마세요
3. 필요 없으면 앱 비밀번호 삭제 (https://myaccount.google.com/apppasswords)

## 📝 .gitignore 확인

`.gitignore` 파일에 다음이 포함되어 있는지 확인:

```
.env
.env.*
!.env.example
```

## 🐛 문제 해결

### "앱 비밀번호 메뉴가 안 보여요"
→ 2단계 인증을 먼저 활성화하세요

### "이메일이 발송 안 돼요"
→ `.env` 파일 위치 확인 (프로젝트 루트에 있어야 함)
→ 앱 비밀번호를 공백 없이 입력했는지 확인
→ EMAIL_USERNAME이 올바른지 확인

### "스팸으로 분류돼요"
→ Gmail 일일 발송 제한: 500건
→ 처음 사용 시 소량으로 테스트 권장

## ✅ 체크리스트

- [ ] 2단계 인증 활성화
- [ ] 앱 비밀번호 생성 (16자리)
- [ ] `.env` 파일 생성 및 설정
- [ ] 서버 재시작
- [ ] 테스트 이메일 발송 확인
