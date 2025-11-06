# 사용자 경험 및 접근성 개선

## 1. 사용자 경험(UX) 디자인

### 1.1 사용자 중심 설계 원칙

#### 1.1.1 디자인 시스템
```typescript
// frontend/design-system/components/Button.tsx
import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';

// 버튼 변형 정의
const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            {children}
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);

Button.displayName = 'Button';

export { Button, buttonVariants };

// frontend/design-system/components/Card.tsx
import React, { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../utils/cn';

const Card = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-lg border bg-card text-card-foreground shadow-sm',
        className
      )}
      {...props}
    />
  )
);
Card.displayName = 'Card';

const CardHeader = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex flex-col space-y-1.5 p-6', className)}
      {...props}
    />
  )
);
CardHeader.displayName = 'CardHeader';

const CardTitle = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        'text-2xl font-semibold leading-none tracking-tight',
        className
      )}
      {...props}
    />
  )
);
CardTitle.displayName = 'CardTitle';

const CardDescription = forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    />
  )
);
CardDescription.displayName = 'CardDescription';

const CardContent = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />
  )
);
CardContent.displayName = 'CardContent';

const CardFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex items-center p-6 pt-0', className)}
      {...props}
    />
  )
);
CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent };

// frontend/design-system/tokens/colors.ts
export const colors = {
  // 기본 색상
  white: '#FFFFFF',
  black: '#000000',
  
  // 그레이 스케일
  gray: {
    50: '#F9FAFB',
    100: '#F3F4F6',
    200: '#E5E7EB',
    300: '#D1D5DB',
    400: '#9CA3AF',
    500: '#6B7280',
    600: '#4B5563',
    700: '#374151',
    800: '#1F2937',
    900: '#111827',
  },
  
  // 브랜드 색상
  primary: {
    50: '#EFF6FF',
    100: '#DBEAFE',
    200: '#BFDBFE',
    300: '#93C5FD',
    400: '#60A5FA',
    500: '#3B82F6',
    600: '#2563EB',
    700: '#1D4ED8',
    800: '#1E40AF',
    900: '#1E3A8A',
  },
  
  // 상태 색상
  success: {
    50: '#F0FDF4',
    100: '#DCFCE7',
    200: '#BBF7D0',
    300: '#86EFAC',
    400: '#4ADE80',
    500: '#22C55E',
    600: '#16A34A',
    700: '#15803D',
    800: '#166534',
    900: '#14532D',
  },
  
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    200: '#FDE68A',
    300: '#FCD34D',
    400: '#FBBF24',
    500: '#F59E0B',
    600: '#D97706',
    700: '#B45309',
    800: '#92400E',
    900: '#78350F',
  },
  
  error: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    200: '#FECACA',
    300: '#FCA5A5',
    400: '#F87171',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C',
    800: '#991B1B',
    900: '#7F1D1D',
  },
};

// frontend/design-system/tokens/typography.ts
export const typography = {
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'Consolas', 'monospace'],
  },
  
  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],
    sm: ['0.875rem', { lineHeight: '1.25rem' }],
    base: ['1rem', { lineHeight: '1.5rem' }],
    lg: ['1.125rem', { lineHeight: '1.75rem' }],
    xl: ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
    '5xl': ['3rem', { lineHeight: '1' }],
    '6xl': ['3.75rem', { lineHeight: '1' }],
  },
  
  fontWeight: {
    thin: '100',
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
    black: '900',
  },
  
  letterSpacing: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0em',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
};

// frontend/design-system/tokens/spacing.ts
export const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  32: '8rem',     // 128px
  40: '10rem',    // 160px
  48: '12rem',    // 192px
  56: '14rem',    // 224px
  64: '16rem',    // 256px
};
```

#### 1.1.2 사용자 인터페이스 가이드라인
```typescript
// frontend/design-system/guidelines/ux-principles.ts
export const uxPrinciples = {
  // 명확성 (Clarity)
  clarity: {
    title: '명확성',
    description: '사용자가 혼동하지 않도록 정보와 인터페이스를 명확하게 제공',
    guidelines: [
      '간결하고 명확한 언어 사용',
      '일관된 용어와 표현',
      '의미 있는 아이콘과 레이블',
      '명확한 시각적 계층 구조',
      '예측 가능한 인터랙션'
    ],
    examples: [
      '버튼 텍스트: "제출" 대신 "양식 제출"',
      '에러 메시지: "오류 발생" 대신 "이메일 주소를 확인해주세요"',
      '성공 메시지: "완료" 대신 "주식 정보가 성공적으로 저장되었습니다"'
    ]
  },
  
  // 일관성 (Consistency)
  consistency: {
    title: '일관성',
    description: '전체 애플리케이션에서 일관된 디자인과 상호작용 제공',
    guidelines: [
      '일관된 색상 사용',
      '통일된 컴포넌트 스타일',
      '일관된 레이아웃 패턴',
      '표준화된 상호작용 방식',
      '규칙 기반 디자인 시스템'
    ],
    examples: [
      '모든 확인 버튼은 동일한 스타일과 위치',
      '일관된 네비게이션 패턴',
      '표준화된 폼 요소 디자인',
      '일관된 아이콘 사용'
    ]
  },
  
  // 효율성 (Efficiency)
  efficiency: {
    title: '효율성',
    description: '사용자가 목표를 빠르고 쉽게 달성할 수 있도록 설계',
    guidelines: [
      '최소한의 단계로 목표 달성',
      '자주 사용하는 기능에 빠른 접근',
      '스마트한 기본값 제공',
      '효율적인 검색과 필터링',
      '단축키와 빠른 액션 제공'
    ],
    examples: [
      '자동 완성 기능',
      '최근 검색 기록',
      '자주 사용하는 주식 빠른 접근',
      '키보드 단축키 지원',
      '일괄 작업 기능'
    ]
  },
  
  // 피드백 (Feedback)
  feedback: {
    title: '피드백',
    description: '사용자 행동에 대한 즉각적이고 명확한 피드백 제공',
    guidelines: [
      '행동 결과 즉시 표시',
      '로딩 상태 명확히 표시',
      '오류 상황에서 구체적인 해결책 제시',
      '성공적인 작업 확인',
      '진행 상황 시각적 표시'
    ],
    examples: [
      '버튼 클릭 시 즉각적인 시각적 반응',
      '로딩 스피너와 진행률 표시',
      '구체적인 에러 메시지와 해결 방안',
      '성공 알림과 다음 단계 안내',
      '파일 업로드 진행률 표시'
    ]
  },
  
  // 오류 방지 (Error Prevention)
  errorPrevention: {
    title: '오류 방지',
    description: '사용자가 오류를 범하지 않도록 예방적 조치 제공',
    guidelines: [
      '위험한 작업 전 확인 절차',
      '입력 값 실시간 검증',
      '되돌리기 기능 제공',
      '안전한 기본값 설정',
      '경고 메시지 제공'
    ],
    examples: [
      '중요 데이터 삭제 전 확인 대화상자',
      '이메일 주소 형식 실시간 검증',
      '자동 저장 기능',
      '실행 취소 가능한 작업',
      '위험 설정 변경 시 경고'
    ]
  },
  
  // 접근성 (Accessibility)
  accessibility: {
    title: '접근성',
    description: '모든 사용자가 동등하게 접근할 수 있는 인터페이스 설계',
    guidelines: [
      '키보드 네비게이션 지원',
      '스크린 리더 호환성',
      '충분한 색상 대비',
      '명확한 포커스 표시',
      '대체 텍스트 제공'
    ],
    examples: [
      '모든 인터랙티브 요소 키보드 접근 가능',
      '이미지에 의미 있는 alt 텍스트',
      '색상만으로 정보 전달하지 않기',
      '명확한 포커스 인디케이터',
      'ARIA 레이블과 속성 사용'
    ]
  },
  
  // 학습 용이성 (Learnability)
  learnability: {
    title: '학습 용이성',
    description: '사용자가 쉽게 배우고 사용할 수 있는 인터페이스 설계',
    guidelines: [
      '직관적인 디자인',
      '일관된 상호작용 패턴',
      '도움말과 가이드 제공',
      '점진적 정보 공개',
      '실제 예시와 데모'
    ],
    examples: [
      '새 사용자를 위한 온보딩 투어',
      '기능별 도움말과 툴팁',
      '인터랙티브 튜토리얼',
      '실제 데이터로 예시 제공',
      '단계별 가이드 제공'
    ]
  }
};

// frontend/design-system/guidelines/interaction-patterns.ts
export const interactionPatterns = {
  // 네비게이션 패턴
  navigation: {
    primary: {
      description: '주요 네비게이션',
      pattern: '상단 또는 사이드바에 위치한 메인 메뉴',
      guidelines: [
        '명확한 계층 구조',
        '현재 위치 표시',
        '일관된 스타일',
        '반응형 디자인'
      ]
    },
    secondary: {
      description: '보조 네비게이션',
      pattern: '페이지 내 로컬 네비게이션',
      guidelines: [
        '컨텍스트에 맞는 메뉴',
        '시각적 계층 구분',
        '간결한 레이블'
      ]
    },
    breadcrumb: {
      description: '브레드크럼',
      pattern: '현재 위치 경로 표시',
      guidelines: [
        '클릭 가능한 경로',
        '현재 페이지 강조',
        '구분자 사용'
      ]
    }
  },
  
  // 폼 패턴
  forms: {
    layout: {
      description: '폼 레이아웃',
      pattern: '논리적 그룹과 시각적 정렬',
      guidelines: [
        '관련 필드 그룹화',
        '일관된 정렬',
        '명확한 레이블 위치',
        '적절한 간격'
      ]
    },
    validation: {
      description: '입력 검증',
      pattern: '실시간 검증과 명확한 에러 메시지',
      guidelines: [
        '실시간 피드백',
        '구체적인 에러 메시지',
        '성공 상태 표시',
        '도움말 제공'
      ]
    },
    submission: {
      description: '제출',
      pattern: '명확한 제출 버튼과 처리 상태',
      guidelines: [
        '명확한 액션 버튼',
        '로딩 상태 표시',
        '성공/실패 피드백',
        '되돌리기 옵션'
      ]
    }
  },
  
  // 데이터 표시 패턴
  dataDisplay: {
    tables: {
      description: '테이블',
      pattern: '구조화된 데이터 표시',
      guidelines: [
        '명확한 헤더',
        '정렬 기능',
        '페이지네이션',
        '반응형 디자인'
      ]
    },
    charts: {
      description: '차트',
      pattern: '시각적 데이터 표현',
      guidelines: [
        '적절한 차트 타입',
        '명확한 레이블',
        '범례 제공',
        '대체 텍스트'
      ]
    },
    filters: {
      description: '필터',
      pattern: '데이터 필터링',
      guidelines: [
        '직관적인 필터 옵션',
        '다중 선택 지원',
        '적용된 필터 표시',
        '필터 초기화'
      ]
    }
  },
  
  // 피드백 패턴
  feedback: {
    notifications: {
      description: '알림',
      pattern: '시스템 메시지 표시',
      guidelines: [
        '적절한 타이밍',
        '명확한 메시지',
        '행동 가능한 알림',
        '자동 제거 옵션'
      ]
    },
    modals: {
      description: '모달',
      pattern: '중요 정보나 작업을 위한 오버레이',
      guidelines: [
        '명확한 목적',
        '닫기 방법',
        '배경 클릭 닫기',
        '포커스 관리'
      ]
    },
    tooltips: {
      description: '툴팁',
      pattern: '추가 정보 제공',
      guidelines: [
        '간결한 정보',
        '적절한 타이밍',
        '접근성 고려',
        '시각적 구분'
      ]
    }
  }
};
```

### 1.2 반응형 디자인

#### 1.2.1 반응형 레이아웃 시스템
```typescript
// frontend/design-system/tokens/breakpoints.ts
export const breakpoints = {
  xs: '0px',      // 0 이상
  sm: '576px',    // 576px 이상
  md: '768px',    // 768px 이상
  lg: '992px',    // 992px 이상
  xl: '1200px',   // 1200px 이상
  xxl: '1400px',  // 1400px 이상
};

// 미디어 쿼리 헬퍼
export const mediaQueries = {
  xs: `@media (min-width: ${breakpoints.xs})`,
  sm: `@media (min-width: ${breakpoints.sm})`,
  md: `@media (min-width: ${breakpoints.md})`,
  lg: `@media (min-width: ${breakpoints.lg})`,
  xl: `@media (min-width: ${breakpoints.xl})`,
  xxl: `@media (min-width: ${breakpoints.xxl})`,
  
  // 최대 너비 기준
  xsMax: `@media (max-width: ${breakpoints.sm - 1}px)`,
  smMax: `@media (max-width: ${breakpoints.md - 1}px)`,
  mdMax: `@media (max-width: ${breakpoints.lg - 1}px)`,
  lgMax: `@media (max-width: ${breakpoints.xl - 1}px)`,
  xlMax: `@media (max-width: ${breakpoints.xxl - 1}px)`,
  
  // 범위 기준
  smOnly: `@media (min-width: ${breakpoints.sm}) and (max-width: ${breakpoints.md - 1}px)`,
  mdOnly: `@media (min-width: ${breakpoints.md}) and (max-width: ${breakpoints.lg - 1}px)`,
  lgOnly: `@media (min-width: ${breakpoints.lg}) and (max-width: ${breakpoints.xl - 1}px)`,
};

// frontend/design-system/components/Layout/Grid.tsx
import React, { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../../utils/cn';

interface GridProps extends HTMLAttributes<HTMLDivElement> {
  cols?: number | ResponsiveValue<number>;
  gap?: number | ResponsiveValue<number>;
  align?: 'start' | 'center' | 'end' | 'stretch';
  justify?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';
}

type ResponsiveValue<T> = T | {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  xxl?: T;
};

const getResponsiveClass = <T>(
  value: ResponsiveValue<T> | undefined,
  prefix: string,
  converter?: (val: T) => string
): string => {
  if (!value) return '';
  
  if (typeof value === 'object') {
    const classes: string[] = [];
    
    Object.entries(value).forEach(([breakpoint, val]) => {
      const convertedVal = converter ? converter(val) : val;
      if (breakpoint === 'xs') {
        classes.push(`${prefix}-${convertedVal}`);
      } else {
        classes.push(`${breakpoint}:${prefix}-${convertedVal}`);
      }
    });
    
    return classes.join(' ');
  }
  
  const convertedVal = converter ? converter(value) : value;
  return `${prefix}-${convertedVal}`;
};

const Grid = forwardRef<HTMLDivElement, GridProps>(
  ({ className, cols, gap, align, justify, ...props }, ref) => {
    const gridClasses = cn(
      'grid',
      getResponsiveClass(cols, 'grid-cols'),
      getResponsiveClass(gap, 'gap'),
      align && `items-${align}`,
      justify && `justify-${justify}`,
      className
    );
    
    return <div ref={ref} className={gridClasses} {...props} />;
  }
);

Grid.displayName = 'Grid';

// frontend/design-system/components/Layout/Container.tsx
import React, { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../../utils/cn';

interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  fluid?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
}

const Container = forwardRef<HTMLDivElement, ContainerProps>(
  ({ className, fluid = false, size = 'lg', ...props }, ref) => {
    const containerClasses = cn(
      'mx-auto px-4 sm:px-6 lg:px-8',
      {
        'max-w-sm': size === 'sm' && !fluid,
        'max-w-md': size === 'md' && !fluid,
        'max-w-lg': size === 'lg' && !fluid,
        'max-w-xl': size === 'xl' && !fluid,
        'max-w-full': size === 'full' || fluid,
      },
      className
    );
    
    return <div ref={ref} className={containerClasses} {...props} />;
  }
);

Container.displayName = 'Container';

// frontend/design-system/components/Layout/Stack.tsx
import React, { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../../utils/cn';

interface StackProps extends HTMLAttributes<HTMLDivElement> {
  direction?: 'row' | 'column';
  spacing?: number | ResponsiveValue<number>;
  align?: 'start' | 'center' | 'end' | 'stretch';
  justify?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';
  wrap?: boolean;
}

const Stack = forwardRef<HTMLDivElement, StackProps>(
  ({ 
    className, 
    direction = 'column', 
    spacing = 0, 
    align, 
    justify, 
    wrap = false,
    children,
    ...props 
  }, ref) => {
    const stackClasses = cn(
      'flex',
      {
        'flex-row': direction === 'row',
        'flex-col': direction === 'column',
        'flex-wrap': wrap,
      },
      align && `items-${align}`,
      justify && `justify-${justify}`,
      getResponsiveClass(spacing, 'gap'),
      className
    );
    
    return (
      <div ref={ref} className={stackClasses} {...props}>
        {children}
      </div>
    );
  }
);

Stack.displayName = 'Stack';

export { Grid, Container, Stack };
```

#### 1.2.2 모바일 최적화
```typescript
// frontend/design-system/components/Mobile/MobileNavigation.tsx
import React, { useState } from 'react';
import { Menu, X, Search, Bell, User } from 'lucide-react';
import { Button } from '../Button';
import { cn } from '../../../utils/cn';

interface MobileNavigationProps {
  className?: string;
  user?: {
    name: string;
    avatar?: string;
  };
}

const MobileNavigation: React.FC<MobileNavigationProps> = ({ 
  className, 
  user 
}) => {
  const [isOpen, setIsOpen] = useState(false);
  
  const toggleMenu = () => setIsOpen(!isOpen);
  
  return (
    <div className={cn('md:hidden', className)}>
      {/* 모바일 헤더 */}
      <div className="flex items-center justify-between p-4 bg-white border-b">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleMenu}
            aria-label="메뉴 열기"
          >
            <Menu className="h-6 w-6" />
          </Button>
          
          <h1 className="text-xl font-bold">InsiteChart</h1>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="icon"
            aria-label="검색"
          >
            <Search className="h-5 w-5" />
          </Button>
          
          <Button
            variant="ghost"
            size="icon"
            aria-label="알림"
          >
            <Bell className="h-5 w-5" />
          </Button>
          
          {user && (
            <Button
              variant="ghost"
              size="icon"
              aria-label="사용자 메뉴"
            >
              {user.avatar ? (
                <img 
                  src={user.avatar} 
                  alt={user.name}
                  className="h-8 w-8 rounded-full"
                />
              ) : (
                <User className="h-5 w-5" />
              )}
            </Button>
          )}
        </div>
      </div>
      
      {/* 모바일 메뉴 오버레이 */}
      {isOpen && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50">
          <div className="fixed inset-y-0 left-0 w-full max-w-xs bg-white shadow-lg">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">메뉴</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleMenu}
                aria-label="메뉴 닫기"
              >
                <X className="h-6 w-6" />
              </Button>
            </div>
            
            <nav className="p-4">
              <ul className="space-y-2">
                <li>
                  <a 
                    href="/stocks" 
                    className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                  >
                    주식 검색
                  </a>
                </li>
                <li>
                  <a 
                    href="/sentiment" 
                    className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                  >
                    센티먼트 분석
                  </a>
                </li>
                <li>
                  <a 
                    href="/watchlist" 
                    className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                  >
                    관심종목
                  </a>
                </li>
                <li>
                  <a 
                    href="/portfolio" 
                    className="block px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100"
                  >
                    포트폴리오
                  </a>
                </li>
              </ul>
            </nav>
            
            {user && (
              <div className="absolute bottom-0 left-0 right-0 p-4 border-t">
                <div className="flex items-center space-x-3">
                  {user.avatar ? (
                    <img 
                      src={user.avatar} 
                      alt={user.name}
                      className="h-10 w-10 rounded-full"
                    />
                  ) : (
                    <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <User className="h-6 w-6 text-gray-600" />
                    </div>
                  )}
                  <div>
                    <p className="font-medium">{user.name}</p>
                    <a 
                      href="/profile" 
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      프로필 관리
                    </a>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MobileNavigation;

// frontend/design-system/components/Mobile/TouchOptimized.tsx
import React, { HTMLAttributes, forwardRef } from 'react';
import { cn } from '../../../utils/cn';

interface TouchOptimizedProps extends HTMLAttributes<HTMLDivElement> {
  minHeight?: number;
  padding?: number;
}

// 터치 최적화 컨테이너
const TouchOptimized = forwardRef<HTMLDivElement, TouchOptimizedProps>(
  ({ className, minHeight = 44, padding = 8, children, ...props }, ref) => {
    const touchOptimizedClasses = cn(
      'touch-manipulation',
      className
    );
    
    const style = {
      minHeight: `${minHeight}px`,
      padding: `${padding}px`,
      ...props.style
    };
    
    return (
      <div 
        ref={ref}
        className={touchOptimizedClasses}
        style={style}
        {...props}
      >
        {children}
      </div>
    );
  }
);

TouchOptimized.displayName = 'TouchOptimized';

// 터치 최적화 버튼
interface TouchButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: 'sm' | 'md' | 'lg';
}

const TouchButton = forwardRef<HTMLButtonElement, TouchButtonProps>(
  ({ className, size = 'md', children, ...props }, ref) => {
    const sizeClasses = {
      sm: 'min-h-[40px] px-3 py-2 text-sm',
      md: 'min-h-[44px] px-4 py-3 text-base',
      lg: 'min-h-[48px] px-6 py-4 text-lg',
    };
    
    const touchButtonClasses = cn(
      'touch-manipulation',
      'inline-flex items-center justify-center',
      'rounded-lg font-medium transition-colors',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      'disabled:opacity-50 disabled:pointer-events-none',
      sizeClasses[size],
      className
    );
    
    return (
      <button
        ref={ref}
        className={touchButtonClasses}
        {...props}
      >
        {children}
      </button>
    );
  }
);

TouchButton.displayName = 'TouchButton';

export { TouchOptimized, TouchButton };
```

## 2. 접근성(Accessibility)

### 2.1 WCAG 2.1 AA 준수

#### 2.1.1 접근성 컴포넌트
```typescript
// frontend/design-system/components/Accessible/SkipLink.tsx
import React from 'react';

interface SkipLinkProps {
  href: string;
  children: React.ReactNode;
  className?: string;
}

// 스킵 링크 - 키보드 사용자가 메인 콘텐츠로 바로 이동
const SkipLink: React.FC<SkipLinkProps> = ({ 
  href, 
  children, 
  className = '' 
}) => {
  return (
    <a
      href={href}
      className={`
        sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4
        bg-primary text-primary-foreground px-4 py-2 rounded-md
        z-50 focus:outline-none focus:ring-2 focus:ring-ring
        ${className}
      `}
    >
      {children}
    </a>
  );
};

export default SkipLink;

// frontend/design-system/components/Accessible/FocusTrap.tsx
import React, { useEffect, useRef, ReactNode } from 'react';

interface FocusTrapProps {
  children: ReactNode;
  isActive: boolean;
  onEscape?: () => void;
}

// 포커스 트랩 - 모달 등에서 포커스 제어
const FocusTrap: React.FC<FocusTrapProps> = ({ 
  children, 
  isActive, 
  onEscape 
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  
  useEffect(() => {
    if (!isActive || !containerRef.current) return;
    
    // 현재 포커스된 요소 저장
    previousFocusRef.current = document.activeElement as HTMLElement;
    
    // 컨테이너 내의 포커스 가능한 요소들
    const focusableElements = containerRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as NodeListOf<HTMLElement>;
    
    if (focusableElements.length === 0) return;
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    // 첫 번째 요소에 포커스
    firstElement.focus();
    
    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      
      if (event.shiftKey) {
        // Shift + Tab: 마지막 요소에서 첫 번째 요소로
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: 첫 번째 요소에서 마지막 요소로
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };
    
    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && onEscape) {
        onEscape();
      }
    };
    
    // 이벤트 리스너 추가
    document.addEventListener('keydown', handleTabKey);
    document.addEventListener('keydown', handleEscapeKey);
    
    return () => {
      // 정리: 이벤트 리스너 제거
      document.removeEventListener('keydown', handleTabKey);
      document.removeEventListener('keydown', handleEscapeKey);
      
      // 이전 포커스된 요소로 복원
      if (previousFocusRef.current && previousFocusRef.current.focus) {
        previousFocusRef.current.focus();
      }
    };
  }, [isActive, onEscape]);
  
  return (
    <div ref={containerRef} tabIndex={-1}>
      {children}
    </div>
  );
};

export default FocusTrap;

// frontend/design-system/components/Accessible/Announcer.tsx
import React, { useEffect, useRef } from 'react';

interface AnnouncerProps {
  message: string;
  politeness?: 'polite' | 'assertive';
  timeout?: number;
}

// 스크린 리더 알림
const Announcer: React.FC<AnnouncerProps> = ({ 
  message, 
  politeness = 'polite',
  timeout = 1000 
}) => {
  const announcerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();
  
  useEffect(() => {
    if (!announcerRef.current || !message) return;
    
    // 이전 타임아웃 정리
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    // 메시지 설정
    announcerRef.current.textContent = message;
    
    // 타임아웃 후 메시지 정리
    timeoutRef.current = setTimeout(() => {
      if (announcerRef.current) {
        announcerRef.current.textContent = '';
      }
    }, timeout);
    
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [message, politeness, timeout]);
  
  return (
    <div
      ref={announcerRef}
      aria-live={politeness}
      aria-atomic="true"
      className="sr-only"
    />
  );
};

export default Announcer;

// frontend/design-system/components/Accessible/VisuallyHidden.tsx
import React, { HTMLAttributes } from 'react';

interface VisuallyHiddenProps extends HTMLAttributes<HTMLSpanElement> {
  as?: React.ElementType;
}

// 시각적으로 숨겨진 요소 (스크린 리더용)
const VisuallyHidden: React.FC<VisuallyHiddenProps> = ({ 
  as: Component = 'span', 
  children, 
  ...props 
}) => {
  return (
    <Component
      {...props}
      style={{
        position: 'absolute',
        width: '1px',
        height: '1px',
        padding: 0,
        margin: '-1px',
        overflow: 'hidden',
        clip: 'rect(0, 0, 0, 0)',
        whiteSpace: 'nowrap',
        border: 0,
        ...props.style
      }}
    >
      {children}
    </Component>
  );
};

export default VisuallyHidden;
```

#### 2.1.2 키보드 네비게이션
```typescript
// frontend/design-system/hooks/useKeyboardNavigation.ts
import { useEffect, useRef } from 'react';

interface KeyboardNavigationOptions {
  onEnter?: () => void;
  onSpace?: () => void;
  onEscape?: () => void;
  onArrowUp?: () => void;
  onArrowDown?: () => void;
  onArrowLeft?: () => void;
  onArrowRight?: () => void;
  onTab?: (isShiftTab: boolean) => void;
  enabled?: boolean;
}

// 키보드 네비게이션 훅
export const useKeyboardNavigation = (options: KeyboardNavigationOptions) => {
  const {
    onEnter,
    onSpace,
    onEscape,
    onArrowUp,
    onArrowDown,
    onArrowLeft,
    onArrowRight,
    onTab,
    enabled = true
  } = options;
  
  const handleKeyDown = (event: KeyboardEvent) => {
    if (!enabled) return;
    
    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        onEnter?.();
        break;
      case ' ':
      case 'Spacebar':
        event.preventDefault();
        onSpace?.();
        break;
      case 'Escape':
        event.preventDefault();
        onEscape?.();
        break;
      case 'ArrowUp':
        event.preventDefault();
        onArrowUp?.();
        break;
      case 'ArrowDown':
        event.preventDefault();
        onArrowDown?.();
        break;
      case 'ArrowLeft':
        event.preventDefault();
        onArrowLeft?.();
        break;
      case 'ArrowRight':
        event.preventDefault();
        onArrowRight?.();
        break;
      case 'Tab':
        event.preventDefault();
        onTab?.(event.shiftKey);
        break;
    }
  };
  
  useEffect(() => {
    if (!enabled) return;
    
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);
};

// frontend/design-system/hooks/useRovingTabIndex.ts
import { useState, useEffect, useRef } from 'react';

interface RovingTabIndexOptions {
  orientation?: 'horizontal' | 'vertical';
  loop?: boolean;
  initialIndex?: number;
}

// 로빙 탭인덱스 훅 (메뉴 등에서 사용)
export const useRovingTabIndex = <T extends HTMLElement>(
  items: Array<{ id: string; element?: T }>,
  options: RovingTabIndexOptions = {}
) => {
  const { orientation = 'vertical', loop = true, initialIndex = 0 } = options;
  const [focusedIndex, setFocusedIndex] = useState(initialIndex);
  const itemsRef = useRef<Array<{ id: string; element?: T }>>(items);
  
  useEffect(() => {
    itemsRef.current = items;
  }, [items]);
  
  const focusItem = (index: number) => {
    const item = itemsRef.current[index];
    if (item?.element) {
      item.element.focus();
      setFocusedIndex(index);
    }
  };
  
  const handleKeyDown = (event: KeyboardEvent) => {
    const isVertical = orientation === 'vertical';
    const incrementKey = isVertical ? 'ArrowDown' : 'ArrowRight';
    const decrementKey = isVertical ? 'ArrowUp' : 'ArrowLeft';
    
    switch (event.key) {
      case incrementKey:
        event.preventDefault();
        const nextIndex = (focusedIndex + 1) % itemsRef.current.length;
        if (loop || nextIndex < itemsRef.current.length) {
          focusItem(nextIndex);
        }
        break;
      case decrementKey:
        event.preventDefault();
        const prevIndex = focusedIndex === 0 ? itemsRef.current.length - 1 : focusedIndex - 1;
        if (loop || prevIndex >= 0) {
          focusItem(prevIndex);
        }
        break;
      case 'Home':
        event.preventDefault();
        focusItem(0);
        break;
      case 'End':
        event.preventDefault();
        focusItem(itemsRef.current.length - 1);
        break;
    }
  };
  
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [focusedIndex, orientation, loop]);
  
  return {
    focusedIndex,
    setFocusedIndex,
    focusItem
  };
};

// frontend/design-system/components/Accessible/MenuItem.tsx
import React, { forwardRef, useRef } from 'react';
import { cn } from '../../../utils/cn';

interface MenuItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  disabled?: boolean;
}

// 접근성 있는 메뉴 아이템
const MenuItem = forwardRef<HTMLButtonElement, MenuItemProps>(
  ({ className, active, disabled, children, ...props }, ref) => {
    const itemRef = useRef<HTMLButtonElement>(null);
    const combinedRef = (element: HTMLButtonElement) => {
      itemRef.current = element;
      if (typeof ref === 'function') {
        ref(element);
      } else if (ref) {
        ref.current = element;
      }
    };
    
    return (
      <button
        ref={combinedRef}
        role="menuitem"
        aria-disabled={disabled}
        aria-selected={active}
        className={cn(
          'w-full text-left px-3 py-2 text-sm rounded-md',
          'focus:bg-accent focus:text-accent-foreground',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          active && 'bg-accent text-accent-foreground',
          className
        )}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  }
);

MenuItem.displayName = 'MenuItem';

export default MenuItem;
```

### 2.2 색상 대비 및 시각적 접근성

#### 2.2.1 색상 대비 유틸리티
```typescript
// frontend/design-system/utils/colorUtils.ts
// 색상 대비율 계산 (WCAG 2.1 표준)
export const getLuminance = (r: number, g: number, b: number): number => {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c = c / 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
};

export const getContrastRatio = (color1: string, color2: string): number => {
  const hexToRgb = (hex: string) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 0, g: 0, b: 0 };
  };
  
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  
  const lum1 = getLuminance(rgb1.r, rgb1.g, rgb1.b);
  const lum2 = getLuminance(rgb2.r, rgb2.g, rgb2.b);
  
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  
  return (brightest + 0.05) / (darkest + 0.05);
};

// WCAG 등급 판정
export const getWCAGLevel = (contrastRatio: number): {
  AA: { normal: boolean; large: boolean };
  AAA: { normal: boolean; large: boolean };
} => {
  return {
    AA: {
      normal: contrastRatio >= 4.5,
      large: contrastRatio >= 3.0
    },
    AAA: {
      normal: contrastRatio >= 7.0,
      large: contrastRatio >= 4.5
    }
  };
};

// 색상 조합 검증
export const validateColorCombination = (
  foreground: string, 
  background: string
): {
  contrastRatio: number;
  wcagLevel: ReturnType<typeof getWCAGLevel>;
  isValid: boolean;
} => {
  const contrastRatio = getContrastRatio(foreground, background);
  const wcagLevel = getWCAGLevel(contrastRatio);
  const isValid = wcagLevel.AA.normal;
  
  return {
    contrastRatio,
    wcagLevel,
    isValid
  };
};

// 텍스트 크기에 따른 최소 대비율
export const getMinimumContrastRatio = (isLargeText: boolean): number => {
  return isLargeText ? 3.0 : 4.5;
};

// 대체 텍스트 색상 제안
export const suggestAlternativeColors = (
  foreground: string, 
  background: string,
  targetRatio: number = 4.5
): Array<{ color: string; contrastRatio: number }> => {
  // 단순화된 색상 조정 알고리즘
  const suggestions: Array<{ color: string; contrastRatio: number }> = [];
  
  // 밝기 조정
  const adjustBrightness = (color: string, factor: number): string => {
    const hex = color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    
    const adjust = (value: number) => {
      const adjusted = Math.round(value * factor);
      return Math.max(0, Math.min(255, adjusted));
    };
    
    const newR = adjust(r).toString(16).padStart(2, '0');
    const newG = adjust(g).toString(16).padStart(2, '0');
    const newB = adjust(b).toString(16).padStart(2, '0');
    
    return `#${newR}${newG}${newB}`;
  };
  
  // 다양한 밝기 조정으로 대안 색상 생성
  for (let factor = 0.5; factor <= 2.0; factor += 0.1) {
    const adjustedColor = adjustBrightness(foreground, factor);
    const contrastRatio = getContrastRatio(adjustedColor, background);
    
    if (contrastRatio >= targetRatio) {
      suggestions.push({
        color: adjustedColor,
        contrastRatio
      });
    }
  }
  
  // 대비율 기준 정렬
  return suggestions.sort((a, b) => b.contrastRatio - a.contrastRatio);
};

// frontend/design-system/components/Accessible/ColorContrastChecker.tsx
import React, { useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';
import { validateColorCombination, suggestAlternativeColors } from '../../../utils/colorUtils';

interface ColorContrastCheckerProps {
  foreground: string;
  background: string;
  onColorChange?: (foreground: string, background: string) => void;
}

// 색상 대비 검사기 (개발용)
const ColorContrastChecker: React.FC<ColorContrastCheckerProps> = ({
  foreground,
  background,
  onColorChange
}) => {
  const [showChecker, setShowChecker] = useState(false);
  const [localForeground, setLocalForeground] = useState(foreground);
  const [localBackground, setLocalBackground] = useState(background);
  
  const validation = validateColorCombination(localForeground, localBackground);
  const alternatives = suggestAlternativeColors(localForeground, localBackground);
  
  const handleColorChange = (newForeground: string, newBackground: string) => {
    setLocalForeground(newForeground);
    setLocalBackground(newBackground);
    onColorChange?.(newForeground, newBackground);
  };
  
  if (!showChecker) {
    return (
      <button
        onClick={() => setShowChecker(true)}
        className="fixed bottom-4 right-4 p-2 bg-white rounded-full shadow-lg border"
        aria-label="색상 대비 검사기 열기"
      >
        <Eye className="h-5 w-5" />
      </button>
    );
  }
  
  return (
    <div className="fixed bottom-4 right-4 w-80 bg-white rounded-lg shadow-lg border p-4 z-50">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">색상 대비 검사기</h3>
        <button
          onClick={() => setShowChecker(false)}
          className="p-1 hover:bg-gray-100 rounded"
          aria-label="닫기"
        >
          <EyeOff className="h-4 w-4" />
        </button>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">전경색</label>
          <div className="flex items-center space-x-2">
            <input
              type="color"
              value={localForeground}
              onChange={(e) => handleColorChange(e.target.value, localBackground)}
              className="w-12 h-8 border rounded"
            />
            <input
              type="text"
              value={localForeground}
              onChange={(e) => handleColorChange(e.target.value, localBackground)}
              className="flex-1 px-2 py-1 border rounded text-sm"
            />
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-1">배경색</label>
          <div className="flex items-center space-x-2">
            <input
              type="color"
              value={localBackground}
              onChange={(e) => handleColorChange(localForeground, e.target.value)}
              className="w-12 h-8 border rounded"
            />
            <input
              type="text"
              value={localBackground}
              onChange={(e) => handleColorChange(localForeground, e.target.value)}
              className="flex-1 px-2 py-1 border rounded text-sm"
            />
          </div>
        </div>
        
        <div className="border-t pt-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">대비율</span>
            <span className={`text-sm font-bold ${
              validation.isValid ? 'text-green-600' : 'text-red-600'
            }`}>
              {validation.contrastRatio.toFixed(2)}:1
            </span>
          </div>
          
          <div className="text-xs space-y-1">
            <div className={`flex items-center space-x-2 ${
              validation.wcagLevel.AA.normal ? 'text-green-600' : 'text-red-600'
            }`}>
              <span>AA 일반 텍스트:</span>
              <span>{validation.wcagLevel.AA.normal ? '✓' : '✗'}</span>
            </div>
            <div className={`flex items-center space-x-2 ${
              validation.wcagLevel.AA.large ? 'text-green-600' : 'text-red-600'
            }`}>
              <span>AA 큰 텍스트:</span>
              <span>{validation.wcagLevel.AA.large ? '✓' : '✗'}</span>
            </div>
            <div className={`flex items-center space-x-2 ${
              validation.wcagLevel.AAA.normal ? 'text-green-600' : 'text-red-600'
            }`}>
              <span>AAA 일반 텍스트:</span>
              <span>{validation.wcagLevel.AAA.normal ? '✓' : '✗'}</span>
            </div>
          </div>
        </div>
        
        {!validation.isValid && alternatives.length > 0 && (
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium mb-2">대체 색상 제안</h4>
            <div className="grid grid-cols-6 gap-2">
              {alternatives.slice(0, 12).map((alt, index) => (
                <button
                  key={index}
                  onClick={() => handleColorChange(alt.color, localBackground)}
                  className="w-10 h-10 rounded border-2 border-gray-200 hover:border-gray-400"
                  style={{ backgroundColor: alt.color }}
                  title={`대비율: ${alt.contrastRatio.toFixed(2)}:1`}
                  aria-label={`대체 색상 ${index + 1}, 대비율 ${alt.contrastRatio.toFixed(2)}:1`}
                />
              ))}
            </div>
          </div>
        )}
        
        <div className="border-t pt-4">
          <div 
            className="p-4 rounded text-center"
            style={{ 
              backgroundColor: localBackground, 
              color: localForeground 
            }}
          >
            예시 텍스트
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColorContrastChecker;
```

### 2.3 다국어 지원

#### 2.3.1 국제화(i18n) 시스템
```typescript
// frontend/i18n/locales/ko.json
{
  "common": {
    "loading": "로딩 중...",
    "error": "오류",
    "success": "성공",
    "cancel": "취소",
    "confirm": "확인",
    "save": "저장",
    "delete": "삭제",
    "edit": "편집",
    "search": "검색",
    "back": "뒤로",
    "next": "다음",
    "previous": "이전",
    "close": "닫기",
    "submit": "제출",
    "reset": "초기화",
    "refresh": "새로고침",
    "help": "도움말",
    "settings": "설정",
    "profile": "프로필",
    "logout": "로그아웃",
    "login": "로그인",
    "register": "회원가입",
    "yes": "예",
    "no": "아니오",
    "ok": "확인",
    "retry": "재시도"
  },
  "navigation": {
    "dashboard": "대시보드",
    "stocks": "주식 검색",
    "sentiment": "센티먼트 분석",
    "watchlist": "관심종목",
    "portfolio": "포트폴리오",
    "alerts": "알림",
    "settings": "설정",
    "help": "도움말"
  },
  "stocks": {
    "search_placeholder": "주식 이름 또는 심볼 검색",
    "no_results": "검색 결과가 없습니다",
    "search_results": "검색 결과",
    "company_name": "회사명",
    "symbol": "심볼",
    "price": "가격",
    "change": "변동",
    "change_percent": "변동률",
    "volume": "거래량",
    "market_cap": "시가총액",
    "pe_ratio": "PER",
    "dividend": "배당률",
    "high_52w": "52주 최고",
    "low_52w": "52주 최저",
    "add_to_watchlist": "관심종목 추가",
    "remove_from_watchlist": "관심종목 제거",
    "view_details": "상세 정보 보기",
    "historical_data": "과거 데이터",
    "news": "뉴스",
    "analysis": "분석"
  },
  "sentiment": {
    "overall_sentiment": "전체 센티먼트",
    "reddit_sentiment": "Reddit 센티먼트",
    "twitter_sentiment": "Twitter 센티먼트",
    "mention_count": "언급 횟수",
    "positive": "긍정",
    "negative": "부정",
    "neutral": "중립",
    "trending": "트렌딩",
    "recent_mentions": "최근 언급",
    "sentiment_score": "센티먼트 점수",
    "confidence": "신뢰도",
    "source": "출처",
    "time": "시간",
    "no_mentions": "언급이 없습니다",
    "loading_mentions": "언급 로딩 중..."
  },
  "accessibility": {
    "skip_to_main": "메인 콘텐츠로 바로가기",
    "skip_to_navigation": "네비게이션으로 바로가기",
    "menu_open": "메뉴 열기",
    "menu_close": "메뉴 닫기",
    "search_open": "검색 열기",
    "search_close": "검색 닫기",
    "previous_month": "이전 달",
    "next_month": "다음 달",
    "previous_year": "이전 년",
    "next_year": "다음 년",
    "calendar_today": "오늘",
    "date_picker": "날짜 선택",
    "time_picker": "시간 선택",
    "color_contrast_checker": "색상 대비 검사기",
    "increase_font_size": "글자 크기 증가",
    "decrease_font_size": "글자 크기 감소",
    "high_contrast": "고대비 모드",
    "screen_reader_only": "스크린 리더 전용"
  },
  "errors": {
    "network_error": "네트워크 오류가 발생했습니다.",
    "server_error": "서버 오류가 발생했습니다.",
    "not_found": "페이지를 찾을 수 없습니다.",
    "unauthorized": "접근 권한이 없습니다.",
    "validation_error": "입력값을 확인해주세요.",
    "timeout_error": "요청 시간이 초과되었습니다.",
    "unknown_error": "알 수 없는 오류가 발생했습니다.",
    "try_again": "다시 시도해주세요.",
    "contact_support": "고객센터에 문의해주세요."
  }
}

// frontend/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';
import { getStoredLanguage, setStoredLanguage } from '../utils/storage';

const initI18n = () => {
  i18n
    .use(Backend)
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      fallbackLng: 'en',
      debug: process.env.NODE_ENV === 'development',
      
      interpolation: {
        escapeValue: false
      },
      
      detection: {
        order: ['localStorage', 'navigator', 'htmlTag'],
        caches: ['localStorage'],
        lookupLocalStorage: 'language'
      },
      
      backend: {
        loadPath: '/locales/{{lng}}/{{ns}}.json'
      },
      
      react: {
        useSuspense: false
      }
    });
};

export default initI18n;

// frontend/hooks/useTranslation.ts
import { useTranslation as useReactTranslation } from 'react-i18next';
import { i18n } from 'i18next';

export const useTranslation = (namespace?: string) => {
  const { t, i18n: i18nInstance } = useReactTranslation(namespace);
  
  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
    setStoredLanguage(lng);
    
    // HTML lang 속성 업데이트
    document.documentElement.lang = lng;
    
    // RTL/LTR 방향 설정
    const rtlLanguages = ['ar', 'he', 'fa'];
    const isRTL = rtlLanguages.includes(lng);
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
  };
  
  const currentLanguage = i18nInstance.language;
  
  return {
    t,
    i18n: i18nInstance,
    changeLanguage,
    currentLanguage,
    isRTL: ['ar', 'he', 'fa'].includes(currentLanguage)
  };
};

// frontend/components/LanguageSelector.tsx
import React from 'react';
import { Globe } from 'lucide-react';
import { Button } from './design-system/components/Button';
import { useTranslation } from '../hooks/useTranslation';

const languages = [
  { code: 'ko', name: '한국어', flag: '🇰🇷' },
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'ja', name: '日本語', flag: '🇯🇵' },
  { code: 'zh', name: '中文', flag: '🇨🇳' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'fr', name: 'Français', flag: '🇫🇷' },
  { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
  { code: 'ar', name: 'العربية', flag: '🇸🇦' }
];

const LanguageSelector: React.FC = () => {
  const { currentLanguage, changeLanguage, t } = useTranslation();
  const [isOpen, setIsOpen] = React.useState(false);
  
  const currentLang = languages.find(lang => lang.code === currentLanguage) || languages[0];
  
  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2"
        aria-label={t('accessibility.language_select')}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="text-lg">{currentLang.flag}</span>
        <span className="hidden sm:inline">{currentLang.name}</span>
        <Globe className="h-4 w-4" />
      </Button>
      
      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border z-50">
          <div className="py-1" role="listbox">
            {languages.map((language) => (
              <button
                key={language.code}
                className={`
                  w-full text-left px-4 py-2 text-sm hover:bg-gray-100 flex items-center space-x-3
                  ${currentLanguage === language.code ? 'bg-blue-50 text-blue-600' : 'text-gray-700'}
                `}
                onClick={() => {
                  changeLanguage(language.code);
                  setIsOpen(false);
                }}
                role="option"
                aria-selected={currentLanguage === language.code}
              >
                <span className="text-lg">{language.flag}</span>
                <span>{language.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LanguageSelector;
```

## 3. 사용자 피드백 및 테스트

### 3.1 사용자 테스트 방법론

#### 3.1.1 사용자 테스트 계획
```typescript
// frontend/testing/userTesting.ts
export interface UserTestPlan {
  id: string;
  title: string;
  description: string;
  objectives: string[];
  participants: {
    target: string;
    count: number;
    criteria: string[];
  };
  tasks: UserTestTask[];
  metrics: UserTestMetric[];
  timeline: {
    preparation: number;
    execution: number;
    analysis: number;
  };
}

export interface UserTestTask {
  id: string;
  title: string;
  description: string;
  steps: string[];
  expectedOutcome: string;
  timeLimit?: number;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface UserTestMetric {
  id: string;
  name: string;
  type: 'quantitative' | 'qualitative';
  measurement: string;
  target?: number;
}

// 주식 검색 기능 사용자 테스트 계획
export const stockSearchUserTestPlan: UserTestPlan = {
  id: 'stock-search-001',
  title: '주식 검색 기능 사용자 테스트',
  description: '사용자가 주식 정보를 검색하고 조회하는 과정의 사용성 평가',
  objectives: [
    '주식 검색 기능의 직관성 평가',
    '검색 결과의 이해도 평가',
    '필터링 기능의 사용성 평가',
    '모바일 환경에서의 사용성 평가'
  ],
  participants: {
    target: '주식 투자 경험 1년 이상 사용자',
    count: 10,
    criteria: [
      '25-55세',
      '주식 투자 경험 1년 이상',
      '모바일 앱 사용 경험',
      '다양한 직업군'
    ]
  },
  tasks: [
    {
      id: 'task-1',
      title: '기본 주식 검색',
      description: '사용자가 특정 주식을 검색하고 상세 정보를 확인',
      steps: [
        '애플리케이션에 접속',
        '검색창에 "Apple" 입력',
        '검색 결과에서 Apple Inc. 선택',
        '주식 상세 정보 확인'
      ],
      expectedOutcome: '사용자가 3분 이내에 Apple 주식 정보를 확인',
      timeLimit: 180,
      difficulty: 'easy'
    },
    {
      id: 'task-2',
      title: '고급 필터링',
      description: '사용자가 특정 조건에 맞는 주식을 검색',
      steps: [
        '검색 필터 열기',
        '섹터를 "기술"로 설정',
        '시가총액을 "1조 이상"으로 설정',
        '검색 실행',
        '결과 확인'
      ],
      expectedOutcome: '사용자가 5분 이내에 필터링된 결과를 확인',
      timeLimit: 300,
      difficulty: 'medium'
    },
    {
      id: 'task-3',
      title: '관심종목 추가',
      description: '사용자가 검색한 주식을 관심종목에 추가',
      steps: [
        '주식 상세 페이지에서 관심종목 버튼 클릭',
        '알림 설정 구성',
        '관심종목 목록에서 추가 확인'
      ],
      expectedOutcome: '사용자가 2분 이내에 관심종목 추가 완료',
      timeLimit: 120,
      difficulty: 'easy'
    }
  ],
  metrics: [
    {
      id: 'metric-1',
      name: '작업 완료율',
      type: 'quantitative',
      measurement: '성공적으로 완료한 작업의 비율',
      target: 85
    },
    {
      id: 'metric-2',
      name: '평균 소요 시간',
      type: 'quantitative',
      measurement: '각 작업별 평균 소요 시간',
      target: 180
    },
    {
      id: 'metric-3',
      name: '오류 발생률',
      type: 'quantitative',
      measurement: '작업 중 발생한 오류의 평균 횟수',
      target: 1
    },
    {
      id: 'metric-4',
      name: '사용자 만족도',
      type: 'qualitative',
      measurement: '5점 척도 만족도 점수',
      target: 4.0
    },
    {
      id: 'metric-5',
      name: '사용성 문제 발견',
      type: 'qualitative',
      measurement: '발견된 사용성 문제의 유형과 심각도'
    }
  ],
  timeline: {
    preparation: 5, // 일
    execution: 3, // 일
    analysis: 2 // 일
  }
};

// 사용자 테스트 실행 도우미
export class UserTestExecutor {
  private testPlan: UserTestPlan;
  private results: UserTestResult[] = [];
  
  constructor(testPlan: UserTestPlan) {
    this.testPlan = testPlan;
  }
  
  async executeTest(): Promise<UserTestReport> {
    console.log(`사용자 테스트 시작: ${this.testPlan.title}`);
    
    // 테스트 환경 준비
    await this.prepareTestEnvironment();
    
    // 참가자 모집
    const participants = await this.recruitParticipants();
    
    // 테스트 실행
    for (const participant of participants) {
      const result = await this.runTestSession(participant);
      this.results.push(result);
    }
    
    // 결과 분석
    const report = await this.analyzeResults();
    
    return report;
  }
  
  private async prepareTestEnvironment(): Promise<void> {
    // 테스트 환경 설정
    console.log('테스트 환경 준비 중...');
    
    // 테스트 데이터 준비
    await this.prepareTestData();
    
    // 녹화 환경 설정
    await this.setupRecording();
    
    // 테스트 기기 준비
    await this.prepareDevices();
  }
  
  private async recruitParticipants(): Promise<TestParticipant[]> {
    // 참가자 모집 로직
    console.log('참가자 모집 중...');
    
    // 실제 구현에서는 참가자 모집 및 선별 프로세스
    return [
      {
        id: 'p001',
        demographics: {
          age: 35,
          gender: 'male',
          experience: 'intermediate'
        }
      }
      // ... 더 많은 참가자
    ];
  }
  
  private async runTestSession(participant: TestParticipant): Promise<UserTestResult> {
    console.log(`참가자 ${participant.id} 테스트 세션 시작`);
    
    const sessionResult: UserTestResult = {
      participantId: participant.id,
      startTime: new Date(),
      tasks: [],
      satisfaction: 0,
      feedback: ''
    };
    
    // 사전 인터뷰
    await this.conductPreInterview(participant, sessionResult);
    
    // 작업 수행
    for (const task of this.testPlan.tasks) {
      const taskResult = await this.executeTask(participant, task);
      sessionResult.tasks.push(taskResult);
    }
    
    // 사후 인터뷰
    await this.conductPostInterview(participant, sessionResult);
    
    sessionResult.endTime = new Date();
    
    return sessionResult;
  }
  
  private async executeTask(
    participant: TestParticipant, 
    task: UserTestTask
  ): Promise<TaskResult> {
    console.log(`작업 실행: ${task.title}`);
    
    const taskResult: TaskResult = {
      taskId: task.id,
      startTime: new Date(),
      steps: [],
      errors: [],
      completed: false,
      timeSpent: 0,
      satisfaction: 0
    };
    
    // 작업 안내
    await this.instructTask(participant, task);
    
    // 작업 수행 관찰
    const observation = await this.observeTaskExecution(participant, task);
    
    // 결과 기록
    taskResult.completed = observation.completed;
    taskResult.timeSpent = observation.timeSpent;
    taskResult.steps = observation.steps;
    taskResult.errors = observation.errors;
    taskResult.endTime = new Date();
    
    // 만족도 평가
    taskResult.satisfaction = await this.evaluateTaskSatisfaction(participant, task);
    
    return taskResult;
  }
  
  private async analyzeResults(): Promise<UserTestReport> {
    console.log('결과 분석 중...');
    
    // 정량적 분석
    const quantitativeAnalysis = this.performQuantitativeAnalysis();
    
    // 정성적 분석
    const qualitativeAnalysis = this.performQualitativeAnalysis();
    
    // 문제점 도출
    const issues = this.identifyIssues();
    
    // 개선 제안
    const recommendations = this.generateRecommendations(issues);
    
    return {
      testPlan: this.testPlan,
      results: this.results,
      quantitativeAnalysis,
      qualitativeAnalysis,
      issues,
      recommendations,
      generatedAt: new Date()
    };
  }
  
  private performQuantitativeAnalysis(): QuantitativeAnalysis {
    const completedTasks = this.results.flatMap(r => r.tasks).filter(t => t.completed);
    const totalTasks = this.results.flatMap(r => r.tasks);
    
    return {
      taskCompletionRate: (completedTasks.length / totalTasks.length) * 100,
      averageTimeSpent: totalTasks.reduce((sum, task) => sum + task.timeSpent, 0) / totalTasks.length,
      errorRate: totalTasks.reduce((sum, task) => sum + task.errors.length, 0) / totalTasks.length,
      satisfactionScore: this.results.reduce((sum, result) => sum + result.satisfaction, 0) / this.results.length
    };
  }
  
  private performQualitativeAnalysis(): QualitativeAnalysis {
    // 정성적 데이터 분석
    const feedbackThemes = this.extractFeedbackThemes();
    const commonIssues = this.identifyCommonIssues();
    const positivePatterns = this.identifyPositivePatterns();
    
    return {
      feedbackThemes,
      commonIssues,
      positivePatterns,
      notableQuotes: this.extractNotableQuotes()
    };
  }
  
  private identifyIssues(): UsabilityIssue[] {
    const issues: UsabilityIssue[] = [];
    
    // 작업 실패 분석
    const failedTasks = this.results.flatMap(r => r.tasks).filter(t => !t.completed);
    failedTasks.forEach(task => {
      if (task.timeSpent > (this.testPlan.tasks.find(t => t.id === task.taskId)?.timeLimit || 300)) {
        issues.push({
          type: 'time_out',
          severity: 'high',
          description: `작업 ${task.taskId} 시간 초과`,
          frequency: 1
        });
      }
    });
    
    // 에러 패턴 분석
    const errorPatterns = this.analyzeErrorPatterns();
    issues.push(...errorPatterns);
    
    return issues;
  }
  
  private generateRecommendations(issues: UsabilityIssue[]): Recommendation[] {
    return issues.map(issue => ({
      issue: issue.type,
      priority: this.calculatePriority(issue),
      description: this.generateRecommendationDescription(issue),
      implementation: this.generateImplementationPlan(issue)
    }));
  }
}

// 인터페이스 정의
interface TestParticipant {
  id: string;
  demographics: {
    age: number;
    gender: string;
    experience: string;
  };
}

interface UserTestResult {
  participantId: string;
  startTime: Date;
  endTime?: Date;
  tasks: TaskResult[];
  satisfaction: number;
  feedback: string;
}

interface TaskResult {
  taskId: string;
  startTime: Date;
  endTime?: Date;
  steps: TaskStep[];
  errors: TaskError[];
  completed: boolean;
  timeSpent: number;
  satisfaction: number;
}

interface TaskStep {
  stepNumber: number;
  description: string;
  timeSpent: number;
  success: boolean;
}

interface TaskError {
  timestamp: Date;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

interface UserTestReport {
  testPlan: UserTestPlan;
  results: UserTestResult[];
  quantitativeAnalysis: QuantitativeAnalysis;
  qualitativeAnalysis: QualitativeAnalysis;
  issues: UsabilityIssue[];
  recommendations: Recommendation[];
  generatedAt: Date;
}

interface QuantitativeAnalysis {
  taskCompletionRate: number;
  averageTimeSpent: number;
  errorRate: number;
  satisfactionScore: number;
}

interface QualitativeAnalysis {
  feedbackThemes: string[];
  commonIssues: string[];
  positivePatterns: string[];
  notableQuotes: string[];
}

interface UsabilityIssue {
  type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  frequency: number;
}

interface Recommendation {
  issue: string;
  priority: 'low' | 'medium' | 'high';
  description: string;
  implementation: string;
}
```

이 사용자 경험 및 접근성 개선 문서는 모든 사용자가 동등하게 서비스를 이용할 수 있도록 설계 원칙, 기술 구현, 테스트 방법론을 포괄적으로 다룹니다. WCAG 2.1 AA 준수, 반응형 디자인, 다국어 지원 등을 통해 포용적인 디지털 경험을 제공할 수 있습니다.

## 4. Enhanced Stock Search UI/UX 디자인

### 4.1 검색 인터페이스 개선

#### 4.1.1 현재 구조 vs 개선된 구조
```python
# 현재 구조
"""
[검색창] [검색 버튼] [클리어 버튼]
[검색 결과 목록]
[필터 드롭다운]
"""

# 개선된 구조
"""
[🔍 검색창 (자동완성 포함)] [⚙️ 고급 필터]
[📋 검색 히스토리 / 🔥 인기 검색어]
[📊 실시간 검색 결과 (카드 형태)]
[🏷️ 빠른 필터 태그들]
"""
```

#### 4.1.2 자동완성 UI 디자인
```python
# components/AutocompleteDropdown.py
import streamlit as st
from typing import List, Dict, Any, Callable
from dataclasses import dataclass

@dataclass
class AutocompleteSuggestion:
    symbol: str
    company_name: str
    stock_type: str
    exchange: str
    relevance_score: float
    current_price: Optional[float] = None
    market_cap: Optional[float] = None

class AutocompleteDropdown:
    """자동완성 드롭다운 컴포넌트"""
    
    def __init__(self, component_id: str = "autocomplete"):
        self.component_id = component_id
        self.selected_index = 0
        self.is_open = False
    
    def render(self,
              suggestions: List[AutocompleteSuggestion],
              on_select: Callable[[AutocompleteSuggestion], None],
              query: str) -> None:
        """자동완성 드롭다운 렌더링"""
        if not suggestions:
            return
        
        with st.container():
            # 드롭다운 스타일 적용
            st.markdown("""
            <style>
            .autocomplete-dropdown {
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                background: white;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                max-height: 300px;
                overflow-y: auto;
                z-index: 1000;
            }
            
            .autocomplete-item {
                padding: 12px 16px;
                border-bottom: 1px solid #f1f5f9;
                cursor: pointer;
                transition: background-color 0.2s;
            }
            
            .autocomplete-item:hover, .autocomplete-item.selected {
                background-color: #f8fafc;
            }
            
            .autocomplete-item:last-child {
                border-bottom: none;
            }
            
            .symbol {
                font-weight: 600;
                color: #1e40af;
            }
            
            .company-name {
                color: #64748b;
                font-size: 0.9em;
            }
            
            .meta-info {
                display: flex;
                justify-content: space-between;
                margin-top: 4px;
                font-size: 0.8em;
                color: #94a3b8;
            }
            
            .highlight {
                background-color: #fef3c7;
                padding: 1px 2px;
                border-radius: 2px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # 자동완성 항목 렌더링
            for i, suggestion in enumerate(suggestions):
                is_selected = i == self.selected_index
                
                # 검색어 하이라이트
                highlighted_symbol = self._highlight_text(suggestion.symbol, query)
                highlighted_name = self._highlight_text(suggestion.company_name, query)
                
                item_html = f"""
                <div class="autocomplete-item {'selected' if is_selected else ''}"
                     onclick="selectSuggestion('{suggestion.symbol}')"
                     data-symbol="{suggestion.symbol}">
                    <div class="symbol">{highlighted_symbol}</div>
                    <div class="company-name">{highlighted_name}</div>
                    <div class="meta-info">
                        <span>{suggestion.stock_type} • {suggestion.exchange}</span>
                        <span>관련도: {suggestion.relevance_score:.0f}</span>
                    </div>
                </div>
                """
                
                st.markdown(item_html, unsafe_allow_html=True)
                
                # JavaScript 이벤트 핸들러
                if st.button(f"Select {suggestion.symbol}", key=f"select_{i}", help="선택"):
                    on_select(suggestion)
    
    def _highlight_text(self, text: str, query: str) -> str:
        """검색어 하이라이트 처리"""
        if not query:
            return text
        
        query_lower = query.lower()
        text_lower = text.lower()
        
        if query_lower not in text_lower:
            return text
        
        # 하이라이트 위치 찾기
        start_idx = text_lower.find(query_lower)
        end_idx = start_idx + len(query)
        
        # 하이라이트 적용
        highlighted = (
            text[:start_idx] +
            f'<span class="highlight">{text[start_idx:end_idx]}</span>' +
            text[end_idx:]
        )
        
        return highlighted
```

#### 4.1.3 검색 결과 카드 디자인
```python
# components/StockResultCard.py
import streamlit as st
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class StockResult:
    symbol: str
    company_name: str
    stock_type: str
    exchange: str
    sector: str
    current_price: Optional[float]
    previous_close: Optional[float]
    day_change: Optional[float]
    day_change_pct: Optional[float]
    volume: Optional[int]
    market_cap: Optional[float]
    relevance_score: float
    sentiment_score: Optional[float]

class StockResultCard:
    """검색 결과 카드 컴포넌트"""
    
    def __init__(self, component_id: str = "stock_card"):
        self.component_id = component_id
    
    def render(self,
              stock: StockResult,
              on_select: Optional[Callable[[str], None]] = None,
              on_watchlist: Optional[Callable[[str], None]] = None) -> None:
        """주식 결과 카드 렌더링"""
        
        # 카드 스타일
        st.markdown("""
        <style>
        .stock-card {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            background: white;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .stock-card:hover {
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transform: translateY(-1px);
        }
        
        .stock-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .stock-symbol {
            font-size: 1.2em;
            font-weight: 700;
            color: #1e40af;
        }
        
        .stock-price {
            font-size: 1.1em;
            font-weight: 600;
        }
        
        .price-positive {
            color: #059669;
        }
        
        .price-negative {
            color: #dc2626;
        }
        
        .stock-company {
            color: #64748b;
            margin-bottom: 8px;
        }
        
        .stock-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
            color: #64748b;
            margin-bottom: 12px;
        }
        
        .stock-actions {
            display: flex;
            gap: 8px;
        }
        
        .action-button {
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid #d1d5db;
            background: white;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        
        .action-button:hover {
            background: #f3f4f6;
        }
        
        .action-button.primary {
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
        }
        
        .action-button.primary:hover {
            background: #2563eb;
        }
        
        .sentiment-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-left: 4px;
        }
        
        .sentiment-positive {
            background: #10b981;
        }
        
        .sentiment-negative {
            background: #ef4444;
        }
        
        .sentiment-neutral {
            background: #6b7280;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 가격 변화 계산
        price_change_color = "price-positive" if (stock.day_change or 0) >= 0 else "price-negative"
        price_change_symbol = "+" if (stock.day_change or 0) >= 0 else ""
        
        # 센티먼트 표시기
        sentiment_indicator = ""
        if stock.sentiment_score is not None:
            if stock.sentiment_score > 0.1:
                sentiment_indicator = '<span class="sentiment-indicator sentiment-positive"></span>'
            elif stock.sentiment_score < -0.1:
                sentiment_indicator = '<span class="sentiment-indicator sentiment-negative"></span>'
            else:
                sentiment_indicator = '<span class="sentiment-indicator sentiment-neutral"></span>'
        
        # 카드 HTML 생성
        card_html = f"""
        <div class="stock-card">
            <div class="stock-header">
                <div class="stock-symbol">{stock.symbol}{sentiment_indicator}</div>
                <div class="stock-price {price_change_color}">
                    ${stock.current_price:.2f if stock.current_price else "N/A"}
                </div>
            </div>
            <div class="stock-company">{stock.company_name}</div>
            <div class="stock-meta">
                <span>{stock.stock_type} • {stock.exchange}</span>
                <span class="{price_change_color}">
                    {price_change_symbol}{stock.day_change:.2f} ({price_change_symbol}{stock.day_change_pct:.2f}%)
                </span>
            </div>
            <div class="stock-actions">
                <button class="action-button primary" onclick="viewChart('{stock.symbol}')">
                    📊 차트 보기
                </button>
                <button class="action-button" onclick="addToWatchlist('{stock.symbol}')">
                    ⭐ 관심종목
                </button>
            </div>
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
        
        # Streamlit 버튼 (JavaScript 대체)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 차트 보기", key=f"chart_{stock.symbol}"):
                if on_select:
                    on_select(stock.symbol)
        
        with col2:
            if st.button("⭐ 관심종목", key=f"watchlist_{stock.symbol}"):
                if on_watchlist:
                    on_watchlist(stock.symbol)
```

#### 4.1.4 향상된 관심종목 패널
```python
# components/EnhancedWatchlist.py
import streamlit as st
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class WatchlistItem:
    symbol: str
    company_name: str
    category: str
    note: str
    added_date: str
    current_price: Optional[float]
    day_change: Optional[float]
    day_change_pct: Optional[float]

class EnhancedWatchlist:
    """향상된 관심종목 컴포넌트"""
    
    def __init__(self, component_id: str = "watchlist"):
        self.component_id = component_id
    
    def render(self,
              watchlist_items: List[WatchlistItem],
              on_select: Optional[Callable[[str], None]] = None,
              on_edit: Optional[Callable[[str], Dict[str, Any]], None]] = None,
              on_remove: Optional[Callable[[str], None]] = None) -> None:
        """향상된 관심종목 패널 렌더링"""
        
        st.markdown("### 📁 My Watchlist")
        
        # 카테고리별 그룹화
        categories = {}
        for item in watchlist_items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        # 카테고리별 렌더링
        for category, items in categories.items():
            with st.expander(f"📈 {category} ({len(items)}개)", expanded=True):
                for item in items:
                    self._render_watchlist_item(item, on_select, on_edit, on_remove)
        
        # 새 카테고리 추가
        if st.button("➕ 카테고리 추가", key="add_category"):
            self._show_add_category_dialog()
    
    def _render_watchlist_item(self,
                              item: WatchlistItem,
                              on_select: Optional[Callable[[str], None]],
                              on_edit: Optional[Callable[[str], Dict[str, Any]], None]],
                              on_remove: Optional[Callable[[str], None]]) -> None:
        """관심종목 아이템 렌더링"""
        
        # 가격 변화 색상
        price_color = "🟢" if (item.day_change or 0) >= 0 else "🔴"
        price_change = f"{price_color} {item.day_change:+.2f} ({item.day_change_pct:+.2f}%)" if item.day_change else ""
        
        col_symbol, col_price, col_actions = st.columns([2, 2, 1])
        
        with col_symbol:
            # 심볼과 회사명
            symbol_text = f"**{item.symbol}**"
            if item.note:
                symbol_text += f' 💭 "{item.note}"'
            
            st.markdown(symbol_text)
            st.markdown(f"<small style='color: #64748b;'>{item.company_name}</small>", unsafe_allow_html=True)
        
        with col_price:
            # 가격 정보
            if item.current_price:
                st.markdown(f"**${item.current_price:.2f}**")
                if price_change:
                    st.markdown(f"<small>{price_change}</small>", unsafe_allow_html=True)
            else:
                st.markdown("가격 정보 없음")
        
        with col_actions:
            # 액션 버튼
            col_view, col_edit, col_remove = st.columns(3)
            
            with col_view:
                if st.button("📊", key=f"view_{item.symbol}", help="차트 보기"):
                    if on_select:
                        on_select(item.symbol)
            
            with col_edit:
                if st.button("✏️", key=f"edit_{item.symbol}", help="편집"):
                    if on_edit:
                        on_edit(item.symbol, {
                            'category': item.category,
                            'note': item.note
                        })
            
            with col_remove:
                if st.button("🗑️", key=f"remove_{item.symbol}", help="제거"):
                    if on_remove:
                        on_remove(item.symbol)
    
    def _show_add_category_dialog(self):
        """카테고리 추가 다이얼로그"""
        with st.form("add_category_form"):
            new_category = st.text_input("새 카테고리 이름")
            submitted = st.form_submit_button("추가")
            
            if submitted and new_category:
                # 카테고리 추가 로직
                st.success(f"'{new_category}' 카테고리가 추가되었습니다.")
                st.rerun()
```

## 5. Social Sentiment Tracker UI/UX 디자인

### 5.1 소셜 센티먼트 대시보드

#### 5.1.1 대시보드 레이아웃
```python
# components/SentimentDashboard.py
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TrendingStock:
    symbol: str
    current_mentions: int
    trend_score: float
    sentiment_score: float
    top_communities: List[Dict[str, Any]]

@dataclass
class SentimentData:
    symbol: str
    overall_sentiment: float
    mention_count: int
    community_breakdown: Dict[str, Any]
    sentiment_trend: List[Dict[str, Any]]
    trending_status: bool

class SentimentDashboard:
    """소셜 센티먼트 대시보드 컴포넌트"""
    
    def __init__(self, component_id: str = "sentiment_dashboard"):
        self.component_id = component_id
    
    def render(self,
              trending_stocks: List[TrendingStock],
              sentiment_data: Optional[SentimentData] = None,
              timeframe: str = "24h") -> None:
        """소셜 센티먼트 대시보드 렌더링"""
        
        # 대시보드 스타일
        st.markdown("""
        <style>
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .trending-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .sentiment-positive {
            color: #10b981;
            font-weight: 600;
        }
        
        .sentiment-negative {
            color: #ef4444;
            font-weight: 600;
        }
        
        .sentiment-neutral {
            color: #6b7280;
            font-weight: 600;
        }
        
        .mention-count {
            font-size: 1.2em;
            font-weight: 700;
        }
        
        .trend-score {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.9em;
            margin-left: 8px;
        }
        
        .community-bar {
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }
        
        .community-segment {
            height: 100%;
            float: left;
        }
        
        .filter-tags {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }
        
        .filter-tag {
            padding: 6px 12px;
            border-radius: 16px;
            border: 1px solid #d1d5db;
            background: white;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s;
        }
        
        .filter-tag.active {
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
        }
        
        .filter-tag:hover {
            background: #f3f4f6;
        }
        
        .filter-tag.active:hover {
            background: #2563eb;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 대시보드 헤더
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown("### 🔥 소셜 센티먼트 대시보드")
        
        with col2:
            selected_timeframe = st.selectbox(
                "기간",
                ["1시간", "6시간", "24시간", "7일"],
                index=["1h", "6h", "24h", "7d"].index(timeframe),
                key="timeframe_selector"
            )
        
        with col3:
            if st.button("🔄 새로고침", key="refresh_sentiment"):
                st.rerun()
        
        # 필터 태그
        self._render_filter_tags()
        
        # 메인 콘텐츠
        col_trending, col_details = st.columns([1, 1])
        
        with col_trending:
            st.markdown("#### 🔥 트렌딩 주식")
            self._render_trending_stocks(trending_stocks)
        
        with col_details:
            if sentiment_data:
                st.markdown("#### 📊 상세 센티먼트 분석")
                self._render_sentiment_details(sentiment_data)
            else:
                st.markdown("#### 📊 상세 센티먼트 분석")
                st.info("주식을 선택하여 상세 센티먼트 정보를 확인하세요.")
    
    def _render_filter_tags(self):
        """필터 태그 렌더링"""
        filters = {
            "day_trading": "단타",
            "value_investing": "가치투자",
            "growth_investing": "성장투자",
            "crypto": "암호화폐"
        }
        
        # 필터 상태 관리
        if 'active_filters' not in st.session_state:
            st.session_state.active_filters = []
        
        # 필터 태그 HTML
        filter_html = '<div class="filter-tags">'
        for key, label in filters.items():
            is_active = key in st.session_state.active_filters
            active_class = "active" if is_active else ""
            
            filter_html += f'''
            <div class="filter-tag {active_class}"
                 onclick="toggleFilter('{key}')"
                 data-filter="{key}">
                {label}
            </div>
            '''
        filter_html += '</div>'
        
        st.markdown(filter_html, unsafe_allow_html=True)
        
        # Streamlit 버튼 (JavaScript 대체)
        cols = st.columns(len(filters))
        for i, (key, label) in enumerate(filters.items()):
            with cols[i]:
                is_active = key in st.session_state.active_filters
                if st.button(label, key=f"filter_{key}",
                           type="primary" if is_active else "secondary"):
                    if is_active:
                        st.session_state.active_filters.remove(key)
                    else:
                        st.session_state.active_filters.append(key)
                    st.rerun()
    
    def _render_trending_stocks(self, trending_stocks: List[TrendingStock]):
        """트렌딩 주식 렌더링"""
        
        for stock in trending_stocks[:10]:  # 상위 10개만 표시
            # 센티먼트 색상
            if stock.sentiment_score > 0.1:
                sentiment_color = "sentiment-positive"
                sentiment_emoji = "🟢"
            elif stock.sentiment_score < -0.1:
                sentiment_color = "sentiment-negative"
                sentiment_emoji = "🔴"
            else:
                sentiment_color = "sentiment-neutral"
                sentiment_emoji = "⚪"
            
            # 트렌딩 카드 HTML
            card_html = f"""
            <div class="trending-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 1.1em; font-weight: 600;">
                            {stock.symbol}
                            <span class="trend-score">🚀 +{stock.trend_score:.0f}%</span>
                        </div>
                        <div style="font-size: 0.9em; opacity: 0.9; margin-top: 4px;">
                            언급: <span class="mention-count">{stock.current_mentions:,}</span>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div class="{sentiment_color}">
                            {sentiment_emoji} {stock.sentiment_score:+.2f}
                        </div>
                        <div style="font-size: 0.8em; opacity: 0.8; margin-top: 4px;">
                            센티먼트
                        </div>
                    </div>
                </div>
            </div>
            """
            
            st.markdown(card_html, unsafe_allow_html=True)
            
            # 커뮤니티 바
            self._render_community_bar(stock.top_communities)
    
    def _render_community_bar(self, top_communities: List[Dict[str, Any]]):
        """커뮤니티 비중 바 렌더링"""
        
        if not top_communities:
            return
        
        # 전체 언급 수 계산
        total_mentions = sum(community['mentions'] for community in top_communities)
        
        if total_mentions == 0:
            return
        
        # 색상 팔레트
        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
        
        # 커뮤니티 바 HTML
        bar_html = '<div class="community-bar">'
        
        for i, community in enumerate(top_communities):
            if community['mentions'] > 0:
                width = (community['mentions'] / total_mentions) * 100
                color = colors[i % len(colors)]
                
                bar_html += f'''
                <div class="community-segment"
                     style="width: {width}%; background: {color};"
                     title="{community['name']}: {community['mentions']} ({width:.1f}%)">
                </div>
                '''
        
        bar_html += '</div>'
        
        st.markdown(bar_html, unsafe_allow_html=True)
        
        # 커뮤니티 레이블
        community_labels = []
        for community in top_communities[:3]:  # 상위 3개만 표시
            percentage = (community['mentions'] / total_mentions) * 100
            community_labels.append(f"{community['name']} {percentage:.1f}%")
        
        st.markdown(f"<small style='color: #64748b;'>{' • '.join(community_labels)}</small>",
                   unsafe_allow_html=True)
    
    def _render_sentiment_details(self, sentiment_data: SentimentData):
        """상세 센티먼트 분석 렌더링"""
        
        # 센티먼트 점수
        sentiment_color = "sentiment-positive" if sentiment_data.overall_sentiment > 0.1 else \
                         "sentiment-negative" if sentiment_data.overall_sentiment < -0.1 else \
                         "sentiment-neutral"
        
        sentiment_emoji = "🟢" if sentiment_data.overall_sentiment > 0.1 else \
                          "🔴" if sentiment_data.overall_sentiment < -0.1 else \
                          "⚪"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-size: 2em; font-weight: 700;" class="{sentiment_color}">
                {sentiment_emoji} {sentiment_data.overall_sentiment:+.2f}
            </div>
            <div style="color: #64748b;">전체 센티먼트 점수</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 언급 통계
        col_mentions, col_trending = st.columns(2)
        
        with col_mentions:
            st.metric(
                "언급 (24h)",
                f"{sentiment_data.mention_count:,}",
                delta="↑ 15%"  # 예시 데이터
            )
        
        with col_trending:
            st.metric(
                "트렌딩 상태",
                "🔥 활성" if sentiment_data.trending_status else "보통"
            )
        
        # 커뮤니티 분석
        st.markdown("##### 커뮤니티 분석")
        self._render_community_breakdown(sentiment_data.community_breakdown)
        
        # 센티먼트 추이
        if sentiment_data.sentiment_trend:
            st.markdown("##### 센티먼트 추이")
            self._render_sentiment_trend(sentiment_data.sentiment_trend)
    
    def _render_community_breakdown(self, community_breakdown: Dict[str, Any]):
        """커뮤니티 분석 렌더링"""
        
        for community, data in community_breakdown.items():
            # 커뮤니티 센티먼트
            sentiment = data.get('sentiment', 0)
            sentiment_color = "sentiment-positive" if sentiment > 0.1 else \
                             "sentiment-negative" if sentiment < -0.1 else \
                             "sentiment-neutral"
            
            mentions = data.get('mentions', 0)
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f1f5f9;">
                <div>
                    <div style="font-weight: 600;">{community}</div>
                    <div style="font-size: 0.9em; color: #64748b;">{mentions:,} 언급</div>
                </div>
                <div class="{sentiment_color}">
                    {sentiment:+.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    def _render_sentiment_trend(self, sentiment_trend: List[Dict[str, Any]]):
        """센티먼트 추이 차트 렌더링"""
        
        if not sentiment_trend:
            return
        
        # 데이터 준비
        timestamps = [item['timestamp'] for item in sentiment_trend]
        sentiment_scores = [item['sentiment'] for item in sentiment_trend]
        
        # 차트 생성
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=sentiment_scores,
            mode='lines+markers',
            name='센티먼트 점수',
            line=dict(color='#3b82f6', width=2),
            marker=dict(size=6)
        ))
        
        # 기준선 (0)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        # 레이아웃 업데이트
        fig.update_layout(
            title="시간별 센티먼트 변화",
            xaxis_title="시간",
            yaxis_title="센티먼트 점수",
            height=300,
            margin=dict(l=0, r=0, t=40, b=40),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
```

#### 5.1.2 차트 통합 뷰
```python
# components/ChartIntegration.py
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class ChartIntegration:
    """차트와 소셜 데이터 통합 컴포넌트"""
    
    def __init__(self, component_id: str = "chart_integration"):
        self.component_id = component_id
    
    def render(self,
              symbol: str,
              stock_data: pd.DataFrame,
              sentiment_data: List[Dict[str, Any]],
              mention_data: List[Dict[str, Any]]) -> None:
        """주식 차트에 소셜 데이터 오버레이"""
        
        if stock_data.empty:
            st.warning(f"{symbol}의 차트 데이터가 없습니다.")
            return
        
        # 서브플롯 생성
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=[
                f'{symbol} 주가 차트',
                '언급량',
                '센티먼트 점수'
            ],
            row_heights=[0.6, 0.2, 0.2]
        )
        
        # 1. 주가 차트
        fig.add_trace(go.Candlestick(
            x=stock_data.index,
            open=stock_data['Open'],
            high=stock_data['High'],
            low=stock_data['Low'],
            close=stock_data['Close'],
            name='주가',
            increasing_line_color='#26a69a',
            decreasing_line_color='#ef5350'
        ), row=1, col=1)
        
        # 2. 언급량 오버레이
        if mention_data:
            mention_df = pd.DataFrame(mention_data)
            mention_df['timestamp'] = pd.to_datetime(mention_df['timestamp'])
            
            fig.add_trace(go.Bar(
                x=mention_df['timestamp'],
                y=mention_df['count'],
                name='언급량',
                marker_color='rgba(59, 130, 246, 0.3)',
                yaxis='y2'
            ), row=1, col=1)
            
            # 두 번째 서브플롯에 언급량
            fig.add_trace(go.Bar(
                x=mention_df['timestamp'],
                y=mention_df['count'],
                name='언급량',
                marker_color='rgba(59, 130, 246, 0.8)',
                showlegend=False
            ), row=2, col=1)
        
        # 3. 센티먼트 점수
        if sentiment_data:
            sentiment_df = pd.DataFrame(sentiment_data)
            sentiment_df['timestamp'] = pd.to_datetime(sentiment_df['timestamp'])
            
            # 색상 매핑
            colors = ['green' if score > 0.1 else 'red' if score < -0.1 else 'gray'
                      for score in sentiment_df['sentiment']]
            
            fig.add_trace(go.Scatter(
                x=sentiment_df['timestamp'],
                y=sentiment_df['sentiment'],
                mode='lines+markers',
                name='센티먼트',
                line=dict(color='#8b5cf6', width=2),
                marker=dict(color=colors, size=6),
                showlegend=False
            ), row=3, col=1)
            
            # 기준선
            fig.add_hline(y=0, line_dash="dash", line_color="gray",
                         opacity=0.5, row=3, col=1)
        
        # 트렌딩 마커 추가
        self._add_trending_markers(fig, mention_data)
        
        # 레이아웃 업데이트
        fig.update_layout(
            height=800,
            showlegend=True,
            xaxis_rangeslider_visible=False,
            yaxis=dict(title='주가 ($)'),
            yaxis2=dict(title='언급량', overlaying='y', side='right'),
            yaxis3=dict(title='센티먼트 점수'),
            xaxis3=dict(title='날짜')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 상관관계 지표
        self._render_correlation_metrics(stock_data, sentiment_data, mention_data)
    
    def _add_trending_markers(self, fig, mention_data: List[Dict[str, Any]]):
        """언급량 급증 마커 추가"""
        
        if not mention_data:
            return
        
        # 언급량 급증 감지 (단순화된 로직)
        mention_df = pd.DataFrame(mention_data)
        mention_df['timestamp'] = pd.to_datetime(mention_df['timestamp'])
        
        # 이동 평균 계산
        mention_df['ma_7'] = mention_df['count'].rolling(window=7).mean()
        
        # 급증 지점 찾기 (현재 값이 7일 이동 평균의 2배 이상)
        spikes = mention_df[mention_df['count'] > 2 * mention_df['ma_7']]
        
        for _, spike in spikes.iterrows():
            fig.add_vline(
                x=spike['timestamp'],
                line_dash="dash",
                line_color="orange",
                annotation_text="🔥 트렌딩",
                annotation_position="top"
            )
    
    def _render_correlation_metrics(self,
                                   stock_data: pd.DataFrame,
                                   sentiment_data: List[Dict[str, Any]],
                                   mention_data: List[Dict[str, Any]]):
        """상관관계 지표 렌더링"""
        
        st.markdown("##### 📊 상관관계 분석")
        
        # 데이터 준비
        if not sentiment_data or not mention_data or stock_data.empty:
            st.info("상관관계 분석에 필요한 데이터가 부족합니다.")
            return
        
        # 데이터프레임 변환
        sentiment_df = pd.DataFrame(sentiment_data)
        sentiment_df['timestamp'] = pd.to_datetime(sentiment_df['timestamp'])
        
        mention_df = pd.DataFrame(mention_data)
        mention_df['timestamp'] = pd.to_datetime(mention_df['timestamp'])
        
        # 날짜 기준으로 데이터 병합
        sentiment_df['date'] = sentiment_df['timestamp'].dt.date
        mention_df['date'] = mention_df['timestamp'].dt.date
        stock_data['date'] = stock_data.index.date
        
        # 일별 데이터 집계
        sentiment_daily = sentiment_df.groupby('date')['sentiment'].mean().reset_index()
        mention_daily = mention_df.groupby('date')['count'].sum().reset_index()
        
        # 주가 일별 수익률 계산
        stock_daily = stock_data.groupby('date')['Close'].last().pct_change().reset_index()
        stock_daily.columns = ['date', 'return']
        
        # 데이터 병합
        merged_data = sentiment_daily.merge(mention_daily, on='date', how='inner')
        merged_data = merged_data.merge(stock_daily, on='date', how='inner')
        
        if len(merged_data) < 3:  # 최소 3일 데이터 필요
            st.info("상관관계 분석을 위한 데이터가 부족합니다.")
            return
        
        # 상관관계 계산
        sentiment_return_corr = merged_data['sentiment'].corr(merged_data['return'])
        mention_return_corr = merged_data['count'].corr(merged_data['return'])
        
        # 메트릭 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "센티먼트-수익률 상관계수",
                f"{sentiment_return_corr:.3f}",
                delta="양의 상관" if sentiment_return_corr > 0.1 else
                       "음의 상관" if sentiment_return_corr < -0.1 else "무상관"
            )
        
        with col2:
            st.metric(
                "언급량-수익률 상관계수",
                f"{mention_return_corr:.3f}",
                delta="양의 상관" if mention_return_corr > 0.1 else
                       "음의 상관" if mention_return_corr < -0.1 else "무상관"
            )
        
        # 상관관계 해석
        st.markdown("###### 상관관계 해석")
        
        if abs(sentiment_return_corr) > 0.5:
            st.success("센티먼트와 주가 움직임에 강한 상관관계가 있습니다.")
        elif abs(sentiment_return_corr) > 0.3:
            st.info("센티먼트와 주가 움직임에 중간 정도의 상관관계가 있습니다.")
        else:
            st.warning("센티먼트와 주가 움직임에 뚜렷한 상관관계가 없습니다.")
        
        if abs(mention_return_corr) > 0.5:
            st.success("언급량과 주가 움직임에 강한 상관관계가 있습니다.")
        elif abs(mention_return_corr) > 0.3:
            st.info("언급량과 주가 움직임에 중간 정도의 상관관계가 있습니다.")
        else:
            st.warning("언급량과 주가 움직임에 뚜렷한 상관관계가 없습니다.")
```

이 Enhanced Stock Search와 Social Sentiment Tracker UI/UX 디자인은 사용자 경험을 극대화하기 위해 다음과 같은 특징을 포함합니다:

1. **직관적인 검색 경험**: 실시간 자동완성, 관련도 기반 정렬, 시각적 피드백
2. **효율적인 정보 표시**: 카드 형태의 검색 결과, 중요 정보 강조, 빠른 액션 버튼
3. **개인화된 관심종목 관리**: 카테고리별 그룹화, 개인 메모, 시각적 구분
4. **포괄적인 센티먼트 시각화**: 다차원 데이터 표현, 커뮤니티 분석, 시간별 추이
5. **차트와 소셜 데이터 통합**: 오버레이 표시, 상관관계 분석, 트렌딩 마커

이러한 디자인 요소들은 사용자가 복잡한 금융 데이터를 쉽게 이해하고 효과적으로 활용할 수 있도록 지원합니다.

## 6. .kiro 스펙문서의 UI/UX 디자인 상세 내용

### 6.1 Enhanced Stock Search UI/UX 디자인 상세

#### 6.1.1 자동완성 엔진 디자인
- **관련도 점수 계산 방식**:
  - 심볼 정확 일치: 100점
  - 심볼 시작 일치: 80점
  - 회사명 시작 일치: 60점
  - 심볼 부분 일치: 40점
  - 회사명 부분 일치: 20점

- **Debouncing 전략**: 300ms 지연으로 불필요한 API 호출 방지
- **캐싱 전략**: 5분간 검색 결과 캐시로 성능 최적화
- **최대 제안 수**: 10개로 제한하여 사용자 선택 부담 감소

#### 6.1.2 검색 결과 시각화 개선
- **카드 디자인 요소**:
  - 심볼과 회사명 명확히 표시
  - 현재 가격과 일일 변동률 시각적 강조
  - 센티먼트 표시기 (녹색: 긍정, 빨간색: 부정, 회색: 중립)
  - 주식 유형, 거래소, 섹터 정보 포함
  - 빠른 액션 버튼 (차트 보기, 관심종목 추가)

- **정렬 전략**:
  - 관련도 점수 기반 기본 정렬
  - 사용자 선택 가능 정렬 옵션 (가격, 변동률, 시가총액)
  - 트렌딩 주식 우선 표시 옵션

#### 6.1.3 필터 시스템 디자인
- **다차원 필터링**:
  - 주식 유형 (EQUITY, ETF, MUTUALFUND, INDEX)
  - 섹터별 필터링 (Technology, Healthcare, Finance 등)
  - 거래소별 필터링 (NYSE, NASDAQ, AMEX 등)
  - 시가총액 범위 필터링
  - 가격 범위 필터링

- **필터 UI/UX**:
  - 빠른 필터 태그로 자주 사용하는 필터 즉시 접근
  - 고급 필터 패널에서 상세 필터링 옵션 제공
  - 적용된 필터 시각적 표시 및 쉽게 제거 기능
  - 필터 조합 저장 및 재사용 기능

#### 6.1.4 검색 히스토리 관리
- **데이터 구조**:
  ```python
  @dataclass
  class SearchHistoryItem:
      symbol: str
      company_name: str
      search_time: datetime
      search_count: int
  ```

- **UI/UX 특징**:
  - 최대 20개 검색 기록 유지
  - 중복 제거 및 최신 검색 시간 기준 정렬
  - 검색 빈도에 따른 인기 검색어 강조
  - 검색 기록에서 바로 주식 선택 가능
  - 검색 기록 선택적 삭제 기능

#### 6.1.5 향상된 관심종목 관리
- **데이터 구조**:
  ```python
  @dataclass
  class WatchlistItem:
      symbol: str
      company_name: str
      category: str
      note: str
      added_date: datetime
      order_index: int
  ```

- **UI/UX 특징**:
  - 카테고리별 그룹화 (Tech Stocks, Finance, etc.)
  - 개인 메모 추가 기능
  - 드래그 앤 드롭 순서 변경 (Streamlit 한계로 버튼 기반 구현)
  - 관심종목 실시간 가격 업데이트
  - 관심종목별 센티먼트 상태 표시
  - 일괄 작업 기능 (다중 선택, 카테고리 변경 등)

### 6.2 Social Sentiment Tracker UI/UX 디자인 상세

#### 6.2.1 소셜 센티먼트 대시보드
- **레이아웃 구조**:
  ```
  ┌─────────────────────────────────────────────────────────┐
  │ 🔥 Trending Now        📊 Top Mentions    ⚙️ Filters    │
  ├─────────────────────────────────────────────────────────┤
  │ TSLA  🚀 +450%        AAPL    1,247      ☑️ Day Trading │
  │ GME   📈 +320%        TSLA    1,156      ☑️ Value       │
  │ AMC   🌙 +280%        NVDA      892      ☐ Growth       │
  └─────────────────────────────────────────────────────────┘
  ```

- **트렌딩 감지 알고리즘**:
  - 베이스라인 계산: 지난 7일 평균 언급량
  - 급증 감지: 현재 언급량이 베이스라인의 200% 이상
  - 지속성 확인: 최소 30분간 높은 언급량 유지
  - 노이즈 필터링: 봇 계정 및 스팸 제거

- **시각적 요소**:
  - 트렌딩 주식 그라데이션 카드 디자인
  - 센티먼트 색상 코딩 (녹색: 긍정, 빨간색: 부정, 회색: 중립)
  - 언급량 시각적 막대 그래프
  - 커뮤니티 비중 시각적 표시
  - 트렌딩 시작 시간과 증가율 표시

#### 6.2.2 커뮤니티 필터링 시스템
- **커뮤니티 분류**:
  - 단타: wallstreetbets, daytrading, pennystocks
  - 가치투자: SecurityAnalysis, ValueInvesting, investing
  - 성장투자: stocks, StockMarket, investing
  - 암호화폐: cryptocurrency, CryptoMarkets, Bitcoin

- **필터 UI/UX**:
  - 투자 성향별 필터 태그
  - 여러 필터 동시 선택 지원
  - 커뮤니티별 언급 비중 시각적 표시
  - 필터 적용 결과 실시간 업데이트

#### 6.2.3 센티먼트 분석 시각화
- **센티먼트 점수 체계**:
  - -100에서 +100 범위의 점수 체계
  - VADER Sentiment 기반 분석
  - 주식 커뮤니티 특화 어휘 ("moon", "diamond hands", "paper hands" 등)
  - 색상으로 시각화 (녹색: 긍정, 빨간색: 부정)

- **상세 분석 뷰**:
  ```
  ┌─────────────────────────────────────────────────────────┐
  │ AAPL - Apple Inc.                                       │
  ├─────────────────────────────────────────────────────────┤
  │ Sentiment Score: +65 🟢                                 │
  │ Mentions (24h): 1,247 (↑15%)                          │
  │                                                         │
  │ Community Breakdown:                                    │
  │ ████████░░ r/investing (40%)                           │
  │ ██████░░░░ r/stocks (30%)                              │
  │ ████░░░░░░ Twitter (20%)                               │
  │ ██░░░░░░░░ r/wallstreetbets (10%)                      │
  │                                                         │
  │ [View Chart Integration] [Add to Watchlist]            │
  └─────────────────────────────────────────────────────────┘
  ```

#### 6.2.4 차트 통합 시각화
- **오버레이 요소**:
  - 주식 차트 위에 언급량 데이터 오버레이
  - 감정 점수 변화 별도 서브플롯 표시
  - 언급량 급증 시점 마커 표시
  - 소셜 데이터와 주가 데이터의 상관관계 지표

- **상관관계 분석**:
  - 센티먼트-수익률 상관계수 계산 및 표시
  - 언급량-수익률 상관계수 계산 및 표시
  - 상관관계 해석 및 인사이트 제공

### 6.3 통합 시스템 UI/UX 고려사항

#### 6.3.1 검색 결과와 센티먼트 통합
- **통합 검색 결과 카드**:
  - 기본 주식 정보와 함께 센티먼트 표시기
  - 언급량 급증 시 특별 마커 표시
  - 커뮤니티별 언급 비중 간략 표시
  - 센티먼트 상세 분석 빠른 접근 버튼

#### 6.3.2 관심종목과 센티먼트 통합
- **관심종목 센티먼트 상태**:
  - 관심종목 목록에 실시간 센티먼트 표시
  - 센티먼트 급변 시 알림 기능
  - 관심종목별 커뮤니티 언급 비중 표시

#### 6.3.3 차트와 소셜 데이터 통합
- **다차원 차트 뷰**:
  - 주가 차트와 언급량 오버레이
  - 센티먼트 점수 서브플롯
  - 트렌딩 마커와 상관관계 지표
  - 특정 시점 선택 시 관련 언급 내용 표시

### 6.4 성능 및 사용자 경험 최적화

#### 6.4.1 로딩 상태 관리
- **스켈레톤 로딩**: 데이터 로딩 시 콘텐츠 구조 시각적 표시
- **점진적 로딩**: 중요 데이터부터 순차적으로 로드
- **로딩 상태 표시**: 명확한 진행률 표시 및 예상 시간 안내

#### 6.4.2 오류 처리 및 복구
- **네트워크 오류**: 재시도 메커니즘 및 오프라인 모드
- **데이터 부족**: 적절한 대체 데이터 및 안내 메시지
- **API 제한**: 사용자에게 명확한 제한 정보 표시

#### 6.4.3 반응형 디자인
- **모바일 최적화**: 터치 최적화 인터페이스
- **태블릿 지원**: 중간 화면 크기에 최적화된 레이아웃
- **데스크톱 경험**: 다중 창 및 고해상도 지원

이러한 상세 UI/UX 디자인 가이드라인은 .kiro 스펙문서의 구체적인 구현 내용을 바탕으로 사용자 경험을 극대화하기 위한 포괄적인 접근 방식을 제공합니다.