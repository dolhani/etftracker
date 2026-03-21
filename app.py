import streamlit as st
import pandas as pd

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

# 스타일 함수 정의
def highlight_status(row):
    # 기본 스타일
    styles = [''] * len(row)
    if row['상태'] == '신규편입':
        return ['background-color: #ffecec; color: #d63031; font-weight: bold'] * len(row) # 연한 빨강
    elif row['상태'] == '전량제외':
        return ['background-color: #eaf2ff; color: #0984e3; font-weight: bold'] * len(row) # 연한 파랑
    return styles

# 실행 및 화면 구성
st.title("🚀 ETF 구성종목 리밸런싱 리포트")

file_1 = 'NAV 구성종목시세_20260310_180000.xls'
file_2 = 'NAV 구성종목시세_20260321_184011.xls'

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