# Requirements Document

## Introduction

Stock Chart Analysis 애플리케이션에 소셜 미디어 센티먼트 분석 기능을 추가하여 커뮤니티에서 언급되는 주식들을 실시간으로 추적하고 분석합니다. Reddit, Twitter, Discord 등 다양한 커뮤니티에서 언급되는 주식의 빈도와 감정을 분석하여 투자자들에게 소셜 트렌드 정보를 제공합니다.

## Glossary

- **Social_Sentiment_System**: 소셜 미디어에서 주식 언급을 추적하고 분석하는 시스템
- **Mention_Counter**: 특정 기간 동안 주식 심볼의 언급 횟수를 계산하는 컴포넌트
- **Trending_Detector**: 언급량이 급증하는 주식을 감지하는 알고리즘
- **Community_Filter**: 투자 성향별로 커뮤니티를 분류하고 필터링하는 시스템
- **Sentiment_Analyzer**: 언급 내용의 긍정/부정 감정을 분석하는 엔진

## Requirements

### Requirement 1

**User Story:** 사용자로서, 현재 소셜 미디어에서 가장 많이 언급되는 주식들을 실시간으로 보고 싶습니다. 그래야 시장의 관심사를 파악할 수 있습니다.

#### Acceptance Criteria

1. THE Social_Sentiment_System SHALL 실시간으로 주식 언급 데이터를 수집하고 표시한다
2. THE Mention_Counter SHALL 1시간, 24시간, 7일 단위로 언급 횟수를 집계한다
3. THE Social_Sentiment_System SHALL 상위 20개 언급 주식을 랭킹 형태로 표시한다
4. WHEN 사용자가 언급 랭킹을 확인하면, THE Social_Sentiment_System SHALL 각 주식의 언급 횟수와 변화율을 표시한다
5. THE Social_Sentiment_System SHALL 5분마다 데이터를 자동 업데이트한다

### Requirement 2

**User Story:** 사용자로서, 갑자기 언급이 급증하는 주식들을 빠르게 발견하고 싶습니다. 그래야 새로운 투자 기회를 놓치지 않을 수 있습니다.

#### Acceptance Criteria

1. THE Trending_Detector SHALL 이전 24시간 대비 언급량이 200% 이상 증가한 주식을 감지한다
2. THE Trending_Detector SHALL 트렌딩 주식을 별도 섹션에 우선 표시한다
3. WHEN 주식이 트렌딩 상태가 되면, THE Social_Sentiment_System SHALL 시각적 알림 표시를 제공한다
4. THE Trending_Detector SHALL 트렌딩 시작 시간과 증가율을 함께 표시한다
5. THE Social_Sentiment_System SHALL 트렌딩 주식의 언급량 변화를 그래프로 시각화한다

### Requirement 3

**User Story:** 사용자로서, 투자 성향별로 커뮤니티를 필터링하여 관련 정보만 보고 싶습니다. 그래야 내 투자 스타일에 맞는 정보를 얻을 수 있습니다.

#### Acceptance Criteria

1. THE Community_Filter SHALL 단타, 가치투자, 성장투자 카테고리로 커뮤니티를 분류한다
2. THE Community_Filter SHALL 사용자가 원하는 투자 성향을 선택할 수 있도록 지원한다
3. WHEN 사용자가 특정 투자 성향을 선택하면, THE Social_Sentiment_System SHALL 해당 커뮤니티의 데이터만 표시한다
4. THE Community_Filter SHALL 여러 투자 성향을 동시에 선택할 수 있도록 지원한다
5. THE Social_Sentiment_System SHALL 각 커뮤니티별 언급 비중을 시각적으로 표시한다

### Requirement 4

**User Story:** 사용자로서, 주식에 대한 커뮤니티의 감정(긍정/부정)을 알고 싶습니다. 그래야 단순 언급량뿐만 아니라 시장 심리도 파악할 수 있습니다.

#### Acceptance Criteria

1. THE Sentiment_Analyzer SHALL 각 언급의 긍정, 중립, 부정 감정을 분석한다
2. THE Social_Sentiment_System SHALL 주식별 전체 감정 점수를 -100에서 +100 범위로 표시한다
3. THE Sentiment_Analyzer SHALL 감정 변화 추이를 시간별로 추적한다
4. WHEN 사용자가 특정 주식을 선택하면, THE Social_Sentiment_System SHALL 상세 감정 분석 결과를 표시한다
5. THE Social_Sentiment_System SHALL 감정 점수를 색상으로 시각화한다 (녹색: 긍정, 빨간색: 부정)

### Requirement 5

**User Story:** 사용자로서, 소셜 센티먼트 데이터와 주식 차트를 함께 보고 싶습니다. 그래야 소셜 트렌드와 주가 움직임의 상관관계를 분석할 수 있습니다.

#### Acceptance Criteria

1. THE Social_Sentiment_System SHALL 기존 주식 차트 위에 언급량 데이터를 오버레이로 표시한다
2. THE Social_Sentiment_System SHALL 감정 점수 변화를 별도 서브플롯으로 표시한다
3. WHEN 사용자가 차트에서 특정 시점을 선택하면, THE Social_Sentiment_System SHALL 해당 시점의 주요 언급 내용을 표시한다
4. THE Social_Sentiment_System SHALL 언급량 급증 시점을 차트에 마커로 표시한다
5. THE Social_Sentiment_System SHALL 소셜 데이터와 주가 데이터의 상관관계 지표를 계산하여 표시한다