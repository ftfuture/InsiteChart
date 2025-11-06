# 국제화(i18n) 전략

## 1. 개요

### 1.1 국제화의 중요성

InsiteChart 플랫폼은 글로벌 금융 데이터를 다루므로 다국어 지원은 필수적입니다. 사용자가 자신의 언어로 플랫폼을 사용할 수 있도록 함으로써 사용자 경험을 향상하고, 글로벌 시장 진출을 가속화할 수 있습니다.

### 1.2 국제화 목표

1. **다국어 지원**: 영어, 한국어, 일본어, 중국어(간체/번체), 스페인어, 프랑스어 등 주요 언어 지원
2. **문화적 적응**: 날짜/시간 형식, 통화, 숫자 형식 등 지역별 맞춤
3. **동적 언어 전환**: 런타임 언어 전환 및 사용자 언어 설정 저장
4. **콘텐츠 현지화**: UI 텍스트, 에러 메시지, 이메일 템플릿 등 현지화
5. **SEO 최적화**: 다국어 URL 구조 및 메타데이터 지원

## 2. 국제화 아키텍처

### 2.1 다계층 국제화 구조

```python
# i18n/i18n_manager.py
import asyncio
import json
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging
import gettext
import locale
from pathlib import Path

class Language(Enum):
    """지원 언어"""
    ENGLISH = "en"
    KOREAN = "ko"
    JAPANESE = "ja"
    CHINESE_SIMPLIFIED = "zh-CN"
    CHINESE_TRADITIONAL = "zh-TW"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"

class LocaleConfig:
    """로케일 설정"""
    
    SUPPORTED_LOCALES = {
        Language.ENGLISH: {
            "code": "en-US",
            "name": "English",
            "native_name": "English",
            "date_format": "%Y-%m-%d",
            "time_format": "%H:%M:%S",
            "datetime_format": "%Y-%m-%d %H:%M:%S",
            "currency": "USD",
            "number_format": {
                "decimal_separator": ".",
                "thousands_separator": ","
            },
            "rtl": False
        },
        Language.KOREAN: {
            "code": "ko-KR",
            "name": "Korean",
            "native_name": "한국어",
            "date_format": "%Y년 %m월 %d일",
            "time_format": "%H시 %M분 %S초",
            "datetime_format": "%Y년 %m월 %d일 %H시 %M분 %S초",
            "currency": "KRW",
            "number_format": {
                "decimal_separator": ".",
                "thousands_separator": ","
            },
            "rtl": False
        },
        Language.JAPANESE: {
            "code": "ja-JP",
            "name": "Japanese",
            "native_name": "日本語",
            "date_format": "%Y年%m月%d日",
            "time_format": "%H:%M:%S",
            "datetime_format": "%Y年%m月%d日 %H:%M:%S",
            "currency": "JPY",
            "number_format": {
                "decimal_separator": ".",
                "thousands_separator": ","
            },
            "rtl": False
        },
        Language.CHINESE_SIMPLIFIED: {
            "code": "zh-CN",
            "name": "Chinese (Simplified)",
            "native_name": "简体中文",
            "date_format": "%Y年%m月%d日",
            "time_format": "%H:%M:%S",
            "datetime_format": "%Y年%m月%d日 %H:%M:%S",
            "currency": "CNY",
            "number_format": {
                "decimal_separator": ".",
                "thousands_separator": ","
            },
            "rtl": False
        },
        Language.CHINESE_TRADITIONAL: {
            "code": "zh-TW",
            "name": "Chinese (Traditional)",
            "native_name": "繁體中文",
            "date_format": "%Y年%m月%d日",
            "time_format": "%H:%M:%S",
            "datetime_format": "%Y年%m月%d日 %H:%M:%S",
            "currency": "TWD",
            "number_format": {
                "decimal_separator": ".",
                "thousands_separator": ","
            },
            "rtl": False
        },
        Language.SPANISH: {
            "code": "es-ES",
            "name": "Spanish",
            "native_name": "Español",
            "date_format": "%d/%m/%Y",
            "time_format": "%H:%M:%S",
            "datetime_format": "%d/%m/%Y %H:%M:%S",
            "currency": "EUR",
            "number_format": {
                "decimal_separator": ",",
                "thousands_separator": "."
            },
            "rtl": False
        },
        Language.FRENCH: {
            "code": "fr-FR",
            "name": "French",
            "native_name": "Français",
            "date_format": "%d/%m/%Y",
            "time_format": "%H:%M:%S",
            "datetime_format": "%d/%m/%Y %H:%M:%S",
            "currency": "EUR",
            "number_format": {
                "decimal_separator": ",",
                "thousands_separator": " "
            },
            "rtl": False
        }
    }

@dataclass
class TranslationKey:
    """번역 키"""
    key: str
    context: Optional[str] = None
    plural: bool = False
    description: Optional[str] = None

class I18nManager:
    """국제화 관리자"""
    
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = Path(translations_dir)
        self.logger = logging.getLogger(__name__)
        
        # 번역 데이터 캐시
        self.translations_cache: Dict[Language, Dict[str, str]] = {}
        
        # 현재 언어 설정
        self.current_language = Language.ENGLISH
        self.fallback_language = Language.ENGLISH
        
        # 번역 로드
        self._load_translations()
    
    def _load_translations(self):
        """번역 파일 로드"""
        
        for language in Language:
            try:
                translations = self._load_language_translations(language)
                self.translations_cache[language] = translations
                self.logger.info(f"Loaded {len(translations)} translations for {language.value}")
            except Exception as e:
                self.logger.error(f"Failed to load translations for {language.value}: {str(e)}")
                self.translations_cache[language] = {}
    
    def _load_language_translations(self, language: Language) -> Dict[str, str]:
        """특정 언어 번역 로드"""
        
        translations = {}
        
        # 번역 파일 경로
        translation_file = self.translations_dir / f"{language.value}.json"
        
        if not translation_file.exists():
            self.logger.warning(f"Translation file not found: {translation_file}")
            return {}
        
        try:
            with open(translation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 평탈화된 번역 데이터 처리
                for key, value in data.items():
                    if isinstance(value, str):
                        translations[key] = value
                    elif isinstance(value, dict):
                        # 복수형 및 컨텍스트 처리
                        for sub_key, sub_value in value.items():
                            if sub_key == "one":
                                translations[key] = sub_value
                            elif sub_key == "other":
                                translations[f"{key}_plural"] = sub_value
                            else:
                                translations[f"{key}_{sub_key}"] = sub_value
                
        except Exception as e:
            self.logger.error(f"Error loading translation file {translation_file}: {str(e)}")
        
        return translations
    
    def set_language(self, language: Language):
        """현재 언어 설정"""
        
        if language not in self.translations_cache:
            self.logger.warning(f"Language not supported: {language.value}")
            return
        
        self.current_language = language
        
        # 로케일 설정
        locale_config = LocaleConfig.SUPPORTED_LOCALES[language]
        try:
            locale.setlocale(locale.LC_ALL, locale_config["code"])
        except locale.Error:
            self.logger.warning(f"Failed to set locale: {locale_config['code']}")
    
    def get_current_language(self) -> Language:
        """현재 언어 조회"""
        return self.current_language
    
    def translate(self, key: str, **kwargs) -> str:
        """번역 조회"""
        
        # 현재 언어 번역 조회
        translations = self.translations_cache.get(self.current_language, {})
        translation = translations.get(key)
        
        # 번역이 없으면 폴백 언어로 조회
        if not translation and self.current_language != self.fallback_language:
            fallback_translations = self.translations_cache.get(self.fallback_language, {})
            translation = fallback_translations.get(key)
        
        # 여전히 없으면 키 반환
        if not translation:
            return key
        
        # 변수 치환
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Translation formatting error for key '{key}': {str(e)}")
        
        return translation
    
    def translate_plural(self, key: str, count: int, **kwargs) -> str:
        """복수형 번역 조회"""
        
        # 복수형 키 생성
        plural_key = f"{key}_plural" if count != 1 else key
        
        # 현재 언어 번역 조회
        translations = self.translations_cache.get(self.current_language, {})
        translation = translations.get(plural_key)
        
        # 번역이 없으면 폴백 언어로 조회
        if not translation and self.current_language != self.fallback_language:
            fallback_translations = self.translations_cache.get(self.fallback_language, {})
            translation = fallback_translations.get(plural_key)
        
        # 여전히 없으면 키 반환
        if not translation:
            return key
        
        # 변수 치환
        kwargs['count'] = count
        try:
            translation = translation.format(**kwargs)
        except (KeyError, ValueError) as e:
            self.logger.warning(f"Translation formatting error for key '{plural_key}': {str(e)}")
        
        return translation
    
    def format_date(self, date: datetime, language: Optional[Language] = None) -> str:
        """날짜 현지화 형식"""
        
        target_language = language or self.current_language
        locale_config = LocaleConfig.SUPPORTED_LOCALES.get(target_language)
        
        if not locale_config:
            return date.strftime("%Y-%m-%d")
        
        return date.strftime(locale_config["date_format"])
    
    def format_time(self, time: datetime, language: Optional[Language] = None) -> str:
        """시간 현지화 형식"""
        
        target_language = language or self.current_language
        locale_config = LocaleConfig.SUPPORTED_LOCALES.get(target_language)
        
        if not locale_config:
            return time.strftime("%H:%M:%S")
        
        return time.strftime(locale_config["time_format"])
    
    def format_datetime(self, datetime_obj: datetime, language: Optional[Language] = None) -> str:
        """날짜/시간 현지화 형식"""
        
        target_language = language or self.current_language
        locale_config = LocaleConfig.SUPPORTED_LOCALES.get(target_language)
        
        if not locale_config:
            return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")
        
        return datetime_obj.strftime(locale_config["datetime_format"])
    
    def format_currency(self, amount: float, language: Optional[Language] = None) -> str:
        """통화 현지화 형식"""
        
        target_language = language or self.current_language
        locale_config = LocaleConfig.SUPPORTED_LOCALES.get(target_language)
        
        if not locale_config:
            return f"${amount:.2f}"
        
        currency = locale_config["currency"]
        
        # 통화별 형식
        if currency == "USD":
            return f"${amount:,.2f}"
        elif currency == "KRW":
            return f"₩{amount:,.0f}"
        elif currency == "JPY":
            return f"¥{amount:,.0f}"
        elif currency == "CNY":
            return f"¥{amount:,.2f}"
        elif currency == "TWD":
            return f"NT${amount:,.0f}"
        elif currency == "EUR":
            return f"€{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{currency} {amount:,.2f}"
    
    def format_number(self, number: Union[int, float], language: Optional[Language] = None) -> str:
        """숫자 현지화 형식"""
        
        target_language = language or self.current_language
        locale_config = LocaleConfig.SUPPORTED_LOCALES.get(target_language)
        
        if not locale_config:
            return str(number)
        
        decimal_sep = locale_config["number_format"]["decimal_separator"]
        thousands_sep = locale_config["number_format"]["thousands_separator"]
        
        # 정수와 소수 부분 분리
        if isinstance(number, float):
            integer_part, decimal_part = str(number).split(".")
            decimal_part = decimal_part.ljust(2, "0")[:2]  # 소수점 이하 2자리
        else:
            integer_part = str(number)
            decimal_part = ""
        
        # 천 단위 구분자 추가
        formatted_integer = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_integer = thousands_sep + formatted_integer
            formatted_integer = digit + formatted_integer
        
        # 소수 부분 결합
        if decimal_part:
            return formatted_integer + decimal_sep + decimal_part
        else:
            return formatted_integer
    
    def get_supported_languages(self) -> List[Dict[str, Any]]:
        """지원 언어 목록 조회"""
        
        languages = []
        
        for language in Language:
            if language in LocaleConfig.SUPPORTED_LOCALES:
                config = LocaleConfig.SUPPORTED_LOCALES[language]
                languages.append({
                    "code": language.value,
                    "locale_code": config["code"],
                    "name": config["name"],
                    "native_name": config["native_name"],
                    "currency": config["currency"],
                    "rtl": config["rtl"]
                })
        
        return languages
    
    def detect_language_from_request(self, accept_language: str) -> Language:
        """HTTP Accept-Language 헤더에서 언어 감지"""
        
        if not accept_language:
            return Language.ENGLISH
        
        # 언어 우선순위 파싱
        languages = accept_language.split(',')
        language_preferences = []
        
        for lang in languages:
            # 언어 코드 파싱 (예: "en-US,en;q=0.9")
            parts = lang.split(';')
            language_code = parts[0].strip()
            quality = 1.0
            
            # 품질 값 파싱
            if len(parts) > 1:
                for part in parts[1:]:
                    if part.strip().startswith('q='):
                        try:
                            quality = float(part.strip()[2:])
                        except ValueError:
                            quality = 0.0
            
            language_preferences.append((language_code, quality))
        
        # 품질 순으로 정렬
        language_preferences.sort(key=lambda x: x[1], reverse=True)
        
        # 지원 언어와 매칭
        for language_code, _ in language_preferences:
            # 정확한 매칭
            for language in Language:
                if language in LocaleConfig.SUPPORTED_LOCALES:
                    config = LocaleConfig.SUPPORTED_LOCALES[language]
                    if config["code"].lower() == language_code.lower():
                        return language
            
            # 언어 코드만 매칭 (예: "en" 매칭)
            language_prefix = language_code.split('-')[0].lower()
            for language in Language:
                if language in LocaleConfig.SUPPORTED_LOCALES:
                    config = LocaleConfig.SUPPORTED_LOCALES[language]
                    if config["code"].split('-')[0].lower() == language_prefix:
                        return language
        
        # 매칭되는 언어가 없으면 기본 언어 반환
        return Language.ENGLISH
    
    def is_rtl_language(self, language: Optional[Language] = None) -> bool:
        """RTL 언어 여부 확인"""
        
        target_language = language or self.current_language
        
        if target_language in LocaleConfig.SUPPORTED_LOCALES:
            return LocaleConfig.SUPPORTED_LOCALES[target_language]["rtl"]
        
        return False
```

### 2.2 프론트엔드 국제화

```typescript
// frontend/src/i18n/i18n.service.ts
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { Language, LocaleConfig } from './i18n.models';

@Injectable({
  providedIn: 'root'
})
export class I18nService {
  private currentLanguageSubject = new BehaviorSubject<Language>(Language.ENGLISH);
  private translationsSubject = new BehaviorSubject<any>({});
  
  currentLanguage$ = this.currentLanguageSubject.asObservable();
  translations$ = this.translationsSubject.asObservable();
  
  private translations: any = {};
  private fallbackLanguage = Language.ENGLISH;
  
  constructor(private http: HttpClient) {
    this.loadTranslations(Language.ENGLISH);
  }
  
  async setLanguage(language: Language): Promise<void> {
    if (this.translations[language.value]) {
      this.currentLanguageSubject.next(language);
      return;
    }
    
    try {
      const translations = await this.loadTranslations(language);
      this.translations[language.value] = translations;
      this.currentLanguageSubject.next(language);
      
      // 로컬 스토리지에 저장
      localStorage.setItem('preferredLanguage', language.value);
      
      // HTML lang 속성 업데이트
      document.documentElement.lang = LocaleConfig.SUPPORTED_LOCALES[language].code;
      
      // RTL 방향 설정
      const isRtl = this.isRtlLanguage(language);
      document.documentElement.dir = isRtl ? 'rtl' : 'ltr';
      
    } catch (error) {
      console.error(`Failed to load translations for ${language.value}:`, error);
    }
  }
  
  private async loadTranslations(language: Language): Promise<any> {
    try {
      const translations = await this.http
        .get(`/assets/i18n/${language.value}.json`)
        .toPromise();
      
      this.translationsSubject.next(translations);
      return translations;
      
    } catch (error) {
      console.error(`Failed to load translations for ${language.value}:`, error);
      
      // 폴백 언어로드
      if (language !== this.fallbackLanguage) {
        return this.loadTranslations(this.fallbackLanguage);
      }
      
      throw error;
    }
  }
  
  translate(key: string, params?: any): string {
    const currentLanguage = this.currentLanguageSubject.value;
    const translations = this.translations[currentLanguage.value] || {};
    
    let translation = translations[key];
    
    // 번역이 없으면 폴백 언어로 조회
    if (!translation && currentLanguage !== this.fallbackLanguage) {
      const fallbackTranslations = this.translations[this.fallbackLanguage.value] || {};
      translation = fallbackTranslations[key];
    }
    
    // 여전히 없으면 키 반환
    if (!translation) {
      return key;
    }
    
    // 변수 치환
    if (params) {
      return this.interpolate(translation, params);
    }
    
    return translation;
  }
  
  translatePlural(key: string, count: number, params?: any): string {
    const currentLanguage = this.currentLanguageSubject.value;
    const translations = this.translations[currentLanguage.value] || {};
    
    // 복수형 키 결정
    const pluralKey = count !== 1 ? `${key}_plural` : key;
    
    let translation = translations[pluralKey];
    
    // 번역이 없으면 폴백 언어로 조회
    if (!translation && currentLanguage !== this.fallbackLanguage) {
      const fallbackTranslations = this.translations[this.fallbackLanguage.value] || {};
      translation = fallbackTranslations[pluralKey];
    }
    
    // 여전히 없으면 키 반환
    if (!translation) {
      return key;
    }
    
    // 변수 치환
    const mergedParams = { ...params, count };
    return this.interpolate(translation, mergedParams);
  }
  
  private interpolate(template: string, params: any): string {
    return template.replace(/\{\{(\w+)\}/g, (match, key) => {
      return params[key] !== undefined ? params[key] : match;
    });
  }
  
  formatDate(date: Date, language?: Language): string {
    const targetLanguage = language || this.currentLanguageSubject.value;
    const localeConfig = LocaleConfig.SUPPORTED_LOCALES[targetLanguage];
    
    if (!localeConfig) {
      return date.toLocaleDateString();
    }
    
    return this.formatWithLocale(date, localeConfig.dateFormat);
  }
  
  formatTime(date: Date, language?: Language): string {
    const targetLanguage = language || this.currentLanguageSubject.value;
    const localeConfig = LocaleConfig.SUPPORTED_LOCALES[targetLanguage];
    
    if (!localeConfig) {
      return date.toLocaleTimeString();
    }
    
    return this.formatWithLocale(date, localeConfig.timeFormat);
  }
  
  formatDateTime(date: Date, language?: Language): string {
    const targetLanguage = language || this.currentLanguageSubject.value;
    const localeConfig = LocaleConfig.SUPPORTED_LOCALES[targetLanguage];
    
    if (!localeConfig) {
      return date.toLocaleString();
    }
    
    return this.formatWithLocale(date, localeConfig.datetimeFormat);
  }
  
  formatCurrency(amount: number, language?: Language): string {
    const targetLanguage = language || this.currentLanguageSubject.value;
    const localeConfig = LocaleConfig.SUPPORTED_LOCALES[targetLanguage];
    
    if (!localeConfig) {
      return amount.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
    }
    
    const currency = localeConfig.currency;
    
    // 통화별 형식
    switch (currency) {
      case 'USD':
        return `$${amount.toLocaleString()}`;
      case 'KRW':
        return `₩${amount.toLocaleString()}`;
      case 'JPY':
        return `¥${amount.toLocaleString()}`;
      case 'CNY':
        return `¥${amount.toLocaleString()}`;
      case 'TWD':
        return `NT$${amount.toLocaleString()}`;
      case 'EUR':
        return `€${amount.toLocaleString('de-DE')}`;
      default:
        return `${currency} ${amount.toLocaleString()}`;
    }
  }
  
  formatNumber(number: number, language?: Language): string {
    const targetLanguage = language || this.currentLanguageSubject.value;
    const localeConfig = LocaleConfig.SUPPORTED_LOCALES[targetLanguage];
    
    if (!localeConfig) {
      return number.toLocaleString();
    }
    
    const decimalSep = localeConfig.numberFormat.decimalSeparator;
    const thousandsSep = localeConfig.numberFormat.thousandsSeparator;
    
    // 수동 포맷팅
    const [integerPart, decimalPart] = number.toString().split('.');
    const formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSep);
    
    return decimalPart ? `${formattedInteger}${decimalSep}${decimalPart}` : formattedInteger;
  }
  
  private formatWithLocale(date: Date, format: string): string {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hours = date.getHours();
    const minutes = date.getMinutes();
    const seconds = date.getSeconds();
    
    return format
      .replace('YYYY', year.toString())
      .replace('MM', month.toString().padStart(2, '0'))
      .replace('DD', day.toString().padStart(2, '0'))
      .replace('HH', hours.toString().padStart(2, '0'))
      .replace('mm', minutes.toString().padStart(2, '0'))
      .replace('SS', seconds.toString().padStart(2, '0'));
  }
  
  getSupportedLanguages(): Array<{code: string, name: string, nativeName: string}> {
    return Object.entries(LocaleConfig.SUPPORTED_LOCALES).map(([code, config]) => ({
      code,
      name: config.name,
      nativeName: config.nativeName
    }));
  }
  
  isRtlLanguage(language?: Language): boolean {
    const targetLanguage = language || this.currentLanguageSubject.value;
    const localeConfig = LocaleConfig.SUPPORTED_LOCALES[targetLanguage];
    
    return localeConfig ? localeConfig.rtl : false;
  }
  
  initializeFromStorage(): void {
    const savedLanguage = localStorage.getItem('preferredLanguage');
    
    if (savedLanguage && Object.values(Language).includes(savedLanguage as Language)) {
      this.setLanguage(savedLanguage as Language);
    } else {
      // 브라우저 언어 감지
      const browserLanguage = navigator.language || (navigator as any).userLanguage;
      const detectedLanguage = this.detectLanguageFromBrowser(browserLanguage);
      this.setLanguage(detectedLanguage);
    }
  }
  
  private detectLanguageFromBrowser(browserLanguage: string): Language {
    const languageCode = browserLanguage.split('-')[0].toLowerCase();
    
    // 지원 언어와 매칭
    for (const [language, config] of Object.entries(LocaleConfig.SUPPORTED_LOCALES)) {
      if (config.code.split('-')[0].toLowerCase() === languageCode) {
        return language as Language;
      }
    }
    
    return Language.ENGLISH; // 기본값
  }
}
```

### 2.3 백엔드 국제화 미들웨어

```python
# backend/i18n/i18n_middleware.py
import asyncio
from typing import Dict, List, Optional, Any, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging
from .i18n_manager import I18nManager, Language, LocaleConfig

class I18nMiddleware:
    """국제화 미들웨어"""
    
    def __init__(self, i18n_manager: I18nManager):
        self.i18n_manager = i18n_manager
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # 요청에서 언어 감지
        language = self._detect_language_from_request(request)
        
        # 언어 설정
        self.i18n_manager.set_language(language)
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 헤더에 언어 정보 추가
        response.headers["Content-Language"] = LocaleConfig.SUPPORTED_LOCALES[language]["code"]
        
        return response
    
    def _detect_language_from_request(self, request: Request) -> Language:
        """요청에서 언어 감지"""
        
        # 1. URL 경로에서 언어 감지 (/api/en/...)
        path_parts = request.url.path.strip('/').split('/')
        if len(path_parts) > 1 and path_parts[0] in [lang.value for lang in Language]:
            try:
                return Language(path_parts[0])
            except ValueError:
                pass
        
        # 2. 쿼리 파라미터에서 언어 감지
        lang_param = request.query_params.get('lang')
        if lang_param and lang_param in [lang.value for lang in Language]:
            try:
                return Language(lang_param)
            except ValueError:
                pass
        
        # 3. Accept-Language 헤더에서 언어 감지
        accept_language = request.headers.get('accept-language')
        if accept_language:
            return self.i18n_manager.detect_language_from_request(accept_language)
        
        # 4. 쿠키에서 언어 감지
        lang_cookie = request.cookies.get('lang')
        if lang_cookie and lang_cookie in [lang.value for lang in Language]:
            try:
                return Language(lang_cookie)
            except ValueError:
                pass
        
        # 5. 사용자 설정에서 언어 감지 (인증된 경우)
        # 실제 구현에서는 데이터베이스에서 사용자 언어 설정 조회
        
        return Language.ENGLISH  # 기본값

class I18nResponseHelper:
    """국제화 응답 헬퍼"""
    
    def __init__(self, i18n_manager: I18nManager):
        self.i18n_manager = i18n_manager
    
    def success_response(self, data: Any, message_key: str = None, **kwargs) -> Dict[str, Any]:
        """성공 응답 생성"""
        
        response = {
            "success": True,
            "data": data,
            "timestamp": self.i18n_manager.format_datetime(datetime.now())
        }
        
        if message_key:
            response["message"] = self.i18n_manager.translate(message_key, **kwargs)
        
        return response
    
    def error_response(self, error_code: str, message_key: str = None, **kwargs) -> Dict[str, Any]:
        """에러 응답 생성"""
        
        response = {
            "success": False,
            "error_code": error_code,
            "timestamp": self.i18n_manager.format_datetime(datetime.now())
        }
        
        if message_key:
            response["message"] = self.i18n_manager.translate(message_key, **kwargs)
        
        return response
    
    def validation_error_response(self, field_errors: Dict[str, List[str]]) -> Dict[str, Any]:
        """검증 에러 응답 생성"""
        
        formatted_errors = {}
        
        for field, error_keys in field_errors.items():
            formatted_errors[field] = [
                self.i18n_manager.translate(error_key) for error_key in error_keys
            ]
        
        return {
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "errors": formatted_errors,
            "timestamp": self.i18n_manager.format_datetime(datetime.now())
        }
```

## 3. 번역 관리 시스템

### 3.1 번역 파일 구조

```json
// translations/en.json
{
  "common": {
    "loading": "Loading...",
    "error": "Error",
    "success": "Success",
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit",
    "search": "Search",
    "filter": "Filter",
    "refresh": "Refresh",
    "close": "Close"
  },
  "navigation": {
    "dashboard": "Dashboard",
    "stocks": "Stocks",
    "sentiment": "Sentiment Analysis",
    "portfolio": "Portfolio",
    "settings": "Settings",
    "logout": "Logout"
  },
  "stock": {
    "search_placeholder": "Search for stocks...",
    "no_results": "No stocks found",
    "price": "Price",
    "change": "Change",
    "change_percent": "Change %",
    "volume": "Volume",
    "market_cap": "Market Cap",
    "pe_ratio": "P/E Ratio",
    "dividend_yield": "Dividend Yield"
  },
  "sentiment": {
    "positive": "Positive",
    "negative": "Negative",
    "neutral": "Neutral",
    "score": "Sentiment Score",
    "confidence": "Confidence",
    "source": "Source",
    "mentions": "Mentions"
  },
  "portfolio": {
    "add_stock": "Add Stock",
    "remove_stock": "Remove Stock",
    "total_value": "Total Value",
    "daily_change": "Daily Change",
    "performance": "Performance",
    "holdings": "Holdings"
  },
  "error": {
    "network_error": "Network error occurred",
    "invalid_symbol": "Invalid stock symbol",
    "api_limit_exceeded": "API rate limit exceeded",
    "authentication_failed": "Authentication failed",
    "permission_denied": "Permission denied",
    "not_found": "Resource not found",
    "server_error": "Internal server error"
  },
  "validation": {
    "required_field": "This field is required",
    "invalid_email": "Invalid email address",
    "password_too_short": "Password must be at least 8 characters",
    "passwords_not_match": "Passwords do not match"
  },
  "time": {
    "now": "Now",
    "minutes_ago": "{count} minute ago",
    "minutes_ago_plural": "{count} minutes ago",
    "hours_ago": "{count} hour ago",
    "hours_ago_plural": "{count} hours ago",
    "days_ago": "{count} day ago",
    "days_ago_plural": "{count} days ago"
  }
}
```

```json
// translations/ko.json
{
  "common": {
    "loading": "로딩 중...",
    "error": "오류",
    "success": "성공",
    "cancel": "취소",
    "save": "저장",
    "delete": "삭제",
    "edit": "편집",
    "search": "검색",
    "filter": "필터",
    "refresh": "새로고침",
    "close": "닫기"
  },
  "navigation": {
    "dashboard": "대시보드",
    "stocks": "주식",
    "sentiment": "감성 분석",
    "portfolio": "포트폴리오",
    "settings": "설정",
    "logout": "로그아웃"
  },
  "stock": {
    "search_placeholder": "주식 검색...",
    "no_results": "검색 결과가 없습니다",
    "price": "가격",
    "change": "변동",
    "change_percent": "변동률",
    "volume": "거래량",
    "market_cap": "시가총액",
    "pe_ratio": "PER",
    "dividend_yield": "배당수익률"
  },
  "sentiment": {
    "positive": "긍정적",
    "negative": "부정적",
    "neutral": "중립적",
    "score": "감성 점수",
    "confidence": "신뢰도",
    "source": "출처",
    "mentions": "언급"
  },
  "portfolio": {
    "add_stock": "주식 추가",
    "remove_stock": "주식 제거",
    "total_value": "총 평가액",
    "daily_change": "일일 변동",
    "performance": "성과",
    "holdings": "보유 자산"
  },
  "error": {
    "network_error": "네트워크 오류가 발생했습니다",
    "invalid_symbol": "잘못된 주식 기호입니다",
    "api_limit_exceeded": "API 호출 한도를 초과했습니다",
    "authentication_failed": "인증에 실패했습니다",
    "permission_denied": "권한이 없습니다",
    "not_found": "리소스를 찾을 수 없습니다",
    "server_error": "서버 내부 오류가 발생했습니다"
  },
  "validation": {
    "required_field": "이 필드는 필수입니다",
    "invalid_email": "잘못된 이메일 주소입니다",
    "password_too_short": "비밀번호는 최소 8자 이상이어야 합니다",
    "passwords_not_match": "비밀번호가 일치하지 않습니다"
  },
  "time": {
    "now": "지금",
    "minutes_ago": "{count}분 전",
    "minutes_ago_plural": "{count}분 전",
    "hours_ago": "{count}시간 전",
    "hours_ago_plural": "{count}시간 전",
    "days_ago": "{count}일 전",
    "days_ago_plural": "{count}일 전"
  }
}
```

### 3.2 번역 관리 도구

```python
# tools/translation_manager.py
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from pathlib import Path
import re

class TranslationManager:
    """번역 관리 도구"""
    
    def __init__(self, translations_dir: str = "translations"):
        self.translations_dir = Path(translations_dir)
        self.logger = logging.getLogger(__name__)
        
        # 지원 언어 목록
        self.supported_languages = [
            "en", "ko", "ja", "zh-CN", "zh-TW", "es", "fr", "de", "pt", "ru"
        ]
    
    def extract_translations(self, source_dir: str) -> Dict[str, Dict[str, str]]:
        """소스 코드에서 번역 가능한 문자열 추출"""
        
        translations = {}
        
        # 소스 파일 스캔
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(('.ts', '.tsx', '.js', '.jsx', '.py')):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # 번역 가능한 문자열 추출
                            extracted = self._extract_strings_from_content(content)
                            
                            for string in extracted:
                                if string not in translations:
                                    translations[string] = string
                    
                    except Exception as e:
                        self.logger.error(f"Error processing file {file_path}: {str(e)}")
        
        return translations
    
    def _extract_strings_from_content(self, content: str) -> List[str]:
        """콘텐츠에서 번역 가능한 문자열 추출"""
        
        strings = []
        
        # 1. 따옴표로 묶인 문자열
        quoted_strings = re.findall(r'["\']([^"\']+)["\']', content)
        strings.extend(quoted_strings)
        
        # 2. translate() 함수 호출
        translate_calls = re.findall(r'translate\(["\']([^"\']+)["\']', content)
        strings.extend(translate_calls)
        
        # 3. 템플릿 문자열 ({{ variable }})
        template_strings = re.findall(r'\{\{([^}]+)\}', content)
        strings.extend([f"{{{s}}}" for s in template_strings])
        
        # 4. HTML 태그 내용
        html_content = re.findall(r'>([^<]+)<', content)
        strings.extend([s.strip() for s in html_content if s.strip()])
        
        # 중복 제거 및 필터링
        unique_strings = list(set(strings))
        filtered_strings = [
            s for s in unique_strings 
            if len(s) > 1 and not s.isdigit() and not s.isspace()
        ]
        
        return filtered_strings
    
    def generate_translation_template(self, extracted_strings: List[str], output_file: str):
        """번역 템플릿 생성"""
        
        template = {}
        
        # 문자열을 카테고리로 그룹화
        categorized_strings = self._categorize_strings(extracted_strings)
        
        for category, strings in categorized_strings.items():
            template[category] = {}
            
            for string in strings:
                template[category][string] = string
        
        # 템플릿 파일 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Translation template saved to {output_file}")
    
    def _categorize_strings(self, strings: List[str]) -> Dict[str, List[str]]:
        """문자열을 카테고리로 그룹화"""
        
        categories = {
            "common": [],
            "navigation": [],
            "stock": [],
            "sentiment": [],
            "portfolio": [],
            "error": [],
            "validation": [],
            "time": []
        }
        
        # 키워드 기반 카테고리 분류
        for string in strings:
            lower_string = string.lower()
            
            if any(keyword in lower_string for keyword in ["loading", "error", "success", "cancel", "save"]):
                categories["common"].append(string)
            elif any(keyword in lower_string for keyword in ["dashboard", "stocks", "sentiment", "portfolio"]):
                categories["navigation"].append(string)
            elif any(keyword in lower_string for keyword in ["price", "change", "volume", "market"]):
                categories["stock"].append(string)
            elif any(keyword in lower_string for keyword in ["positive", "negative", "neutral", "sentiment"]):
                categories["sentiment"].append(string)
            elif any(keyword in lower_string for keyword in ["portfolio", "holdings", "performance"]):
                categories["portfolio"].append(string)
            elif any(keyword in lower_string for keyword in ["network", "invalid", "authentication", "permission"]):
                categories["error"].append(string)
            elif any(keyword in lower_string for keyword in ["required", "email", "password", "field"]):
                categories["validation"].append(string)
            elif any(keyword in lower_string for keyword in ["minute", "hour", "day", "ago"]):
                categories["time"].append(string)
            else:
                categories["common"].append(string)  # 기본 카테고리
        
        return categories
    
    def validate_translations(self) -> Dict[str, List[str]]:
        """번역 파일 검증"""
        
        validation_results = {}
        
        for language in self.supported_languages:
            translation_file = self.translations_dir / f"{language}.json"
            
            if not translation_file.exists():
                validation_results[language] = [f"Translation file not found: {translation_file}"]
                continue
            
            try:
                with open(translation_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                
                errors = self._validate_translation_structure(translations, language)
                validation_results[language] = errors
                
            except Exception as e:
                validation_results[language] = [f"Error loading translation file: {str(e)}"]
        
        return validation_results
    
    def _validate_translation_structure(self, translations: Dict, language: str) -> List[str]:
        """번역 구조 검증"""
        
        errors = []
        
        # 필수 키 확인
        required_keys = [
            "common.loading",
            "common.error",
            "common.success",
            "navigation.dashboard",
            "stock.search_placeholder",
            "error.network_error"
        ]
        
        for key in required_keys:
            keys = key.split('.')
            current = translations
            
            for k in keys:
                if k not in current:
                    errors.append(f"Missing required key: {key}")
                    break
                current = current[k]
        
        # 값 타입 검증
        for key, value in self._flatten_dict(translations).items():
            if not isinstance(value, str):
                errors.append(f"Invalid value type for key {key}: {type(value)}")
        
        return errors
    
    def _flatten_dict(self, d: Dict, parent_key: str = '') -> Dict[str, Any]:
        """중첩 딕셔너리 평탈화"""
        
        items = {}
        
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key))
            else:
                items[new_key] = v
        
        return items
    
    def merge_translations(self, base_file: str, update_file: str, output_file: str):
        """번역 파일 병합"""
        
        try:
            # 기본 번역 로드
            with open(base_file, 'r', encoding='utf-8') as f:
                base_translations = json.load(f)
            
            # 업데이트 번역 로드
            with open(update_file, 'r', encoding='utf-8') as f:
                update_translations = json.load(f)
            
            # 번역 병합
            merged_translations = self._deep_merge(base_translations, update_translations)
            
            # 병합된 번역 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_translations, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Merged translations saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error merging translations: {str(e)}")
    
    def _deep_merge(self, base: Dict, update: Dict) -> Dict:
        """딕셔너리 깊은 병합"""
        
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def generate_translation_report(self) -> Dict[str, Any]:
        """번역 현황 보고서 생성"""
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "languages": {},
            "statistics": {
                "total_keys": 0,
                "translated_keys": {},
                "missing_translations": {}
            }
        }
        
        # 기준 언어 (영어) 로드
        base_file = self.translations_dir / "en.json"
        if not base_file.exists():
            return report
        
        with open(base_file, 'r', encoding='utf-8') as f:
            base_translations = json.load(f)
        
        base_keys = set(self._flatten_dict(base_translations).keys())
        report["statistics"]["total_keys"] = len(base_keys)
        
        # 각 언어별 번역 현황 분석
        for language in self.supported_languages:
            if language == "en":
                continue  # 기준 언어는 건너뛰기
            
            translation_file = self.translations_dir / f"{language}.json"
            
            if not translation_file.exists():
                report["languages"][language] = {
                    "status": "missing",
                    "translated_count": 0,
                    "missing_count": len(base_keys),
                    "missing_keys": list(base_keys)
                }
                continue
            
            try:
                with open(translation_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                
                translated_keys = set(self._flatten_dict(translations).keys())
                missing_keys = base_keys - translated_keys
                
                report["languages"][language] = {
                    "status": "exists",
                    "translated_count": len(translated_keys),
                    "missing_count": len(missing_keys),
                    "missing_keys": list(missing_keys)
                }
                
                report["statistics"]["translated_keys"][language] = len(translated_keys)
                report["statistics"]["missing_translations"][language] = len(missing_keys)
                
            except Exception as e:
                report["languages"][language] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return report
```

## 4. 구현 가이드

### 4.1 단계별 구현 계획

#### 1단계: 기본 국제화 프레임워크 (2-3주)
- I18nManager 구현 및 번역 로드 시스템
- 기본 UI 컴포넌트 현지화
- 언어 전환 기능 구현
- 날짜/시간/통화 현지화

#### 2단계: 프론트엔드 국제화 (2-3주)
- Angular/React i18n 서비스 구현
- 다국어 라우팅 구현
- 언어 감지 및 전환 UI
- RTL 언어 지원

#### 3단계: 백엔드 국제화 (2-3주)
- API 응답 현지화 미들웨어
- 데이터베이스 다국어 지원
- 이메일 템플릿 현지화
- 에러 메시지 현지화

#### 4단계: 번역 관리 도구 (1-2주)
- 번역 문자열 추출 도구
- 번역 템플릿 생성기
- 번역 검증 도구
- 번역 병합 도구

#### 5단계: 고급 기능 (2-3주)
- 동적 번역 로딩
- 번역 캐싱 시스템
- 번역 관리 API
- 자동 번역 통합

### 4.2 성능 고려사항

1. **번역 로딩 성능**
   - 번역 파일 분할 로드
   - 클라이언트 측 캐싱
   - 지연 로딩 구현

2. **메모리 사용량**
   - 번역 데이터 압축
   - 사용 언어만 로드
   - 미사용 번역 정리

3. **번역 전환 성능**
   - 번역 키 해싱
   - 변수 치환 최적화
   - 복수형 처리 효율화

### 4.3 보안 고려사항

1. **번역 데이터 보안**
   - 번역 파일 암호화
   - 무단자 변조 방지
   - 안전한 번역 배포

2. **언어 전환 보안**
   - 클라이언트 측 조작 방지
   - 서버 측 검증
   - XSS 방지

3. **콘텐츠 보안**
   - 번역된 콘텐츠 검증
   - 악의적인 코드 주입 방지
   - 안전한 HTML 렌더링

## 5. 결론

본 국제화 전략은 InsiteChart 플랫폼의 글로벌 확장을 위한 포괄적인 솔루션을 제공합니다. 다계층 국제화 아키텍처, 자동화된 번역 관리, 문화적 적응 기능을 통해 다양한 언어권 사용자에게 일관된 경험을 제공할 수 있습니다.

단계적인 구현을 통해 시스템의 국제화 수준을 점진적으로 향상하고, 실제 사용자 피드백을 기반으로 현지화 정책을 최적화하여 장기적인 글로벌 성공을 보장할 수 있습니다.