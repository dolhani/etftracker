import streamlit as st
import pandas as pd
import glob
import re
from datetime import datetime, timedelta

st.set_page_config(page_title="ETF 리밸런싱 분석", layout="wide")

def process_rebalancing(file_old, file_new):
    cols = ['종목명', '현재가', '등락률', '비중', '주식 단축 종목코드']

    # 데이터 로드
    df_old = pd.read_excel(file_old)[cols]
    df_new = pd.read_excel(file_new)[cols]

    # 병합 (Outer Join)
    df = pd.merge(df_old, df_new, on='주식 단축 종목코드', how='outer', suffixes=('_이전', '_현재'))

    # 상태 분류 로직 (신규, 제외, 유지)
    def check_status(row):
        if pd.isna(row['비중_이전']) or row['비중_이전'] == 0:
            return "신규편입"
        elif pd.isna(row['비중_현재']) or row['비중_현재'] == 0:
            return "전량제외"
        else:
            return "비중변경"

    df['상태'] = df.apply(check_status, axis=1)

    # 데이터 보정
    df['비중_이전'] = df['비중_이전'].fillna(0)
    df['비중_현재'] = df['비중_현재'].fillna(0)
    df['종목명'] = df['종목명_현재'].fillna(df['종목명_이전'])
    df['현재가'] = df['현재가_현재'].fillna(df['현재가_이전']).astype(int)
    df['등락률'] = df['등락률_현재'].fillna(df['등락률_이전'])
    df['비중변화'] = (df['비중_현재'] - df['비중_이전']).round(3)

    # 현재 비중 순 정렬 (제외 종목은 하단으로 이동)
    result = df.sort_values(by=['비중_현재', '비중_이전'], ascending=[False, False])

    # 출력 컬럼 정리
    result = result[['상태', '종목명', '주식 단축 종목코드', '현재가', '등락률', '비중_이전', '비중_현재', '비중변화']]
    result.columns = ['상태', '종목명', '코드', '현재가', '등락률', '이전비중', '현재비중', '변동']
    return result


def extract_date_from_filename(filename):
    """파일명에서 날짜 추출 (예: NAV 구성종목시세_20260310_180000.xls → 2026-03-10)"""
    match = re.search(r'(\d{8})_\d{6}', filename)
    if match:
        return datetime.strptime(match.group(1), '%Y%m%d')
    return None


def select_file_pair(filename_list, period):
    """선택된 기간에 맞는 파일 쌍(이전, 현재)을 반환"""
    # 파일 목록에서 날짜 추출 & 유효한 파일만 필터
    dated_files = []
    for f in filename_list:
        d = extract_date_from_filename(f)
        if d:
            dated_files.append((d, f))
    dated_files.sort(key=lambda x: x[0])

    if len(dated_files) < 2:
        return None, None

    if period == "1일":
        # 가장 최근 2개 파일
        return dated_files[-2][1], dated_files[-1][1]
    elif period == "일주일":
        # 가장 최근 파일 기준 ~7일 전 파일 찾기
        latest_date, latest_file = dated_files[-1]
        target_date = latest_date - timedelta(days=7)
        # target_date와 가장 가까운 파일 선택
        closest = min(dated_files[:-1], key=lambda x: abs((x[0] - target_date).total_seconds()))
        return closest[1], latest_file
    else:
        # 1일과 동일하게 동작
        return dated_files[-2][1], dated_files[-1][1]


# 스타일 함수 정의
def highlight_status(row):
    # 기본 스타일
    styles = [''] * len(row)
    if row['상태'] == '신규편입':
        return ['background-color: #ffecec; color: #d63031; font-weight: bold'] * len(row)
    elif row['상태'] == '전량제외':
        return ['background-color: #eaf2ff; color: #0984e3; font-weight: bold'] * len(row)
    return styles


# ===================== 실행 및 화면 구성 =====================
st.title("🚀 ETF 구성종목 리밸런싱 리포트")

# 파일 목록 가져오기
filename_list = glob.glob('NAV 구성종목시세_*.xls*')
filename_list.sort()

# --- UI: 기간 선택 ---
period = st.selectbox(
    "비교 기간을 선택하세요",
    options=["1일", "일주일"],
    index=0  # 기본값: 1일
)

file_1, file_2 = select_file_pair(filename_list, period)

if file_1 is None or file_2 is None:
    st.error("비교할 파일이 충분하지 않습니다. 최소 2개 이상의 파일이 필요합니다.")
    st.stop()

st.caption(f"📂 비교 대상: `{file_1}`  ↔  `{file_2}`")

try:
    final_df = process_rebalancing(file_1, file_2)

    # 요약 정보 상단 배치
    new_count = len(final_df[final_df['상태'] == '신규편입'])
    out_count = len(final_df[final_df['상태'] == '전량제외'])

    c1, c2, c3 = st.columns(3)
    c1.metric("신규 편입", f"{new_count} 종목")
    c2.metric("전량 제외", f"{out_count} 종목")
    c3.info("💡 빨간색 행은 신규, 파란색 행은 제외 종목입니다.")

    # 스타일 적용 테이블 출력
    st.subheader("리밸런싱 상세 내역")
    styled_table = final_df.style.apply(highlight_status, axis=1) \
                                 .format({'이전비중': '{:.2f}%', '현재비중': '{:.2f}%', '변동': '{:+.2f}%'})

    st.dataframe(styled_table, use_container_width=True, height=600)

except Exception as e:
    st.error(f"데이터를 처리하는 중 오류가 발생했습니다: {e}")