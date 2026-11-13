# Spec Delta

## Purpose

회의록 등록 · 할 일 배정과 완료 · 댓글 · 합류 다섯 가지 팀 활동을 행위자 · 시점 · 대상과 함께 기록하고, 팀 활동과 내 활동으로 보여 주어 팀의 흐름을 한눈에 확인하게 한다.

## ADDED Requirements

### Requirement: 활동 종류
<!-- 근거: J-07 · profile.html / 정의서 6 -->
시스템은 활동 kind 를 meeting_add · todo_assign · todo_done · comment_add · member_join 다섯 가지로만 MUST 기록한다. 팀 생성 · 계정 변경 · 진행(DOING) 이동 · 삭제는 기록하지 않는다. 회의록 저장 때 담당자가 붙은 할 일도 todo_assign 으로 남긴다.

#### Scenario: 팀을 막 만든 owner
- **WHEN** 팀을 만들기만 한 owner 가 내 활동을 보면
- **THEN** 200 과 빈 배열이고 화면은 「활동 기록 없음」 / 「팀 생성은 활동 kind 5종에 없음」을 보여 준다

#### Scenario: 회의록 저장의 활동
- **WHEN** 담당자가 붙은 할 일 2건이 뽑힌 회의록을 저장하면
- **THEN** meeting_add 1건과 todo_assign 2건이 생긴다

### Requirement: 팀 활동 조회
<!-- 근거: F-01 · team.html / 정의서 7-1 -->
시스템은 `GET /api/teams/{id}/activities` 로 `id · kind · actor_name · text · created_at` 을 최신 순으로 최근 50건까지 MUST 돌려준다. text 는 서버가 만든 완성 문장이고 화면은 그대로 그린다. 다른 팀은 403 `FORBIDDEN` 이다.

#### Scenario: 60건 쌓인 팀
- **WHEN** 활동 60건인 팀의 활동을 조회하면
- **THEN** 최신 50건만 최신 순으로 온다

### Requirement: 내 활동 조회
<!-- 근거: J-07 · profile.html / 정의서 7-1 -->
시스템은 `GET /api/me/activities` 로 내가 행위자인 활동을 같은 필드 · 같은 순서 · 같은 상한으로 MUST 돌려준다. 내 정보 화면은 내 할 일과 내 활동을 함께 보여 준다.

#### Scenario: 내 활동
- **WHEN** 댓글 1건을 쓴 사람이 내 정보 화면을 열면
- **THEN** 내 활동에 comment_add 1건이 보인다

### Requirement: 활동 띠 색
<!-- 근거: F-01 · team.html / 정의서 7-2 -->
화면은 활동 kind 로 띠 색을 MUST 고른다. meeting_add=blue · todo_assign=orange · todo_done=green · comment_add 와 member_join=purple 이며 팔레트 5색 밖의 색은 쓰지 않는다.

#### Scenario: 완료 활동
- **WHEN** todo_done 활동을 그리면
- **THEN** 좌측 띠는 green 이다
