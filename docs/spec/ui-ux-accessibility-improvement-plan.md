# UI/UX 접근성 개선 계획

## 1. 개요

본 문서는 주식 차트 분석 애플리케이션의 UI/UX 접근성을 향상시키기 위한 상세한 계획을 제시합니다. WCAG 2.1 AA 준수, 반응형 디자인, 키보드 내비게이션, 스크린 리더 지원, 다국어 지원 등 다양한 접근성 측면에서의 개선 전략을 다룹니다.

## 2. 접근성 아키텍처

### 2.1 접근성 계층 모델

```
┌─────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Visual       │  │   Auditory      │  │   Motor      │ │
│  │   Accessibility │  │   Accessibility │  │   Accessibility │ │
│  │   - Color       │  │   - Screen      │  │   - Voice      │ │
│  │   - Typography   │  │     Reader      │  │   Control     │ │
│  │   - Layout       │  │   - Audio Alerts │  │   - Switch     │ │
│  │   - Spacing      │  │   - Text to      │  │   - Navigation │ │
│  │   - Contrast     │  │     Speech      │  │   - Physical    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│                    Interaction Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Keyboard      │  │   Touch         │  │   Voice       │ │
│  │   Navigation    │  │   Gestures       │  │   Commands    │ │
│  │   - Tab Order    │  │   - Swipe        │  │   - Dictation   │ │
│  │   - Focus        │  │   - Tap          │  │   - Control    │ │
│  │   - Shortcuts    │  │   - Pinch        │  │   - Navigation │ │
│  │   - Skip Links   │  │   - Drag         │  │   - Confirmation│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│                    Content Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Text          │  │   Media         │  │   Structure   │ │
│  │   - Alt Text     │  │   - Captions     │  │   - Headings    │ │
│  │   - Descriptions │  │   - Transcripts  │  │   - Lists       │ │
│  │   - Language     │  │   - Audio Desc    │  │   - Tables      │ │
│  │   - Readability   │  │   - Sign Language │  │   - Landmarks   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2.2 WCAG 2.1 AA 준수 체크리스트

```typescript
// accessibility/wcag-checklist.ts
export interface WCAGGuideline {
  principle: string;
  guideline: string;
  criteria: string;
  level: 'A' | 'AA' | 'AAA';
  description: string;
  implementation: string[];
  testable: boolean;
}

export const WCAG21AA_Checklist: WCAGGuideline[] = [
  // Perceivable
  {
    principle: "Perceivable",
    guideline: "1.1 Non-text Content",
    criteria: "1.1.1",
    level: "AA",
    description: "All non-text content has a text alternative",
    implementation: [
      "Add alt text to all images",
      "Provide captions for videos",
      "Include audio descriptions for complex visual content",
      "Use ARIA labels for interactive elements"
    ],
    testable: true
  },
  {
    principle: "Perceivable",
    guideline: "1.2 Time-based Media",
    criteria: "1.2.2",
    level: "AA",
    description: "Captions are provided for all prerecorded audio content",
    implementation: [
      "Add synchronized captions to videos",
      "Provide transcripts for audio content",
      "Ensure captions are accurate and synchronized",
      "Include speaker identification"
    ],
    testable: true
  },
  {
    principle: "Perceivable",
    guideline: "1.3 Adaptable",
    criteria: "1.3.1",
    level: "AA",
    description: "Information and structure can be programmatically determined",
    implementation: [
      "Use semantic HTML elements",
      "Implement proper heading hierarchy",
      "Use ARIA landmarks",
      "Ensure content is accessible via screen readers"
    ],
    testable: true
  },
  {
    principle: "Perceivable",
    guideline: "1.4 Distinguishable",
    criteria: "1.4.3",
    level: "AA",
    description: "Color is not used as the only visual means of conveying information",
    implementation: [
      "Ensure text contrast ratio of at least 4.5:1",
      "Use icons with text labels",
      "Don't rely on color alone for meaning",
      "Provide visual indicators beyond color"
    ],
    testable: true
  },
  
  // Operable
  {
    principle: "Operable",
    guideline: "2.1 Keyboard Accessible",
    criteria: "2.1.1",
    level: "AA",
    description: "All functionality is available from a keyboard",
    implementation: [
      "Ensure all interactive elements are keyboard accessible",
      "Implement proper tab order",
      "Provide keyboard shortcuts",
      "Ensure focus is visible"
    ],
    testable: true
  },
  {
    principle: "Operable",
    guideline: "2.2 Enough Time",
    criteria: "2.2.1",
    level: "AA",
    description: "Users have enough time to read and use content",
    implementation: [
      "Remove or allow users to dismiss time limits",
      "Provide warnings before auto-save",
      "Allow users to extend time limits",
      "Don't use auto-refresh without warning"
    ],
    testable: true
  },
  {
    principle: "Operable",
    guideline: "2.3 Seizures",
    criteria: "2.3.1",
    level: "AA",
    description: "Web pages do not contain anything that flashes more than 3 times per second",
    implementation: [
      "Avoid flashing content above 3Hz",
      "Provide controls to stop animations",
      "Implement reduced motion preferences",
      "Test with flash detection tools"
    ],
    testable: true
  },
  {
    principle: "Operable",
    guideline: "2.4 Navigable",
    criteria: "2.4.1",
    level: "AA",
    description: "Users can navigate, find content, and determine where they are",
    implementation: [
      "Implement proper heading structure",
      "Use skip links",
      "Provide clear navigation",
      "Include page titles and breadcrumbs"
    ],
    testable: true
  },
  
  // Understandable
  {
    principle: "Understandable",
    guideline: "3.1 Readable",
    criteria: "3.1.1",
    level: "AA",
    description: "Text content is readable and understandable",
    implementation: [
      "Use clear and simple language",
      "Define technical terms",
      "Use consistent terminology",
      "Provide text alternatives for symbols"
    ],
    testable: true
  },
  {
    principle: "Understandable",
    guideline: "3.2 Predictable",
    criteria: "3.2.1",
    level: "AA",
    description: "Web pages appear and operate in predictable ways",
    implementation: [
      "Use consistent navigation patterns",
      "Follow common UI conventions",
      "Provide clear feedback for actions",
      "Ensure consistent element behavior"
    ],
    testable: true
  },
  {
    principle: "Understandable",
    guideline: "3.3 Input Assistance",
    criteria: "3.3.1",
    level: "AA",
    description: "Users are helped to avoid and correct mistakes",
    implementation: [
      "Provide clear error messages",
      "Implement input validation",
      "Offer suggestions for corrections",
      "Provide confirmation for destructive actions"
    ],
    testable: true
  },
  
  // Robust
  {
    principle: "Robust",
    guideline: "4.1 Compatible",
    criteria: "4.1.1",
    level: "AA",
    description: "Content is compatible with assistive technologies",
    implementation: [
      "Use semantic HTML",
      "Test with screen readers",
      "Ensure ARIA compatibility",
      "Validate HTML structure"
    ],
    testable: true
  }
];
```

## 3. 키보드 내비게이션 구현

### 3.1 키보드 내비게이션 컴포넌트
```typescript
// components/accessible/KeyboardNavigation.tsx
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface FocusTrapProps {
  children: React.ReactNode;
  isActive: boolean;
  onEscape?: () => void;
}

export const FocusTrap: React.FC<FocusTrapProps> = ({ 
  children, 
  isActive, 
  onEscape 
}) => {
  const containerRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive) return;

    const container = containerRef.current;
    if (!container) return;

    // Store current focus
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Focus first focusable element
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length > 0) {
      (focusableElements[0] as HTMLElement).focus();
    }

    // Handle tab navigation
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        event.preventDefault();
        
        const focusableElements = Array.from(
          container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
        ) as HTMLElement[];
        
        const currentIndex = focusableElements.indexOf(
          document.activeElement as HTMLElement
        );
        
        let nextIndex;
        if (event.shiftKey) {
          // Shift + Tab: go to previous
          nextIndex = currentIndex <= 0 
            ? focusableElements.length - 1 
            : currentIndex - 1;
        } else {
          // Tab: go to next
          nextIndex = currentIndex >= focusableElements.length - 1 
            ? 0 
            : currentIndex + 1;
        }
        
        focusableElements[nextIndex]?.focus();
      } else if (event.key === 'Escape' && onEscape) {
        onEscape();
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      
      // Restore focus when trap is deactivated
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isActive, onEscape]);

  return (
    <div 
      ref={containerRef}
      role="dialog"
      aria-modal={isActive}
      tabIndex={isActive ? -1 : undefined}
    >
      {children}
    </div>
  );
};

interface SkipLinkProps {
  href: string;
  children: React.ReactNode;
}

export const SkipLink: React.FC<SkipLinkProps> = ({ href, children }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(false), 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <a
      href={href}
      className={`skip-link ${isVisible ? 'visible' : ''}`}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}
    </a>
  );
};

// SkipLinks component for main navigation
export const SkipLinks: React.FC = () => {
  return (
    <>
      <SkipLink href="#main-content">
        Skip to main content
      </SkipLink>
      <SkipLink href="#navigation">
        Skip to navigation
      </SkipLink>
      <SkipLink href="#search">
        Skip to search
      </SkipLink>
    </>
  );
};
```

### 3.2 키보드 단축키 시스템
```typescript
// hooks/useKeyboardShortcuts.ts
import { useEffect, useCallback } from 'react';

interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  action: () => void;
  description: string;
}

export const useKeyboardShortcuts = (shortcuts: KeyboardShortcut[]) => {
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    for (const shortcut of shortcuts) {
      const {
        key,
        ctrlKey = false,
        shiftKey = false,
        altKey = false,
        action
      } = shortcut;

      if (
        event.key === key &&
        event.ctrlKey === ctrlKey &&
        event.shiftKey === shiftKey &&
        event.altKey === altKey
      ) {
        event.preventDefault();
        event.stopPropagation();
        action();
        break;
      }
    }
  }, [shortcuts]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
};

// Usage in component
export const KeyboardShortcutsHelp: React.FC = () => {
  const shortcuts: KeyboardShortcut[] = [
    {
      key: 'k',
      action: () => document.getElementById('stock-search')?.focus(),
      description: 'Focus search'
    },
    {
      key: '/',
      ctrlKey: true,
      action: () => document.getElementById('help')?.click(),
      description: 'Open help'
    },
    {
      key: 'n',
      action: () => {
        const nextStock = document.querySelector('[data-next-stock]');
        nextStock?.click();
      },
      description: 'Next stock'
    },
    {
      key: 'p',
      action: () => {
        const prevStock = document.querySelector('[data-prev-stock]');
        prevStock?.click();
      },
      description: 'Previous stock'
    },
    {
      key: 't',
      action: () => {
        const timeframe1d = document.querySelector('[data-timeframe="1d"]');
        timeframe1d?.click();
      },
      description: '1 day timeframe'
    }
  ];

  useKeyboardShortcuts(shortcuts);

  return (
    <div className="keyboard-shortcuts-help">
      <h3>Keyboard Shortcuts</h3>
      <ul>
        {shortcuts.map((shortcut, index) => (
          <li key={index}>
            <kbd>
              {shortcut.ctrlKey && <span>Ctrl+</span>}
              {shortcut.shiftKey && <span>Shift+</span>}
              {shortcut.altKey && <span>Alt+</span>}
              {shortcut.key}
            </kbd>
            <span>{shortcut.description}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
```

## 4. 스크린 리더 지원 구현

### 4.1 ARIA 레이블 및 랜드마크
```typescript
// components/accessible/StockChart.tsx
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface StockChartProps {
  data: any[];
  title: string;
  symbol: string;
}

export const AccessibleStockChart: React.FC<StockChartProps> = ({ data, title, symbol }) => {
  const [chartDescription, setChartDescription] = useState('');

  useEffect(() => {
    // Generate dynamic description for screen readers
    if (data.length > 0) {
      const latestPrice = data[data.length - 1].close;
      const priceChange = data[data.length - 1].close - data[0].close;
      const priceChangePercent = (priceChange / data[0].close) * 100;
      
      setChartDescription(
        `${symbol} stock chart showing ${data.length} data points. ` +
        `Current price: $${latestPrice.toFixed(2)}. ` +
        `Change: ${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)} ` +
        `(${priceChangePercent.toFixed(2)}%). ` +
        `Use arrow keys to navigate data points.`
      );
    }
  }, [data, symbol]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="custom-tooltip" role="tooltip">
          <div className="tooltip-header">
            <span className="tooltip-date">{payload[0].payload.date}</span>
            <span className="tooltip-symbol">{symbol}</span>
          </div>
          <div className="tooltip-content">
            <div>Open: ${payload[0].payload.open}</div>
            <div>High: ${payload[0].payload.high}</div>
            <div>Low: ${payload[0].payload.low}</div>
            <div>Close: ${payload[0].payload.close}</div>
            <div>Volume: {payload[0].payload.volume.toLocaleString()}</div>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="accessible-chart" role="img" aria-label={chartDescription}>
      <h2 id={`chart-title-${symbol}`} className="chart-title">
        {title}
      </h2>
      
      <div className="chart-controls" aria-label="Chart controls">
        <button
          aria-label="Previous data point"
          onClick={() => {/* Navigate to previous point */}}
          aria-controls={`chart-${symbol}`}
        >
          ← Previous
        </button>
        <button
          aria-label="Next data point"
          onClick={() => {/* Navigate to next point */}}
          aria-controls={`chart-${symbol}`}
        >
          Next →
        </button>
        <button
          aria-label="Toggle chart type"
          onClick={() => {/* Toggle chart type */}}
          aria-controls={`chart-${symbol}`}
        >
          Toggle Type
        </button>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <LineChart
          id={`chart-${symbol}`}
          data={data}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          aria-label={`${symbol} stock price chart`}
          aria-describedby={`chart-title-${symbol}`}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis 
            dataKey="date" 
            stroke="#666"
            tickFormatter={(value) => new Date(value).toLocaleDateString()}
          />
          <YAxis 
            stroke="#666"
            tickFormatter={(value) => `$${value.toFixed(2)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#8884d8"
            strokeWidth={2}
            dot={{ fill: '#8884d8', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6 }}
            aria-label={`Stock price for ${symbol}`}
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="chart-summary" aria-live="polite" aria-atomic="true">
        <h3>Chart Summary</h3>
        <p>Current price: ${data[data.length - 1]?.close}</p>
        <p>Period: {data[0]?.date} to {data[data.length - 1]?.date}</p>
      </div>
    </div>
  );
};
```

### 4.2 라이브 지역 및 동적 콘텐츠
```typescript
// components/accessible/LiveRegion.tsx
import React, { useState, useEffect } from 'react';

interface LiveRegionProps {
  children: React.ReactNode;
  ariaLive?: 'polite' | 'assertive' | 'off';
  ariaAtomic?: boolean;
  id?: string;
}

export const LiveRegion: React.FC<LiveRegionProps> = ({ 
  children, 
  ariaLive = 'polite', 
  ariaAtomic = true,
  id 
}) => {
  const [announcement, setAnnouncement] = useState('');

  const announce = (message: string) => {
    setAnnouncement(message);
    setTimeout(() => setAnnouncement(''), 1000);
  };

  return (
    <div
      id={id}
      aria-live={ariaLive}
      aria-atomic={ariaAtomic}
      className="live-region"
      aria-label="Live updates"
    >
      {announcement && (
        <div className="sr-only" role="status">
          {announcement}
        </div>
      )}
      {children}
    </div>
  );
};

// Usage for stock price updates
export const StockPriceAnnouncer: React.FC<{ symbol: string; price: number; change: number }> = ({ 
  symbol, 
  price, 
  change 
}) => {
  const [lastPrice, setLastPrice] = useState(price);

  useEffect(() => {
    if (lastPrice !== price) {
      const changeDirection = change >= 0 ? 'increased' : 'decreased';
      const changeAmount = Math.abs(change).toFixed(2);
      
      const announcement = `${symbol} stock price ${changeDirection} by $${changeAmount} to $${price.toFixed(2)}`;
      
      // This will be announced by the LiveRegion component
      setLastPrice(price);
    }
  }, [symbol, price, change, lastPrice]);

  return null; // Component only manages announcements
};

// Screen reader only component
export const ScreenReaderOnly: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="sr-only" aria-live="polite">
      {children}
    </div>
  );
};
```

## 5. 반응형 디자인 구현

### 5.1 모바일 최적화 레이아웃
```typescript
// hooks/useResponsive.ts
import { useState, useEffect } from 'react';

interface Breakpoints {
  mobile: number;
  tablet: number;
  desktop: number;
  largeDesktop: number;
}

const breakpoints: Breakpoints = {
  mobile: 320,
  tablet: 768,
  desktop: 1024,
  largeDesktop: 1440
};

export const useResponsive = () => {
  const [windowSize, setWindowSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight
  });

  const [isMobile, setIsMobile] = useState(
    window.innerWidth < breakpoints.tablet
  );
  const [isTablet, setIsTablet] = useState(
    window.innerWidth >= breakpoints.tablet && window.innerWidth < breakpoints.desktop
  );
  const [isDesktop, setIsDesktop] = useState(
    window.innerWidth >= breakpoints.desktop
  );

  useEffect(() => {
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight
      });
      
      setIsMobile(window.innerWidth < breakpoints.tablet);
      setIsTablet(
        window.innerWidth >= breakpoints.tablet && window.innerWidth < breakpoints.desktop
      );
      setIsDesktop(window.innerWidth >= breakpoints.desktop);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    windowSize,
    isMobile,
    isTablet,
    isDesktop,
    isSmallScreen: windowSize.width < 480,
    isMediumScreen: windowSize.width >= 480 && windowSize.width < 768,
    isLargeScreen: windowSize.width >= 768
  };
};

// Responsive layout component
interface ResponsiveLayoutProps {
  children: React.ReactNode;
}

export const ResponsiveLayout: React.FC<ResponsiveLayoutProps> = ({ children }) => {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  if (isMobile) {
    return (
      <div className="mobile-layout">
        <header className="mobile-header">
          <SkipLinks />
          <button className="mobile-menu-toggle" aria-label="Toggle menu">
            ☰
          </button>
        </header>
        <nav className="mobile-navigation" role="navigation" aria-label="Main navigation">
          {children}
        </nav>
        <main className="mobile-main" id="main-content">
          {children}
        </main>
      </div>
    );
  }

  if (isTablet) {
    return (
      <div className="tablet-layout">
        <header className="tablet-header">
          <SkipLinks />
          <nav className="tablet-navigation" role="navigation" aria-label="Main navigation">
            {children}
          </nav>
        </header>
        <aside className="tablet-sidebar" role="complementary" aria-label="Additional information">
          {children}
        </aside>
        <main className="tablet-main" id="main-content">
          {children}
        </main>
      </div>
    );
  }

  return (
    <div className="desktop-layout">
      <header className="desktop-header">
        <SkipLinks />
        <nav className="desktop-navigation" role="navigation" aria-label="Main navigation">
          {children}
        </nav>
      </header>
      <aside className="desktop-sidebar" role="complementary" aria-label="Additional information">
        {children}
      </aside>
      <main className="desktop-main" id="main-content">
        {children}
      </main>
    </div>
  );
};
```

### 5.2 유동 타입그래피 및 터치 최적화
```typescript
// hooks/useTouchGestures.ts
import { useRef, useEffect, useCallback } from 'react';

interface TouchGesture {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
  onPinch?: (scale: number) => void;
}

export const useTouchGestures = (elementRef: React.RefObject<HTMLElement>, gestures: TouchGesture) => {
  const startX = useRef<number>(0);
  const startY = useRef<number>(0);
  const endX = useRef<number>(0);
  const endY = useRef<number>(0);
  const initialDistance = useRef<number>(0);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    if (e.touches.length === 1) {
      startX.current = e.touches[0].clientX;
      startY.current = e.touches[0].clientY;
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      initialDistance.current = Math.sqrt(dx * dx + dy * dy);
    }
  }, []);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    e.preventDefault();
  }, []);

  const handleTouchEnd = useCallback((e: TouchEvent) => {
    if (e.changedTouches.length === 1) {
      endX.current = e.changedTouches[0].clientX;
      endY.current = e.changedTouches[0].clientY;

      const deltaX = endX.current - startX.current;
      const deltaY = endY.current - startY.current;

      // Detect swipe gestures
      if (Math.abs(deltaX) > 50) {
        if (deltaX > 0 && gestures.onSwipeRight) {
          gestures.onSwipeRight();
        } else if (deltaX < 0 && gestures.onSwipeLeft) {
          gestures.onSwipeLeft();
        }
      }

      if (Math.abs(deltaY) > 50) {
        if (deltaY > 0 && gestures.onSwipeDown) {
          gestures.onSwipeDown();
        } else if (deltaY < 0 && gestures.onSwipeUp) {
          gestures.onSwipeUp();
        }
      }
    }
  }, [gestures]);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    element.addEventListener('touchstart', handleTouchStart);
    element.addEventListener('touchmove', handleTouchMove);
    element.addEventListener('touchend', handleTouchEnd);

    return () => {
      element.removeEventListener('touchstart', handleTouchStart);
      element.removeEventListener('touchmove', handleTouchMove);
      element.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd]);
};

// Touch-friendly chart component
interface TouchableChartProps {
  data: any[];
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
}

export const TouchableChart: React.FC<TouchableChartProps> = ({ data, onSwipeLeft, onSwipeRight }) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useTouchGestures(chartRef, {
    onSwipeLeft,
    onSwipeRight
  });

  return (
    <div 
      ref={chartRef}
      className="touchable-chart"
      role="img"
      aria-label="Stock chart. Swipe left or right to change time period."
      tabIndex={0}
    >
      {/* Chart implementation */}
      <div className="chart-content">
        {/* Chart rendering logic */}
      </div>
      
      <div className="touch-indicators">
        <div className="swipe-indicator left" aria-hidden="true">
          ← Swipe left
        </div>
        <div className="swipe-indicator right" aria-hidden="true">
          Swipe right →
        </div>
      </div>
    </div>
  );
};
```

## 6. 색상 대비 및 테마 시스템

### 6.1 색상 대비 테마 구현
```css
/* styles/themes.css */

:root {
  /* Light theme (default) */
  --primary-color: #1976d2;
  --secondary-color: #dc004e;
  --background-color: #ffffff;
  --text-color: #333333;
  --border-color: #e0e0e0;
  --shadow-color: rgba(0, 0, 0, 0.1);
  --chart-line-color: #1976d2;
  --chart-grid-color: #f0f0f0;
  --success-color: #4caf50;
  --warning-color: #ff9800;
  --error-color: #f44336;
  
  /* High contrast colors */
  --high-contrast-primary: #0000ff;
  --high-contrast-background: #ffffff;
  --high-contrast-text: #000000;
}

[data-theme="dark"] {
  --primary-color: #90caf9;
  --secondary-color: #ff9800;
  --background-color: #121212;
  --text-color: #ffffff;
  --border-color: #333333;
  --shadow-color: rgba(0, 0, 0, 0.3);
  --chart-line-color: #90caf9;
  --chart-grid-color: #333333;
  --success-color: #4caf50;
  --warning-color: #ff9800;
  --error-color: #f44336;
}

[data-theme="high-contrast"] {
  --primary-color: var(--high-contrast-primary);
  --background-color: var(--high-contrast-background);
  --text-color: var(--high-contrast-text);
  --border-color: #000000;
  --shadow-color: rgba(0, 0, 0, 0.5);
  --chart-line-color: #0000ff;
  --chart-grid-color: #808080;
}

/* Ensure sufficient contrast ratios */
.text-content {
  color: var(--text-color);
  background-color: var(--background-color);
}

.button-primary {
  background-color: var(--primary-color);
  color: white;
  border: 1px solid var(--primary-color);
}

.button-primary:hover,
.button-primary:focus {
  opacity: 0.8;
  outline: 2px solid var(--text-color);
  outline-offset: 2px;
}

/* Focus indicators */
.focusable:focus {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* High contrast mode specific styles */
[data-theme="high-contrast"] .focusable:focus {
  outline: 3px solid #000000;
  outline-offset: 2px;
  background-color: #ffff00;
}

/* Dark mode specific adjustments */
[data-theme="dark"] .chart-container {
  background-color: var(--background-color);
  border: 1px solid var(--border-color);
}

[data-theme="dark"] .tooltip {
  background-color: #333333;
  color: #ffffff;
  border: 1px solid #555555;
}
```

### 6.2 테마 전환 컴포넌트
```typescript
// components/accessible/ThemeToggle.tsx
import React, { useState, useEffect } from 'react';

type Theme = 'light' | 'dark' | 'high-contrast';

interface ThemeToggleProps {
  initialTheme?: Theme;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ initialTheme = 'light' }) => {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    // Load saved theme preference
    const savedTheme = localStorage.getItem('theme') as Theme;
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    }
  }, []);

  useEffect(() => {
    // Save theme preference
    localStorage.setItem('theme', theme);
    applyTheme(theme);
  }, [theme]);

  const applyTheme = (newTheme: Theme) => {
    document.documentElement.setAttribute('data-theme', newTheme);
    
    // Update meta theme-color for mobile browsers
    const themeColors = {
      light: '#1976d2',
      dark: '#121212',
      'high-contrast': '#000000'
    };
    
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute('content', themeColors[newTheme]);
    }
  };

  const toggleTheme = () => {
    setTheme(prevTheme => {
      if (prevTheme === 'light') return 'dark';
      if (prevTheme === 'dark') return 'high-contrast';
      return 'light';
    });
  };

  return (
    <div className="theme-toggle">
      <button
        onClick={toggleTheme}
        className="theme-toggle-button"
        aria-label={`Current theme: ${theme}. Click to cycle through themes.`}
        aria-pressed={false}
      >
        <span className="theme-icon" aria-hidden="true">
          {theme === 'light' && '☀️'}
          {theme === 'dark' && '🌙'}
          {theme === 'high-contrast' && '🔆'}
        </span>
        <span className="theme-label">
          {theme === 'light' && 'Light'}
          {theme === 'dark' && 'Dark'}
          {theme === 'high-contrast' && 'High Contrast'}
        </span>
      </button>
      
      <div className="theme-options" role="menu">
        <button
          onClick={() => setTheme('light')}
          className={`theme-option ${theme === 'light' ? 'active' : ''}`}
          aria-pressed={theme === 'light'}
          aria-label="Switch to light theme"
        >
          Light
        </button>
        <button
          onClick={() => setTheme('dark')}
          className={`theme-option ${theme === 'dark' ? 'active' : ''}`}
          aria-pressed={theme === 'dark'}
          aria-label="Switch to dark theme"
        >
          Dark
        </button>
        <button
          onClick={() => setTheme('high-contrast')}
          className={`theme-option ${theme === 'high-contrast' ? 'active' : ''}`}
          aria-pressed={theme === 'high-contrast'}
          aria-label="Switch to high contrast theme"
        >
          High Contrast
        </button>
      </div>
    </div>
  );
};
```

## 7. 다국어 지원 (i18n) 구현

### 7.1 국제화 시스템
```typescript
// i18n/index.ts
export const languages = [
  {
    code: 'en',
    name: 'English',
    rtl: false
  },
  {
    code: 'ko',
    name: '한국어',
    rtl: false
  },
  {
    code: 'ja',
    name: '日本語',
    rtl: false
  },
  {
    code: 'zh',
    name: '中文',
    rtl: false
  },
  {
    code: 'es',
    name: 'Español',
    rtl: false
  },
  {
    code: 'ar',
    name: 'العربية',
    rtl: true
  }
];

export const defaultLanguage = 'en';

// i18n/hooks/useTranslation.ts
import { useState, useEffect } from 'react';

interface Translation {
  [key: string]: string | Translation;
}

interface UseTranslationReturn {
  t: (key: string, options?: any) => string;
  language: string;
  changeLanguage: (lang: string) => void;
  isRTL: boolean;
}

export const useTranslation = (): UseTranslationReturn => {
  const [language, setLanguage] = useState(defaultLanguage);
  const [translations, setTranslations] = useState<Translation>({});

  useEffect(() => {
    // Load translations for current language
    import(`./locales/${language}.json`).then((module) => {
      setTranslations(module.default);
    });
  }, [language]);

  const changeLanguage = (lang: string) => {
    setLanguage(lang);
    localStorage.setItem('language', lang);
  };

  const t = (key: string, options?: any): string => {
    let translation = translations[key] || key;
    
    // Handle pluralization
    if (options?.count !== undefined) {
      const count = options.count;
      if (count === 1) {
        translation = translations[`${key}_one`] || translation;
      } else {
        translation = translations[`${key}_other`] || translation;
      }
    }
    
    // Handle interpolation
    if (options?.replace) {
      Object.keys(options.replace).forEach(placeholder => {
        translation = translation.replace(`{{${placeholder}}}`, options.replace[placeholder]);
      });
    }
    
    return translation;
  };

  const isRTL = languages.find(lang => lang.code === language)?.rtl || false;

  return { t, language, changeLanguage, isRTL };
};

// i18n/locales/en.json
{
  "app": {
    "title": "Stock Analysis",
    "description": "Professional stock chart analysis with sentiment tracking"
  },
  "navigation": {
    "dashboard": "Dashboard",
    "stocks": "Stocks",
    "sentiment": "Sentiment",
    "portfolio": "Portfolio",
    "settings": "Settings"
  },
  "stock": {
    "search_placeholder": "Search by symbol, name, or sector...",
    "no_results": "No stocks found",
    "loading": "Loading...",
    "error": "Error loading stock data",
    "price": "Price",
    "change": "Change",
    "volume": "Volume",
    "market_cap": "Market Cap",
    "pe_ratio": "P/E Ratio"
  },
  "chart": {
    "timeframe_1d": "1 Day",
    "timeframe_1w": "1 Week",
    "timeframe_1m": "1 Month",
    "timeframe_3m": "3 Months",
    "timeframe_6m": "6 Months",
    "timeframe_1y": "1 Year",
    "timeframe_5y": "5 Years",
    "timeframe_max": "Max",
    "indicators": "Indicators",
    "rsi": "RSI",
    "macd": "MACD",
    "bollinger": "Bollinger Bands",
    "moving_averages": "Moving Averages"
  },
  "accessibility": {
    "skip_to_main": "Skip to main content",
    "skip_to_navigation": "Skip to navigation",
    "keyboard_shortcuts": "Keyboard Shortcuts",
    "screen_reader_only": "Screen reader only content"
  }
}

// i18n/locales/ko.json
{
  "app": {
    "title": "주식 분석",
    "description": "감성 추적이 포함된 전문적인 주식 차트 분석"
  },
  "navigation": {
    "dashboard": "대시보드",
    "stocks": "주식",
    "sentiment": "감성 분석",
    "portfolio": "포트폴리오",
    "settings": "설정"
  },
  "stock": {
    "search_placeholder": "심볼, 이름, 또는 섹터로 검색...",
    "no_results": "주식을 찾을 수 없습니다",
    "loading": "로딩 중...",
    "error": "주식 데이터 로딩 오류",
    "price": "가격",
    "change": "변동",
    "volume": "거래량",
    "market_cap": "시가 총액",
    "pe_ratio": "PER 비율"
  },
  "chart": {
    "timeframe_1d": "1일",
    "timeframe_1w": "1주",
    "timeframe_1m": "1개월",
    "timeframe_3m": "3개월",
    "timeframe_6m": "6개월",
    "timeframe_1y": "1년",
    "timeframe_5y": "5년",
    "timeframe_max": "최대",
    "indicators": "지표",
    "rsi": "RSI",
    "macd": "MACD",
    "bollinger": "볼린저 밴드",
    "moving_averages": "이동 평균"
  },
  "accessibility": {
    "skip_to_main": "메인 콘텐츠로 건너뛰기",
    "skip_to_navigation": "네비게이션으로 건너뛰기",
    "keyboard_shortcuts": "키보드 단축키",
    "screen_reader_only": "스크린 리더 전용 콘텐츠"
  }
}
```

## 8. 접근성 테스트 자동화

### 8.1 접근성 테스트 도구 설정
```javascript
// tests/accessibility/axe-tests.js
import { chromium } from 'playwright';
import { injectAxe, checkA11y } from 'axe-playwright';

class AccessibilityTests {
  constructor() {
    this.browser = null;
    this.page = null;
    this.violations = [];
  }

  async setup() {
    this.browser = await chromium.launch();
    this.page = await this.browser.newPage();
    await injectAxe(this.page);
  }

  async runAccessibilityTests(url) {
    await this.page.goto(url);
    
    // Wait for page to load
    await this.page.waitForLoadState('networkidle');
    
    // Run axe accessibility tests
    const results = await checkA11y(this.page, null, {
      detailedReport: true,
      detailedReportOptions: { html: true },
      reporter: 'v2'
    });

    this.violations = results.violations;
    
    // Generate accessibility report
    await this.generateReport(results);
    
    return results;
  }

  async generateReport(results) {
    const report = {
      url: this.page.url(),
      timestamp: new Date().toISOString(),
      violations: results.violations.map(violation => ({
        id: violation.id,
        impact: violation.impact,
        tags: violation.tags,
        description: violation.description,
        help: violation.help,
        helpUrl: violation.helpUrl,
        nodes: violation.nodes.map(node => ({
          html: node.html,
          target: node.target,
          failureSummary: node.failureSummary
        }))
      })),
      passes: results.passes.length,
      incomplete: results.incomplete.length,
      score: this.calculateAccessibilityScore(results)
    };

    // Save report
    const reportPath = `accessibility-report-${Date.now()}.json`;
    require('fs').writeFileSync(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`Accessibility report saved to: ${reportPath}`);
  }

  calculateAccessibilityScore(results) {
    const totalTests = results.violations.length + results.passes.length;
    const passedTests = results.passes.length;
    
    if (totalTests === 0) return 100;
    
    // Weight violations by impact
    const weightedViolations = results.violations.reduce((acc, violation) => {
      const weight = {
        'minor': 1,
        'moderate': 5,
        'serious': 15,
        'critical': 50
      }[violation.impact] || 1;
      
      return acc + weight;
    }, 0);

    const maxPossibleScore = totalTests * 50; // Maximum weight per test
    const currentScore = maxPossibleScore - weightedViolations;
    
    return Math.max(0, Math.min(100, (currentScore / maxPossibleScore) * 100));
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

// Usage in tests
const accessibilityTests = new AccessibilityTests();

describe('Accessibility Tests', () => {
  test('Main page accessibility', async () => {
    const results = await accessibilityTests.runAccessibilityTests('http://localhost:3000');
    
    expect(results.violations).toHaveLength(0);
    expect(results.score).toBeGreaterThanOrEqual(95);
  });

  test('Stock chart accessibility', async () => {
    const results = await accessibilityTests.runAccessibilityTests('http://localhost:3000/stocks/AAPL');
    
    // Check for specific accessibility requirements
    const hasKeyboardNavigation = results.passes.some(pass => 
      pass.ruleId === 'keyboard-navigation'
    );
    
    const hasColorContrast = results.passes.some(pass => 
      pass.ruleId === 'color-contrast'
    );
    
    expect(hasKeyboardNavigation).toBe(true);
    expect(hasColorContrast).toBe(true);
  });
});
```

### 8.2 자동화된 접근성 CI/CD
```yaml
# .github/workflows/accessibility.yml
name: Accessibility Testing

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  accessibility-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: |
        cd frontend
        npm install
    
    - name: Install Playwright
      run: |
        cd frontend
        npx playwright install
    
    - name: Build application
      run: |
        cd frontend
        npm run build
    
    - name: Start application
      run: |
        cd frontend
        npm start &
        sleep 30
    
    - name: Run accessibility tests
      run: |
        cd frontend
        npx playwright test --project=accessibility
    
    - name: Upload accessibility report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: accessibility-report
        path: accessibility-report/
    
    - name: Check accessibility score
      run: |
        node scripts/check-accessibility-score.js
    
    - name: Comment PR with accessibility results
      uses: actions/github-script@v6
      if: github.event_name == 'pull_request'
      with:
        script: |
          const fs = require('fs');
          const path = 'accessibility-report/latest-report.json';
          
          if (fs.existsSync(path)) {
            const report = JSON.parse(fs.readFileSync(path, 'utf8'));
            const score = report.score;
            
            if (score < 95) {
              const comment = `## 🚨 Accessibility Issues Found\n\n**Accessibility Score: ${score}/100**\n\nPlease review the [accessibility report](${process.env.GITHUB_SERVER_URL}/blob/${{process.env.GITHUB_SHA}/accessibility-report/latest-report.json) and fix the issues before merging.\n\n### Violations:\n${report.violations.map(v => `- ${v.description}`).join('\n')}`;
              
              github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: context.issue.number,
                body: comment
              });
            }
          }
```

## 9. 결론

본 UI/UX 접근성 개선 계획은 WCAG 2.1 AA 준수를 충족하는 포괄적인 접근성 시스템을 구축하기 위한 상세한 전략을 제시합니다.

주요 특징:
1. **키보드 내비게이션**: 완전한 키보드 탐색 및 단축키 지원
2. **스크린 리더 지원**: ARIA 레이블 및 라이브 리전스 구현
3. **반응형 디자인**: 모바일, 태블릿, 데스크톱 최적화
4. **색상 대비**: 다크 모드 및 고대비 테마 지원
5. **다국어 지원**: i18n 시스템을 통한 다국어 지원
6. **자동화된 테스트**: 지속적인 접근성 테스트 및 CI/CD 통합
7. **사용자 제어**: 개인화된 접근성 설정 옵션

이 접근성 개선 시스템을 통해 모든 사용자가 장애에 관계없이 애플리케이션을 효과적으로 사용할 수 있으며, 법적적인 요구사항을 충족하여 법적적 준수를 높일 수 있습니다.